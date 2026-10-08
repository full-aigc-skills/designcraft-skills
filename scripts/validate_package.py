"""校验本地技能结构与不可变安装锁；不安装运行时。"""
from pathlib import Path
import hashlib
import json
import re
from urllib.parse import unquote, urlsplit

ROOT=Path(__file__).resolve().parents[1]

def validate():
    suite=json.loads((ROOT/'skill-suite.json').read_text())
    domain=suite['domain']
    expected=set(suite['skills'])
    routing=json.loads((ROOT/'skill-routing.json').read_text())
    routes=routing.get('routes',[])
    route_names=[item.get('skill') for item in routes if isinstance(item,dict)]
    if routing.get('schemaVersion')!=1 or routing.get('defaultSkill')!=f'{domain}-use' or len(routes)!=len(route_names) or set(route_names)!=expected or len(set(route_names))!=len(route_names) or not routing.get('unrelatedExamples'):
        raise ValueError('skill_routing_matrix_invalid')
    for item in routes:
        if not isinstance(item.get('intent'),str) or not item['intent'] or not isinstance(item.get('examples'),list) or not item['examples'] or any(not isinstance(example,str) or not example for example in item['examples']) or not isinstance(item.get('sideEffects'),str) or not item['sideEffects']:
            raise ValueError('skill_routing_matrix_invalid')
    if not isinstance(suite.get('version'),str) or not suite['version'] or not isinstance(suite.get('nativeVersion'),str):raise ValueError('skill_suite_identity_invalid')
    coverage=json.loads((ROOT/'command-coverage.json').read_text())
    actions=coverage.get('gatewayActions',[]);native_commands=coverage.get('nativeCommands',[])
    native_status=coverage.get('nativeCatalogStatus')
    research_path=coverage.get('researchSourceInventory')
    if research_path!='research-command-inventory.json':raise ValueError('research_inventory_invalid')
    research=json.loads((ROOT/research_path).read_text())
    research_files=research.get('sourceFiles',[]);research_commands=research.get('commands',[])
    revision=research.get('sourceRevision')
    if research.get('schemaVersion')!=1 or research.get('classification')!='RESEARCH_SOURCE_ONLY' or research.get('sourceProject')!='research/designcraft' or research.get('sourceEvidenceType')!='STATIC_SOURCE_SCAN' or not isinstance(revision,str) or not re.fullmatch(r'[0-9a-f]{40,64}',revision) or research.get('nativeCatalogStatus')!='NOT_RUN' or not isinstance(research_files,list) or not isinstance(research_commands,list):raise ValueError('research_inventory_invalid')
    if any(not isinstance(item,dict) or not isinstance(item.get('path'),str) or not item['path'] or not isinstance(item.get('sha256'),str) or not re.fullmatch(r'[0-9a-f]{64}',item['sha256']) for item in research_files):raise ValueError('research_inventory_invalid')
    research_paths=[item['path'] for item in research_files]
    if len(set(research_paths))!=len(research_paths):raise ValueError('research_inventory_invalid')
    if any(not isinstance(item,dict) or not isinstance(item.get('id'),str) or not item['id'] or not isinstance(item.get('module'),str) or item.get('validationStatus')!='RESEARCH_SOURCE_ONLY' or 'ownerSkill' in item for item in research_commands):raise ValueError('research_inventory_invalid')
    research_ids=[item['id'] for item in research_commands]
    if len(set(research_ids))!=len(research_ids) or research.get('commandCount')!=len(research_commands):raise ValueError('research_inventory_invalid')
    subcommands=research.get('cliSubcommands')
    if not isinstance(subcommands,list) or not subcommands or any(not isinstance(item,str) or not item for item in subcommands) or len(set(subcommands))!=len(subcommands):raise ValueError('research_inventory_invalid')
    action_ids=[item.get('action') for item in actions if isinstance(item,dict)]
    native_ids=[item.get('id') for item in native_commands if isinstance(item,dict)]
    if coverage.get('schemaVersion')!=1 or coverage.get('domain')!=domain or native_status not in ('NOT_RUN','DISCOVERED','VERIFIED') or len(action_ids)!=len(actions) or any(not isinstance(item,str) for item in action_ids) or len(set(action_ids))!=len(action_ids) or set(action_ids)!={'list','describe','check','run','receipt'}:raise ValueError('command_coverage_invalid')
    if len(native_ids)!=len(native_commands) or any(not isinstance(item,str) for item in native_ids) or len(set(native_ids))!=len(native_ids) or native_ids and native_status=='NOT_RUN':raise ValueError('command_coverage_invalid')
    native_identity=coverage.get('nativeCatalogIdentity')
    if native_status=='NOT_RUN':
        if native_identity is not None or native_commands:raise ValueError('native_catalog_identity_invalid')
    elif not isinstance(native_identity,dict) or not isinstance(native_identity.get('cliVersion'),str) or not native_identity['cliVersion'] or any(not isinstance(native_identity.get(key),str) or not re.fullmatch(r'[0-9a-f]{64}',native_identity[key]) for key in ('binarySha256','catalogSha256')):
        raise ValueError('native_catalog_identity_invalid')
    if native_status in ('DISCOVERED','VERIFIED'):
        evidence_path=coverage.get('nativeCatalogEvidence')
        if not isinstance(evidence_path,str) or not evidence_path or Path(evidence_path).is_absolute() or '..' in Path(evidence_path).parts:
            raise ValueError('native_catalog_evidence_invalid')
        catalog_path=ROOT/evidence_path
        if catalog_path.is_symlink() or not catalog_path.is_file():
            raise ValueError('native_catalog_evidence_invalid')
        catalog=json.loads(catalog_path.read_text(encoding='utf-8'))
        if not isinstance(catalog,list) or any(not isinstance(item,dict) or not isinstance(item.get('id'),str) or not item['id'] for item in catalog):
            raise ValueError('native_catalog_evidence_invalid')
        if hashlib.sha256(json.dumps(catalog,sort_keys=True,ensure_ascii=False).encode('utf-8')).hexdigest()!=native_identity['catalogSha256']:
            raise ValueError('native_catalog_evidence_invalid')
        catalog_ids=[item['id'] for item in catalog]
        if len(set(catalog_ids))!=len(catalog_ids) or set(native_ids)!=set(catalog_ids):
            raise ValueError('native_catalog_coverage_mismatch')
        if any(item.get('validationStatus')!='DISCOVERED' for item in native_commands):
            raise ValueError('native_catalog_unverified_command')
        lock=json.loads((ROOT/'skills'/f'{domain}-cli'/'scripts/runtime.lock.json').read_text(encoding='utf-8'))
        if native_identity['cliVersion']!=lock.get('resolvedVersion') or native_identity['binarySha256']!=lock.get('artifacts',{}).get('darwin-arm64',{}).get('binarySha256'):
            raise ValueError('native_catalog_identity_invalid')
    for item in actions:
        if item.get('ownerSkill') not in expected or item.get('validationStatus') not in ('STATIC','OFFLINE_TESTED','NATIVE_TESTED','HOST_TESTED'):raise ValueError('command_owner_invalid')
    for item in native_commands:
        if not isinstance(item.get('id'),str) or not item['id'] or item.get('ownerSkill') not in expected or item.get('validationStatus') not in ('DISCOVERED','DOCUMENTED','SIMULATED','NATIVE_TESTED','HOST_TESTED'):raise ValueError('command_owner_invalid')
    actual={p.name for p in (ROOT/'skills').iterdir() if p.is_dir()}
    if actual!=expected:raise ValueError('skill_set_mismatch')
    canonical=ROOT/'skills'/f'{domain}-use'/'scripts'
    resources=('bootstrap.py','cli.py','runtime.lock.json','commands.py','command_gateway.py')
    for name in sorted(expected):
        p=ROOT/'skills'/name
        if p.is_symlink():raise ValueError('skill_symlink')
        text=(p/'SKILL.md').read_text()
        if not text.startswith('---\n') or f'name: {name}\n' not in text or not re.search(r'^description:\s*\S',text,re.M):raise ValueError('skill_frontmatter_invalid')
        if len(text.splitlines())>=500:raise ValueError('skill_too_long')
        if '/mnt/skills/user' in text:raise ValueError('hardcoded_skill_path')
        if any(section not in text for section in ('## 路由范围','## 首次使用','## 当前场景','## 场景示例')) or '[场景示例](examples/workflow-cases.md)' not in text:
            raise ValueError('skill_workflow_quality_invalid:'+name+':entry_contract')
        for document in p.rglob('*.md'):
            body=document.read_text(encoding='utf-8')
            for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',body):
                target=target.strip().split(maxsplit=1)[0].strip('<>')
                parsed=urlsplit(target)
                if parsed.scheme or target.startswith('#') or not parsed.path:continue
                resolved=(document.parent/unquote(parsed.path)).resolve()
                try:resolved.relative_to(p.resolve())
                except ValueError as error:raise ValueError('cross_skill_relative_link: '+name) from error
                if not resolved.exists():raise ValueError('broken_skill_markdown_link: '+name+':'+target)
        cases_path=p/'examples/workflow-cases.md'
        if cases_path.is_symlink() or not cases_path.is_file():raise ValueError('skill_workflow_quality_invalid:'+name+':examples_missing')
        cases=cases_path.read_text(encoding='utf-8')
        sections=re.split(r'(?m)^## ',cases)
        success=next((section for section in sections if section.startswith('成功示例：')),None)
        recovery=next((section for section in sections if section.startswith('拒绝与恢复示例：')),None)
        if success is None or recovery is None:raise ValueError('skill_workflow_quality_invalid:'+name+':scenario_missing')
        if any(label not in success for label in ('**前置：**','**动作：**','**预期状态：**','**验收：**')):
            raise ValueError('skill_workflow_quality_invalid:'+name+':success_case_incomplete')
        if any(label not in recovery for label in ('**前置：**','**动作：**','**预期状态：**','**安全下一步：**')):
            raise ValueError('skill_workflow_quality_invalid:'+name+':recovery_case_incomplete')
        for resource in resources:
            file=p/'scripts'/resource
            if file.is_symlink() or file.read_bytes()!=(canonical/resource).read_bytes():raise ValueError('independent_resource_drift')
        lock=json.loads((p/'scripts/runtime.lock.json').read_text())
        if lock['artifact']!=domain+'-cli':raise ValueError('foreign_domain_runtime')
        for item in lock['artifacts'].values():
            for key in ('archiveSha256','binarySha256'):
                if not re.fullmatch('[0-9a-f]{64}',item[key]):raise ValueError('invalid_checksum')
    return {'domain':domain,'skills':len(expected),'structure':'PASS','nativeInstallation':'NOT_RUN','modelDispatch':'NOT_RUN'}

if __name__=='__main__':print(json.dumps(validate(),ensure_ascii=False))
