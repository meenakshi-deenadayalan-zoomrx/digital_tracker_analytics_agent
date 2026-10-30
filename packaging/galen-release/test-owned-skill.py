"""Offline builder checks using disposable source and binary fixtures only."""
from contextlib import ExitStack
import hashlib
import importlib.util
import io
import json
import os
import subprocess
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import zipfile

spec = importlib.util.spec_from_file_location("owned_skill_builder", Path(__file__).with_name("build-owned-skill.py"))
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
digest = lambda data: hashlib.sha256(data).hexdigest()


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="owned-skill-check-", dir=os.environ.get("OWNED_SKILL_TEST_TMPDIR"))
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "source"
        self.entries = []
        for host in ("codex", "claude"):
            data = b"---\nname: sample\nversion: 1\n---\nFixture only.\n"
            relative = host + "/SKILL.md"
            file = self.root / relative
            file.parent.mkdir(parents=True)
            file.write_bytes(data)
            self.entries.append(dict(member="sample/" + relative, kind="source", source=relative, bytes=len(data), sha256=digest(data)))
        self.manifest = dict(schemaVersion=1, name="sample", version=1, entries=self.entries)
        self.save_manifest()

    def save_manifest(self):
        (self.root / "PACKAGING.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def asset(self):
        member, data = "sample/codex/vendor/fixture.whl", b"\x00explicit-binary-fixture"
        archive = self.base / "input.zip"
        with zipfile.ZipFile(archive, "x") as z:
            z.writestr(member, data)
        sha = digest(archive.read_bytes())
        ident = "sha256:" + sha
        self.entries.append(dict(member=member, kind="asset", bytes=len(data), sha256=digest(data), asset=dict(inputId=ident, archiveSha256=sha, archiveMember=member, fileSha256=digest(data), memberSha256=digest(data))))
        self.save_manifest()
        inputs = self.base / "inputs.json"
        inputs.write_text(json.dumps(dict(archives={ident: dict(path=str(archive), sha256=sha)})), encoding="utf-8")
        return archive, inputs, member, data

    def symlink(self, target, link):
        try:
            os.symlink(target, link, target_is_directory=target.is_dir())
        except (OSError, NotImplementedError) as error:
            self.skipTest("Symbolic link creation unavailable: " + str(error))

    def junction(self, target, link):
        if os.name != "nt":
            self.skipTest("Windows junction check requires Windows")
        self.assertTrue(target.resolve().is_relative_to(self.base.resolve()))
        self.assertTrue(link.absolute().is_relative_to(self.base.absolute()))
        if any(c in str(target) + str(link) for c in '%!&|<>^\r\n"'):
            self.skipTest("Junction fixture path contains unsupported shell characters")
        command = 'mklink /J "' + str(link) + '" "' + str(target) + '"'
        result = subprocess.run("cmd.exe /d /c " + command, capture_output=True, text=True)
        if result.returncode:
            self.skipTest("Junction creation unavailable: " + (result.stdout + result.stderr).strip())
        # Remove only the junction itself before TemporaryDirectory cleanup.
        # The target and junction paths are verified fixture descendants above.
        self.addCleanup(os.rmdir, link)
        self.assertTrue(getattr(link.lstat(), "st_file_attributes", 0) & 1024)

    def test_actual_windows_junction_source_root_rejected(self):
        link = self.base / "source-junction"
        self.junction(self.root, link)
        with self.assertRaisesRegex(ValueError, "linked_path_preserved"):
            builder.build(link, self.base / "output")
        self.assertTrue((self.root / "codex/SKILL.md").exists())

    def test_actual_windows_junction_output_parent_rejected(self):
        target = self.base / "destination"
        target.mkdir()
        link = self.base / "output-junction"
        self.junction(target, link)
        with self.assertRaisesRegex(ValueError, "linked_path_preserved"):
            builder.build(self.root, link / "new-output")
        self.assertFalse((target / "new-output").exists())

    def test_deterministic_output_and_exact_members(self):
        first = builder.build(self.root, self.base / "first")
        second = builder.build(self.root, self.base / "second")
        self.assertEqual(first["sha256"], second["sha256"])
        with zipfile.ZipFile(first["archive"]) as z:
            self.assertEqual(set(z.namelist()), {row["member"] for row in self.entries})
            for row in self.entries:
                self.assertEqual(z.read(row["member"]), (self.root / row["source"]).read_bytes())

    def test_existing_output_is_preserved(self):
        output = self.base / "existing"
        output.mkdir()
        sentinel = output / "keep.txt"
        sentinel.write_bytes(b"keep")
        with self.assertRaisesRegex(ValueError, "existing_output_preserved"):
            builder.build(self.root, output)
        self.assertEqual(sentinel.read_bytes(), b"keep")

    def test_source_content_drift_rejected(self):
        (self.root / "codex/SKILL.md").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "declared_content_drift"):
            builder.build(self.root, self.base / "output")

    def test_unknown_source_file_rejected(self):
        (self.root / "extra.txt").write_text("unlisted")
        with self.assertRaisesRegex(ValueError, "undeclared_or_missing_source_files"):
            builder.build(self.root, self.base / "output")

    def test_explicit_assets_required(self):
        self.asset()
        with self.assertRaisesRegex(ValueError, "explicit_asset_inputs_required"):
            builder.build(self.root, self.base / "output")

    def test_asset_uses_verified_bytes_if_input_path_changes(self):
        archive, inputs, member, data = self.asset()
        original_read = Path.read_bytes

        def change_after_read(file):
            raw = original_read(file)
            if file == archive:
                archive.write_bytes(b"replaced after snapshot")
            return raw

        with mock.patch.object(Path, "read_bytes", change_after_read):
            result = builder.build(self.root, self.base / "output", inputs)
        with zipfile.ZipFile(result["archive"]) as z:
            self.assertEqual(z.read(member), data)

    def test_linked_source_root_rejected(self):
        link = self.base / "source-link"
        self.symlink(self.root, link)
        with self.assertRaisesRegex(ValueError, "linked_path_preserved"):
            builder.build(link, self.base / "output")

    def test_linked_output_parent_rejected(self):
        parent = self.base / "destination"
        parent.mkdir()
        link = self.base / "output-link"
        self.symlink(parent, link)
        with self.assertRaisesRegex(ValueError, "linked_path_preserved"):
            builder.build(self.root, link / "new-output")
        self.assertFalse((parent / "new-output").exists())

    def test_linked_packaging_manifest_rejected_before_read(self):
        target = self.base / "manifest.json"
        manifest = self.root / "PACKAGING.json"
        manifest.rename(target)
        self.symlink(target, manifest)
        with self.assertRaisesRegex(ValueError, "linked_path_preserved"):
            builder.build(self.root, self.base / "output")

    def test_linked_asset_manifest_rejected(self):
        _, inputs, _, _ = self.asset()
        link = self.base / "inputs-link.json"
        self.symlink(inputs, link)
        with self.assertRaisesRegex(ValueError, "linked_path_preserved"):
            builder.build(self.root, self.base / "output", link)

    def test_linked_asset_archive_rejected(self):
        archive, inputs, _, _ = self.asset()
        link = self.base / "archive-link.zip"
        self.symlink(archive, link)
        value = json.loads(inputs.read_bytes())
        next(iter(value["archives"].values()))["path"] = str(link)
        inputs.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "linked_path_preserved"):
            builder.build(self.root, self.base / "output", inputs)

    def test_windows_reparse_attributes_rejected_without_is_junction(self):
        old_lstat = Path.lstat

        def attributes(file, *args, **kwargs):
            if file == self.root:
                return SimpleNamespace(st_file_attributes=1024)
            return old_lstat(file, *args, **kwargs)

        with ExitStack() as stack:
            stack.enter_context(mock.patch.object(Path, "is_symlink", return_value=False))
            if hasattr(Path, "is_junction"):
                stack.enter_context(mock.patch.object(Path, "is_junction", return_value=False))
            stack.enter_context(mock.patch.object(Path, "lstat", attributes))
            with self.assertRaisesRegex(ValueError, "linked_path_preserved"):
                builder.build(self.root, self.base / "output")


if __name__ == "__main__":
    unittest.main(verbosity=2)
