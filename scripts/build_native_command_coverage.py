"""从固定 CLI 原生命令目录构造可校验的唯一技能归属表。"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE='evidence/native/designcraft-cli-0.2.1/command-catalog.json'

def owner_for(command_id):
    """按技能声明的用户任务边界分配命令；未细分的编辑操作归版面技能。"""
    if command_id.startswith(('file.export','file.print','file.package')) or command_id=='book.exportPdf':
        return 'designcraft-cli-export'
    prefix=command_id.split('.',1)[0]
    if prefix in {'document','book','article','story','note','footnote','endnote','xref','index','hyperlink','bookmark','variables','xml'}:
        return 'designcraft-cli-document'
    if prefix=='file' and command_id!='file.place':
        return 'designcraft-cli-document'
    return 'designcraft-cli-layout'

def build(catalog_path):
    path=Path(catalog_path).resolve()
    if path.is_symlink() or not path.is_file():raise ValueError('native_catalog_missing_or_symlink')
    catalog=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(catalog,list) or any(not isinstance(item,dict) or not isinstance(item.get('id'),str) or not item['id'] for item in catalog):raise ValueError('native_catalog_shape_invalid')
    ids=[item['id'] for item in catalog]
    if len(set(ids))!=len(ids):raise ValueError('native_catalog_duplicate_id')
    lock=json.loads((ROOT/'skills/designcraft-cli/scripts/runtime.lock.json').read_text(encoding='utf-8'))
    if lock.get('resolvedVersion')!='0.2.1':raise ValueError('native_cli_version_not_fixed')
    binary=lock.get('artifacts',{}).get('darwin-arm64',{}).get('binarySha256')
    if not isinstance(binary,str):raise ValueError('native_cli_binary_identity_missing')
    return {
        'schemaVersion':1,
        'domain':'designcraft',
        'nativeCatalogStatus':'DISCOVERED',
        'nativeCatalogEvidence':EVIDENCE,
        'researchSourceInventory':'research-command-inventory.json',
        'nativeCatalogIdentity':{
            'cliVersion':lock['resolvedVersion'],
            'binarySha256':binary,
            'catalogSha256':hashlib.sha256(json.dumps(catalog,sort_keys=True,ensure_ascii=False).encode('utf-8')).hexdigest(),
        },
        'gatewayActions':[
            {'action':action,'ownerSkill':'designcraft-cli','validationStatus':'OFFLINE_TESTED'}
            for action in ('list','describe','check','run','receipt')
        ],
        'nativeCommands':[
            {'id':command_id,'ownerSkill':owner_for(command_id),'validationStatus':'DISCOVERED'}
            for command_id in ids
        ],
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--catalog',default=str(ROOT/EVIDENCE))
    parser.add_argument('--output',default=str(ROOT/'command-coverage.json'))
    args=parser.parse_args()
    output=Path(args.output)
    output.write_text(json.dumps(build(args.catalog),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'commands':len(json.loads(Path(args.catalog).read_text(encoding='utf-8'))),'output':str(output)},ensure_ascii=False))

if __name__=='__main__':main()
