"""Compare a pinned static inventory with a read-only DesignCraft research checkout."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
MODULE_RE=re.compile(r'^\s*(?:pub(?:\([^)]*\))?\s+)?mod\s+([A-Za-z_]\w*)\s*;',re.M)
COMMAND_RE=re.compile(r'\bcmd!\s*\(\s*(?:(?:query|noundo)\s+)?"([^"]+)"')
SUBCOMMAND_RE=re.compile(r'Some\(([^)]*)\)\s*=>')
STRING_RE=re.compile(r'"([^"]+)"')

def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build_inventory(source_root, revision):
    """Build a static source inventory; it does not establish installed CLI support."""
    source_root=Path(source_root).resolve()
    main=source_root/'apps/designcraft-cli/src/main.rs'
    registry=source_root/'crates/engine/src/cmd/mod.rs'
    if not main.is_file() or not registry.is_file():
        raise ValueError('research_source_layout_invalid')
    main_text=main.read_text(encoding='utf-8')
    match_start=main_text.find('match args.first()')
    match_end=main_text.find('\nfn report',match_start)
    if match_start<0 or match_end<0:
        raise ValueError('research_cli_dispatch_not_found')
    subcommands=[]
    for arm in SUBCOMMAND_RE.findall(main_text[match_start:match_end]):
        subcommands.extend(STRING_RE.findall(arm))
    if not subcommands:
        raise ValueError('research_cli_subcommands_not_found')

    source_files={main.relative_to(source_root).as_posix():main,registry.relative_to(source_root).as_posix():registry}
    command_root=registry.parent
    commands=[]
    for module in MODULE_RE.findall(registry.read_text(encoding='utf-8')):
        flat_path=command_root/f'{module}.rs'
        nested_root=command_root/module
        module_files=[flat_path] if flat_path.is_file() else sorted(nested_root.rglob('*.rs')) if nested_root.is_dir() else []
        if not module_files:
            raise ValueError('research_command_module_missing:'+module)
        for path in module_files:
            source_files[path.relative_to(source_root).as_posix()]=path
            submodule=path.relative_to(command_root).with_suffix('').as_posix()
            if submodule.endswith('/mod'):
                submodule=submodule[:-4]
            for command_id in COMMAND_RE.findall(path.read_text(encoding='utf-8')):
                commands.append({'id':command_id,'module':submodule,'validationStatus':'RESEARCH_SOURCE_ONLY'})
    ids=[item['id'] for item in commands]
    if len(ids)!=len(set(ids)):
        raise ValueError('research_command_id_duplicate')
    files=[{'path':name,'sha256':_sha256(path)} for name,path in sorted(source_files.items())]
    return {
        'schemaVersion':1,
        'classification':'RESEARCH_SOURCE_ONLY',
        'sourceProject':'research/designcraft',
        'sourceRevision':revision,
        'sourceEvidenceType':'STATIC_SOURCE_SCAN',
        'sourceFiles':files,
        'cliSubcommands':list(dict.fromkeys(subcommands)),
        'commandCount':len(commands),
        'commands':commands,
        'nativeCatalogStatus':'NOT_RUN',
    }

def inventory_matches(pinned, source_root, revision):
    """Return true only when revision, source hashes, and parsed inventory all match."""
    try:
        return pinned==build_inventory(source_root,revision)
    except (OSError,UnicodeError,ValueError):
        return False

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',required=True,type=Path,help='read-only research/designcraft checkout')
    parser.add_argument('--inventory',type=Path,default=ROOT/'research-command-inventory.json')
    args=parser.parse_args(argv)
    try:
        revision=subprocess.run(['git','-C',str(args.source_root),'rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip()
        pinned=json.loads(args.inventory.read_text(encoding='utf-8'))
    except (OSError,subprocess.CalledProcessError,json.JSONDecodeError) as error:
        print(f'research_inventory_unavailable: {error}',file=sys.stderr)
        return 2
    if not re.fullmatch(r'[0-9a-f]{40,64}',revision) or not inventory_matches(pinned,args.source_root,revision):
        print('research_inventory_stale',file=sys.stderr)
        return 1
    print(json.dumps({'status':'PASS','classification':pinned['classification'],'sourceRevision':revision,'staticCommandCount':pinned['commandCount'],'nativeCatalogStatus':pinned['nativeCatalogStatus']},ensure_ascii=False))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
