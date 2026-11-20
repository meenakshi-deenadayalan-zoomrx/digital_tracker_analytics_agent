"""Windows repository reads using resolved NT identities and the same handles.

DOS volume-name conversion can be denied by the host although file access is
allowed. NT names preserve volume identity; unresolved lexical paths never
authorize a read. This module does not alter Windows or sandbox permissions.
"""
import ctypes
from ctypes import wintypes
from contextlib import contextmanager
import fnmatch
from functools import lru_cache
import ntpath
import os
import re
from pathlib import PureWindowsPath
import time

REPOS = {"digitrace-chrome-extension", "perxcept-ap-server", "perxcept-ios", "perxcept-macos", "perxcept-data-processing-service"}
MAX_SCAN = 10000
MAX_SECONDS = 10

class BoundaryError(ValueError):
    pass

class FileTooLarge(BoundaryError):
    pass

class _Info(ctypes.Structure):
    _fields_ = [("attributes", wintypes.DWORD), ("created", wintypes.FILETIME),
                ("accessed", wintypes.FILETIME), ("written", wintypes.FILETIME),
                ("volume", wintypes.DWORD), ("size_high", wintypes.DWORD),
                ("size_low", wintypes.DWORD), ("links", wintypes.DWORD),
                ("index_high", wintypes.DWORD), ("index_low", wintypes.DWORD)]

class _DirInfo(ctypes.Structure):
    _fields_ = [("next", wintypes.DWORD), ("index", wintypes.DWORD),
                ("created", ctypes.c_longlong), ("accessed", ctypes.c_longlong),
                ("written", ctypes.c_longlong), ("changed", ctypes.c_longlong),
                ("size", ctypes.c_longlong), ("allocated", ctypes.c_longlong),
                ("attributes", wintypes.DWORD), ("name_bytes", wintypes.DWORD),
                ("ea_size", wintypes.DWORD), ("short_length", wintypes.BYTE),
                ("short_name", wintypes.WCHAR * 12), ("file_id", ctypes.c_longlong),
                ("filename", wintypes.WCHAR * 1)]

def _api():
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    declarations = {
        "CreateFileW": ([wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE], wintypes.HANDLE),
        "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
        "GetFileInformationByHandle": ([wintypes.HANDLE, ctypes.POINTER(_Info)], wintypes.BOOL),
        "GetFileInformationByHandleEx": ([wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
        "GetFinalPathNameByHandleW": ([wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD], wintypes.DWORD),
        "ReadFile": ([wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p], wintypes.BOOL),
        "CompareStringOrdinal": ([wintypes.LPCWSTR, ctypes.c_int, wintypes.LPCWSTR, ctypes.c_int, wintypes.BOOL], ctypes.c_int),
    }
    for name, (args, result) in declarations.items():
        getattr(k, name).argtypes, getattr(k, name).restype = args, result
    return k

def _relative(value, allow_empty=False):
    if not isinstance(value, str) or "\x00" in value or ":" in value:
        raise BoundaryError("Repository input must be an ordinary relative path without a stream or drive")
    raw = value.replace("/", "\\")
    p = PureWindowsPath(raw)
    if p.drive or p.root or (not raw and not allow_empty):
        raise BoundaryError("Absolute, device and drive-relative repository paths are refused")
    parts = raw.split("\\") if raw else []
    if len(parts) > 128:
        raise BoundaryError("Repository path exceeded its component limit")
    if any(not part or part in (".", "..") or part.endswith((".", " ")) or any(c in part for c in '*?<>|"') for part in parts):
        raise BoundaryError("Empty, traversal and ambiguous repository path components are refused")
    if any(part.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *("COM"+str(i) for i in range(1,10)), *("LPT"+str(i) for i in range(1,10))} for part in parts):
        raise BoundaryError("Windows device names are refused")
    return parts

class WindowsRepoScope:
    def __init__(self, configured):
        if os.name != "nt":
            raise BoundaryError("Windows handle scope is only used on Windows")
        if not isinstance(configured, str) or "\x00" in configured:
            raise BoundaryError("Configure a dedicated absolute local repository directory")
        self.k, self.pins, self.base_handle = _api(), [], None
        self.started, self.scanned = time.monotonic(), 0
        p = PureWindowsPath(configured)
        if not p.is_absolute() or not p.drive or p.drive.startswith("\\") or len(p.drive) != 2 or p.drive[1] != ":":
            raise BoundaryError("Repository base must be an absolute local drive path; UNC/device bases are unsupported")
        # Input validation is lexical only; authorization below uses open handles.
        _relative("\\".join(p.parts[1:]), allow_empty=True)
        self.base = ntpath.normpath(str(p))
        try:
            self.base_handle = self._open(self.base, directory=True)
            self.pins.append(self.base_handle)
            self.identity = self._identity(self.base_handle)
            self.root_identity, root_object = self._identity_temp(p.anchor)
            home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
            self.home_identity, home_object = self._identity_temp(home)
            base_object = self._object_id(self._info(self.base_handle))
            if base_object in (root_object, home_object):
                raise BoundaryError("Configure a dedicated repository base, not a drive root or employee home")
            # Pin every lexical ancestor against rename/delete for this scope.
            ancestor = ntpath.dirname(self.base)
            while ancestor != p.anchor:
                self.pins.append(self._open(ancestor, directory=True, metadata_only=True))
                parent = ntpath.dirname(ancestor)
                if parent == ancestor:
                    break
                ancestor = parent
        except BaseException:
            self.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        for handle in reversed(self.pins):
            self.k.CloseHandle(handle)
        self.pins.clear()

    def _same(self, left, right):
        # Never conflate distinct entries in a case-sensitive Windows directory.
        # Canonical casing differences are refused, not guessed or case folded.
        return self.k.CompareStringOrdinal(left, len(left), right, len(right), False) == 2

    @staticmethod
    def _object_id(info):
        return info.volume, info.index_high, info.index_low

    def _inside(self, target):
        a, b = self.identity.split("\\"), target.split("\\")
        return (len(b) > len(a) and all(self._same(x, y) for x, y in zip(a, b))
                and any(self._same(b[len(a)], repo) for repo in REPOS))

    def _open(self, file, directory=False, metadata_only=False):
        # Directory sharing permits normal activity but denies rename/delete.
        # File reads deny concurrent writes and deletes until this handle closes.
        access, share = ((0x80 if metadata_only else 0x81), 3) if directory else (0x80000000, 1)
        handle = self.k.CreateFileW("\\\\?\\"+file, access, share, None, 3, 0x02000000, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        return handle

    def _info(self, handle):
        info = _Info()
        if not self.k.GetFileInformationByHandle(handle, ctypes.byref(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        return info

    def _identity(self, handle):
        size = 1024
        while size <= 65536:
            buf = ctypes.create_unicode_buffer(size)
            used = self.k.GetFinalPathNameByHandleW(handle, buf, size, 2)  # normalized VOLUME_NAME_NT
            if not used:
                raise ctypes.WinError(ctypes.get_last_error())
            if used < size:
                name = buf.value.rstrip("\\")
                if not re.match(r'^\\Device\\HarddiskVolume\d+(?:\\|$)', name) or "\x00" in name:
                    raise BoundaryError("Unsupported canonical Windows identity")
                return name
            size = used+1
        raise BoundaryError("Canonical Windows identity exceeded its limit")

    def _identity_temp(self, file):
        handle = self._open(ntpath.normpath(file), directory=True, metadata_only=True)
        try:
            return self._identity(handle), self._object_id(self._info(handle))
        finally:
            self.k.CloseHandle(handle)

    @contextmanager
    def target(self, relative, directory=False):
        parts = _relative(relative)
        if parts[0] not in REPOS:
            raise BoundaryError("Repository is outside the five declared tracker repositories")
        opened = []
        try:
            for i in range(1, len(parts)):
                parent = self._open(ntpath.join(self.base, *parts[:i]), directory=True, metadata_only=True)
                opened.append(parent)
                if not self._inside(self._identity(parent)):
                    raise BoundaryError("Repository path escapes the canonical base")
            handle = self._open(ntpath.join(self.base, *parts), directory=directory)
            opened.append(handle)
            identity, info = self._identity(handle), self._info(handle)
            if not self._inside(identity):
                raise BoundaryError("Repository path escapes the canonical base")
            if bool(info.attributes & 0x10) != directory:
                raise BoundaryError("Repository target has the wrong file type")
            if not directory and info.links != 1:
                raise BoundaryError("Multiply linked repository files need an explicit ownership contract")
            yield handle, info, identity
        finally:
            for handle in reversed(opened):
                self.k.CloseHandle(handle)

    def read_text(self, relative, maximum):
        if time.monotonic()-self.started > MAX_SECONDS:
            raise BoundaryError("Repository read exceeded the declared time budget")
        with self.target(relative) as (handle, info, _):
            size = (info.size_high << 32) | info.size_low
            if size > maximum:
                raise FileTooLarge("Repository file exceeds the declared byte limit")
            output = bytearray()
            while len(output) <= maximum:
                if time.monotonic()-self.started > MAX_SECONDS:
                    raise BoundaryError("Repository read exceeded the declared time budget")
                buffer = ctypes.create_string_buffer(min(65536, maximum+1-len(output)))
                read = wintypes.DWORD()
                if not self.k.ReadFile(handle, buffer, len(buffer), ctypes.byref(read), None):
                    raise ctypes.WinError(ctypes.get_last_error())
                if not read.value:
                    return output.decode("utf-8", errors="replace")
                output.extend(buffer.raw[:read.value])
            raise FileTooLarge("Repository file grew beyond the declared byte limit")

    def validate_directory(self, relative):
        with self.target(relative, directory=True):
            return True

    def _entries(self, handle):
        if _DirInfo.filename.offset != 104:
            raise BoundaryError("Unsupported Windows directory record layout")
        first = True
        while True:
            buffer = ctypes.create_string_buffer(65536)
            if not self.k.GetFileInformationByHandleEx(handle, 11 if first else 10, buffer, len(buffer)):
                error = ctypes.get_last_error()
                if error == 18:
                    return
                raise ctypes.WinError(error)
            first = False
            offset = 0
            while True:
                if offset+ctypes.sizeof(_DirInfo) > len(buffer):
                    raise BoundaryError("Malformed Windows directory record")
                entry = _DirInfo.from_buffer_copy(buffer.raw[offset:offset+ctypes.sizeof(_DirInfo)])
                end = offset+104+entry.name_bytes
                if entry.name_bytes % 2 or end > len(buffer):
                    raise BoundaryError("Malformed Windows directory filename")
                name = buffer.raw[offset+104:end].decode("utf-16-le")
                if name not in (".", ".."):
                    _relative(name)
                    yield name, bool(entry.attributes & 0x10)
                if not entry.next:
                    break
                if entry.next < 104 or offset+entry.next <= offset:
                    raise BoundaryError("Malformed Windows directory offset")
                offset += entry.next

    def files(self, repo, subpath="", pattern="**/*"):
        if repo not in REPOS:
            raise BoundaryError("Repository is outside the five declared tracker repositories")
        subparts = _relative(subpath, allow_empty=True)
        if not isinstance(pattern, str) or len(pattern) > 512 or len(pattern.split('/'))>64 or not pattern or ":" in pattern or "\\" in pattern or pattern.startswith("/") or any(p in ('', '.', '..') for p in pattern.split("/")):
            raise BoundaryError("Repository glob must be a bounded relative glob")
        start = "\\".join([repo, *subparts])
        stack = [(start, "")]
        visited = []
        while stack:
            relative, below = stack.pop()
            with self.target(relative, directory=True) as (handle, _, identity):
                if any(self._same(identity, old) for old in visited):
                    continue
                visited.append(identity)
                for name, is_dir in self._entries(handle):
                    self.scanned += 1
                    if self.scanned > MAX_SCAN or time.monotonic()-self.started > MAX_SECONDS:
                        raise BoundaryError("Repository enumeration exceeded the declared scan budget")
                    if name.startswith(".") or name in ("node_modules", "__pycache__", "dist", "build"):
                        continue
                    child = relative+"\\"+name
                    visible = below+"/"+name if below else name
                    if is_dir:
                        try:
                            self.validate_directory(child)
                        except (OSError, BoundaryError):
                            continue
                        stack.append((child, visible))
                    elif _glob_match(visible, pattern):
                        try:
                            with self.target(child):
                                yield child
                        except (OSError, BoundaryError):
                            continue

def _glob_match(path, pattern):
    # Component-aware globbing: '*' never crosses a directory separator.
    # Matching selects candidates only; handle identity authorizes each read.
    names, patterns = path.split('/'), pattern.split('/')
    @lru_cache(maxsize=None)
    def match(i, j):
        if j == len(patterns):
            return i == len(names)
        if patterns[j] == '**':
            return match(i, j+1) or (i < len(names) and match(i+1, j))
        return i < len(names) and fnmatch.fnmatchcase(names[i].lower(), patterns[j].lower()) and match(i+1, j+1)
    return match(0, 0)
