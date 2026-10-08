"""同步未发布的本地插件快照；预检旧摘要，不覆盖漂移或已发布来源。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

ROOT=Path(__file__).resolve().parents[1]

def transient_path(path):
    """忽略解释器缓存和系统目录项，不把运行噪声放进可分发快照。"""
    value=Path(path)
    return '__pycache__' in value.parts or value.name in ('.DS_Store',) or value.suffix in ('.pyc','.pyo')


def inventory(root,skill_names=None):
    """拒绝链接后计算指定技能文件摘要，排除由插件单独维护的本地技能。"""
    root=Path(root)
    entries=sorted(root.rglob('*'))
    if any(p.is_symlink() for p in entries):raise ValueError('snapshot_symlink')
    selected=set(skill_names) if skill_names is not None else None
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in entries if p.is_file() and not transient_path(p.relative_to(root)) and (selected is None or p.relative_to(root).parts[0] in selected)}


def sync(plugin):
    """仅对当前领域的未发布且未漂移快照做正常增量复制。"""
    domain=ROOT.name.removesuffix('-skills')
    metadata=plugin/'candidate-source.json'
    lock=json.loads(metadata.read_text())
    manifest=json.loads((plugin/'plugin.json').read_text())
    source_manifest=json.loads((ROOT/'skill-suite.json').read_text())
    external=lock.get('bundledSourceIdentity',{}).get('skills')
    if (manifest['name']!=domain or lock.get('sourceProject')!=ROOT.name or lock.get('sourceStatus')!='local-unpublished-candidate' or lock.get('releaseTag') is not None or not isinstance(external,list) or len(set(external))!=len(external)):raise ValueError('not_current_local_candidate')
    current=inventory(plugin/'skills',external)
    locked={path:digest for path,digest in lock['skillFileSha256'].items() if not transient_path(path)}
    if current!=locked:raise ValueError('preserve_modified_plugin_snapshot')
    incoming=inventory(ROOT/'skills',source_manifest['skills'])
    if set(current)-set(incoming):raise ValueError('source_removal_requires_review')
    for relative,digest in incoming.items():
        if current.get(relative)==digest:continue
        target=plugin/'skills'/relative
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()!=current[relative]:raise ValueError('concurrent_snapshot_change')
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/'skills'/relative,target)
    if inventory(plugin/'skills',source_manifest['skills'])!=incoming:raise ValueError('snapshot_copy_mismatch')
    lock['skillFileSha256']=incoming
    lock['sourceProject']=ROOT.name;lock['sourceVersion']=source_manifest['version'];lock['bundledSourceIdentity']={'sourceProject':ROOT.name,'sourceVersion':source_manifest['version'],'skills':source_manifest['skills'],'releaseTag':None}
    metadata.write_text(json.dumps(lock,ensure_ascii=False,indent=2)+'\n')
    return {'domain':domain,'skills':len(list((ROOT/'skills').glob('*/SKILL.md'))),'sourceRelease':'UNPUBLISHED','snapshot':'PASS'}


def upgrade_legacy_candidate(plugin):
    """将可核验的旧本地候选元数据升级到当前 schema，并保留原始副本。"""
    plugin=Path(plugin);metadata=plugin/'candidate-source.json';original=metadata.read_bytes();lock=json.loads(original)
    domain=ROOT.name.removesuffix('-skills');source=json.loads((ROOT/'skill-suite.json').read_text());manifest=json.loads((plugin/'plugin.json').read_text())
    if manifest.get('name')!=domain or lock.get('sourceProject')!=ROOT.name or lock.get('sourceStatus')!='local-unpublished-candidate' or lock.get('sourceVersion')!=source.get('version') or lock.get('releaseTag') is not None or any(key in lock for key in ('schemaVersion','candidateType','bundledSourceIdentity')):
        raise ValueError('legacy_candidate_not_migratable')
    actual=inventory(plugin/'skills',source['skills']);locked={path:digest for path,digest in lock.get('skillFileSha256',{}).items() if not transient_path(path)}
    if actual!=locked:raise ValueError('legacy_snapshot_drift')
    backup=metadata.with_name(metadata.name+'.legacy')
    if backup.exists():
        if backup.read_bytes()!=original:raise ValueError('legacy_backup_conflict')
    else:
        with backup.open('xb') as stream:
            stream.write(original);stream.flush();os.fsync(stream.fileno())
    lock.update({'schemaVersion':1,'candidateType':'local-unpublished-candidate','bundledSourceIdentity':{'sourceProject':ROOT.name,'sourceVersion':source['version'],'skills':source['skills'],'releaseTag':None}})
    if metadata.read_bytes()!=original:raise ValueError('candidate_metadata_changed')
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=plugin,prefix='.candidate-',delete=False) as stream:
            temporary=Path(stream.name);json.dump(lock,stream,ensure_ascii=False,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,metadata)
    finally:
        if temporary is not None and temporary.exists():temporary.unlink()
    return {'domain':domain,'migration':'PASS','backup':backup.name,'sourceRelease':'UNPUBLISHED'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plugin-root',type=Path,required=True);parser.add_argument('--migrate-legacy',action='store_true')
    args=parser.parse_args();result=upgrade_legacy_candidate(args.plugin_root) if args.migrate_legacy else sync(args.plugin_root);print(json.dumps(result,ensure_ascii=False))
