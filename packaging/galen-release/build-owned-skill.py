"""Build a declared skill from source plus explicit hash-bound external assets.

No source file is recovered from an old ZIP at build time. External ZIPs supply
only individually declared binary asset members. Unknown source files, missing
inputs and content drift fail closed. Outputs are never installed or published.
"""
from pathlib import Path, PurePosixPath
import argparse, hashlib, json, re, stat, zipfile

def digest(data):return hashlib.sha256(data).hexdigest()
def member_path(name,directory=False):
    if not isinstance(name,str) or not name or '\\'in name or ':'in name or '\0'in name or name.startswith('/'):
        raise ValueError('unsafe_member_path')
    value=name[:-1]if directory and name.endswith('/')else name
    if not value or any(p in ('','..','.')for p in value.split('/')):raise ValueError('unsafe_member_path')
    if directory!=name.endswith('/'):raise ValueError('directory_kind_mismatch')
    return value
def source_path(root,relative):
    member_path(relative)
    target=root/relative
    if not target.resolve().is_relative_to(root):raise ValueError('source_path_outside_root')
    for parent in [target,*target.parents]:
        if parent==root.parent:break
        if parent.is_symlink() or (hasattr(parent,'is_junction')and parent.is_junction()):raise ValueError('linked_source_preserved')
    if not target.is_file()or not stat.S_ISREG(target.stat().st_mode):raise ValueError('missing_source_file')
    return target
def load_manifest(root):
    manifest=json.loads((root/'PACKAGING.json').read_text(encoding='utf-8'))
    if manifest.get('schemaVersion')!=1:raise ValueError('unsupported_manifest_schema')
    if not isinstance(manifest.get('name'),str)or'/'in manifest['name']:raise ValueError('invalid_skill_name')
    names=set();case_names=set();source_names=set();entries=manifest.get('entries',[])
    if not entries or len(entries)>10000:raise ValueError('invalid_entry_count')
    for row in entries:
        directory=row.get('kind')=='directory'
        name=row.get('member')
        member_path(name,directory)
        if not name.startswith(manifest['name']+'/'):raise ValueError('unexpected_archive_root')
        if name in names or name.casefold()in case_names:raise ValueError('duplicate_archive_member')
        names.add(name);case_names.add(name.casefold())
        if row.get('kind')not in ('directory','source','asset'):raise ValueError('unknown_entry_kind')
        if directory:continue
        if not isinstance(row.get('bytes'),int)or not 0<=row['bytes']<=32*1024*1024:raise ValueError('entry_size_bound')
        if len(row.get('sha256',''))!=64:raise ValueError('invalid_entry_hash')
        if row['kind']=='source':
            relative=row.get('source')
            member_path(relative)
            if relative in source_names:raise ValueError('duplicate_source_declaration')
            source_names.add(relative)
        else:
            asset=row.get('asset',{})
            if asset.get('archiveMember')!=name or asset.get('fileSha256')!=row['sha256']or asset.get('memberSha256')!=row['sha256']:
                raise ValueError('asset_declaration_mismatch')
            if asset.get('inputId')!='sha256:'+asset.get('archiveSha256',''):raise ValueError('asset_input_id_mismatch')
    administrative={'PACKAGING.json','SOURCE-RECOVERY.json'}
    actual=set()
    for path in root.rglob('*'):
        if '__pycache__'in path.parts:continue
        if path.is_symlink()or(hasattr(path,'is_junction')and path.is_junction()):raise ValueError('linked_source_preserved')
        if path.is_file():actual.add(path.relative_to(root).as_posix())
    if actual-administrative!=source_names:raise ValueError('undeclared_or_missing_source_files')
    return manifest
def build(root,output,asset_input=None):
    root=Path(root).resolve();output=Path(output).resolve()
    if output.exists():raise ValueError('existing_output_preserved')
    manifest=load_manifest(root)
    if output==root or output.is_relative_to(root):raise ValueError('output_must_be_outside_source')
    assets=[r for r in manifest['entries']if r['kind']=='asset']
    supplied={};input_root=None
    if asset_input:
        file=Path(asset_input).resolve();input_root=file.parent
        supplied=json.loads(file.read_text(encoding='utf-8')).get('archives',{})
    if assets and not asset_input:raise ValueError('explicit_asset_inputs_required')
    archives={};contents={};total=0
    try:
        for row in manifest['entries']:
            if row['kind']=='directory':contents[row['member']]=b'';continue
            if row['kind']=='source':
                data=source_path(root,row['source']).read_bytes()
                if b'\0'in data:raise ValueError('binary_data_in_source')
                data.decode('utf-8-sig')
            else:
                asset=row['asset'];ident=asset['inputId']
                if ident not in supplied:raise ValueError('missing_external_asset_input')
                if ident not in archives:
                    record=supplied[ident];path=Path(record['path'])
                    if not path.is_absolute():path=input_root/path
                    raw=path.read_bytes()
                    if digest(raw)!=asset['archiveSha256']or record.get('sha256')!=asset['archiveSha256']:raise ValueError('external_archive_hash_mismatch')
                    archive=zipfile.ZipFile(path)
                    names=archive.namelist()
                    if len(names)!=len(set(names)):raise ValueError('duplicate_external_archive_member')
                    archives[ident]=archive
                archive=archives[ident]
                info=archive.getinfo(asset['archiveMember'])
                if info.file_size!=row['bytes']:raise ValueError('external_asset_size_mismatch')
                data=archive.read(info)
            if len(data)!=row['bytes']or digest(data)!=row['sha256']:raise ValueError('declared_content_drift')
            total+=len(data)
            if total>128*1024*1024:raise ValueError('skill_size_bound')
            contents[row['member']]=data
    finally:
        for archive in archives.values():archive.close()
    for host in ('codex','claude'):
        skill=contents.get(manifest['name']+'/'+host+'/SKILL.md')
        if skill is None:raise ValueError('missing_host_skill')
        version=re.search(r'(?m)^version:\s*(\d+)\s*$',skill.decode('utf-8-sig'))
        if not version or int(version[1])!=manifest['version']:raise ValueError('host_version_mismatch')
    output.mkdir(parents=True,exist_ok=False)
    archive=output/(manifest['name']+'.zip')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9)as z:
        for name,data in sorted(contents.items()):
            info=zipfile.ZipInfo(name,(2026,10,30,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=(0o40755 if name.endswith('/')else 0o100644)<<16
            z.writestr(info,data)
    result={'schemaVersion':1,'name':manifest['name'],'version':manifest['version'],'archive':str(archive),'sha256':digest(archive.read_bytes()),'bytes':archive.stat().st_size,'sourceManifestSha256':digest((root/'PACKAGING.json').read_bytes()),'entries':len(contents),'sourceFiles':sum(r['kind']=='source'for r in manifest['entries']),'externalAssetMembers':len(assets),'deploymentApproved':False,'publishedArtifactChanged':False}
    (output/'BUILD.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source');parser.add_argument('new_output');parser.add_argument('--asset-inputs')
    args=parser.parse_args()
    print(json.dumps(build(args.source,args.new_output,args.asset_inputs)))
