"""Bind layered source acceptance evidence to the current package, runtime and files."""
from datetime import datetime
import hashlib
import json
import platform
from pathlib import Path, PurePosixPath
import sys
import uuid

EXCLUDED={'evidence','evidence-manifest.json','.git','__pycache__'}

def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()

def canonical_digest(value):
    return digest_bytes(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())

def _files(root):
    root=Path(root);result=[]
    for path in sorted(root.rglob('*')):
        relative=path.relative_to(root)
        if any(part in EXCLUDED for part in relative.parts) or path.suffix in ('.pyc','.pyo') or path.name=='.DS_Store':continue
        if path.is_symlink():raise ValueError('evidence_tree_symlink:'+relative.as_posix())
        if path.is_file():result.append((relative.as_posix(),digest_bytes(path.read_bytes())))
    return result

def current_environment():
    return {'os':platform.system(),'machine':platform.machine(),'python':platform.python_version()}

def current_bindings(root):
    root=Path(root).resolve();suite=json.loads((root/'skill-suite.json').read_text(encoding='utf-8'))
    runtime_files=sorted((root/'skills').rglob('runtime.lock.json'))
    if not runtime_files:raise ValueError('runtime_lock_missing')
    runtime_identity=[]
    for path in runtime_files:
        lock=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(lock.get('artifact'),str) or not isinstance(lock.get('resolvedVersion'),str) or not isinstance(lock.get('artifacts'),dict):raise ValueError('runtime_lock_invalid')
        runtime_identity.append({'path':path.relative_to(root).as_posix(),'artifact':lock['artifact'],'version':lock['resolvedVersion'],'artifacts':lock['artifacts']})
    return {
        'packageVersion':suite.get('version'),
        'nativeVersion':suite.get('nativeVersion'),
        'packageTreeSha256':canonical_digest(_files(root)),
        'skillSuiteSha256':digest_bytes((root/'skill-suite.json').read_bytes()),
        'commandCoverageSha256':digest_bytes((root/'command-coverage.json').read_bytes()),
        'researchInventorySha256':digest_bytes((root/'research-command-inventory.json').read_bytes()),
        'runtimeLockSha256':canonical_digest(runtime_identity),
        'expectedNativeBinarySha256':sorted({artifact['binarySha256'] for item in runtime_identity for artifact in item['artifacts'].values() if isinstance(artifact,dict) and isinstance(artifact.get('binarySha256'),str)}),
    }

def _file_records(root,paths):
    root=Path(root).resolve();result=[]
    for raw in paths:
        relative=PurePosixPath(raw)
        if relative.is_absolute() or '..' in relative.parts or not relative.parts:raise ValueError('evidence_path_invalid:'+str(raw))
        path=root.joinpath(*relative.parts)
        if path.is_symlink() or not path.is_file():raise ValueError('evidence_file_missing_or_symlink:'+str(raw))
        result.append({'path':relative.as_posix(),'sha256':digest_bytes(path.read_bytes())})
    result.sort(key=lambda item:item['path'])
    if len({item['path'] for item in result})!=len(result):raise ValueError('evidence_path_duplicate')
    return result

def create_record(root,record_id,layer,status,run_id,observed_at,input_paths,artifact_paths,environment=None):
    if status not in ('PASS','FAIL'):raise ValueError('evidence_record_status_invalid')
    try:uuid.UUID(run_id)
    except (ValueError,TypeError,AttributeError) as error:raise ValueError('evidence_run_id_invalid') from error
    datetime.fromisoformat(observed_at.replace('Z','+00:00'))
    return {'id':record_id,'layer':layer,'status':status,'runId':run_id,'observedAt':observed_at,'environment':environment or current_environment(),'bindings':current_bindings(root),'inputs':_file_records(root,input_paths),'artifacts':_file_records(root,artifact_paths)}

def evaluate_manifest(root,manifest,environment=None):
    if not isinstance(manifest,dict) or manifest.get('schemaVersion')!=1 or not isinstance(manifest.get('records'),list):raise ValueError('evidence_manifest_invalid')
    environment=environment or current_environment();result={}
    for record in manifest['records']:
        if not isinstance(record,dict) or not isinstance(record.get('id'),str) or not record['id'] or not isinstance(record.get('layer'),str) or not record['layer'] or record.get('status') not in ('PASS','FAIL','NOT_RUN') or record['id'] in result:raise ValueError('evidence_record_invalid')
        if record['status']=='NOT_RUN':result[record['id']]='NOT_RUN';continue
        stale=False
        try:
            uuid.UUID(record.get('runId',''));datetime.fromisoformat(record.get('observedAt','').replace('Z','+00:00'))
            stale=(record.get('bindings')!=current_bindings(root) or record.get('environment')!=environment or record.get('inputs')!=_file_records(root,[item['path'] for item in record.get('inputs',[])]) or record.get('artifacts')!=_file_records(root,[item['path'] for item in record.get('artifacts',[])]))
        except (ValueError,TypeError,KeyError,AttributeError,OSError):stale=True
        result[record['id']]='STALE' if stale else record['status']
    return result

def status_mismatches(root,statuses):
    root=Path(root)
    project=json.loads((root/'project-status.json').read_text(encoding='utf-8'))
    expected={
        'offline-tests':project.get('offlineTests'),
        'package-validation':project.get('packageValidation'),
        'native-runtime':project.get('nativeInstallation'),
        'ci':project.get('ci'),
        'host':project.get('hostDiscovery'),
        'target-platform':project.get('targetPlatformAcceptance'),
        'model-dispatch':project.get('modelDispatch'),
        'creative':project.get('creativeAcceptance'),
        'release':'PASS' if project.get('published') is True else 'NOT_RUN',
    }
    return [layer for layer,value in expected.items() if statuses.get(layer)!=value]

def main(argv=None):
    args=list(sys.argv[1:] if argv is None else argv)
    if len(args)!=1:raise SystemExit('usage: evidence_freshness.py <evidence-manifest.json>')
    manifest=json.loads(Path(args[0]).read_text(encoding='utf-8'))
    root=Path(__file__).resolve().parents[1]
    statuses=evaluate_manifest(root,manifest)
    mismatches=status_mismatches(root,statuses)
    print(json.dumps({'records':statuses,'statusSourcesMatch':not mismatches,'statusMismatches':mismatches,'allRecordedEvidenceCurrent':all(value not in ('STALE','FAIL') for value in statuses.values()),'allAcceptanceLayersPassed':all(value=='PASS' for value in statuses.values())},ensure_ascii=False,sort_keys=True))
    return 1 if 'STALE' in statuses.values() or 'FAIL' in statuses.values() or mismatches else 0

if __name__=='__main__':raise SystemExit(main())
