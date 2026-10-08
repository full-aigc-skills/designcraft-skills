"""独立技能源本地合同；不运行原生程序。"""
import importlib.util
import json
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
DOMAIN=ROOT.name.removesuffix('-skills')

class PackageContract(unittest.TestCase):
    def _validate_fixture(self, fixture):
        spec=importlib.util.spec_from_file_location('validator_fixture',fixture/'scripts/validate_package.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.ROOT=fixture
        return module.validate()

    def test_structure_and_resources(self):
        p=ROOT/'scripts/validate_package.py'
        spec=importlib.util.spec_from_file_location('validator',p)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertEqual(module.validate()['skills'],6)

    def test_broken_local_markdown_reference_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            fixture=Path(t)/'package';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__'))
            path=fixture/'skills/designcraft-use/SKILL.md';path.write_text(path.read_text()+'\n[missing](references/not-present.md)\n')
            spec=importlib.util.spec_from_file_location('validator_fixture',fixture/'scripts/validate_package.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.ROOT=fixture
            with self.assertRaisesRegex(ValueError,'broken_skill_markdown_link'):
                module.validate()

    def test_workflow_quality_requires_success_and_refusal_recovery_cases(self):
        mutations=(
            ('missing_example_link',lambda fixture:(fixture/'skills/designcraft-use/SKILL.md').write_text((fixture/'skills/designcraft-use/SKILL.md').read_text().replace('[场景示例](examples/workflow-cases.md)','')),'entry_contract'),
            ('missing_recovery_case',lambda fixture:(fixture/'skills/designcraft-use/examples/workflow-cases.md').write_text((fixture/'skills/designcraft-use/examples/workflow-cases.md').read_text().replace('## 拒绝与恢复示例：无关请求或结果未知','## 边界示例：无关请求或结果未知')),'scenario_missing'),
            ('missing_next_step',lambda fixture:(fixture/'skills/designcraft-use/examples/workflow-cases.md').write_text((fixture/'skills/designcraft-use/examples/workflow-cases.md').read_text().replace('**安全下一步：**','**后续：**')),'recovery_case_incomplete'),
        )
        for label,mutate,error in mutations:
            with self.subTest(contract=label),tempfile.TemporaryDirectory() as t:
                fixture=Path(t)/'package';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__','.DS_Store'))
                mutate(fixture)
                with self.assertRaisesRegex(ValueError,'skill_workflow_quality_invalid:designcraft-use:'+error):
                    self._validate_fixture(fixture)

    def test_cross_skill_relative_reference_is_rejected_even_when_target_exists(self):
        with tempfile.TemporaryDirectory() as t:
            fixture=Path(t)/'package';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__'))
            path=fixture/'skills/designcraft-use/SKILL.md';path.write_text(path.read_text()+'\n[other skill](../designcraft-cli/SKILL.md)\n')
            spec=importlib.util.spec_from_file_location('cross_skill_validator',fixture/'scripts/validate_package.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.ROOT=fixture
            with self.assertRaisesRegex(ValueError,'cross_skill_relative_link'):
                module.validate()

    def test_command_coverage_requires_a_single_valid_owner(self):
        with tempfile.TemporaryDirectory() as t:
            fixture=Path(t)/'package';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__'))
            path=fixture/'command-coverage.json';coverage=json.loads(path.read_text());coverage['gatewayActions'][0]['ownerSkill']='missing-skill';path.write_text(json.dumps(coverage))
            spec=importlib.util.spec_from_file_location('coverage_validator',fixture/'scripts/validate_package.py')
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.ROOT=fixture
            with self.assertRaisesRegex(ValueError,'command_owner_invalid'):
                module.validate()

    def test_native_catalog_requires_cli_binary_and_catalog_identity(self):
        with tempfile.TemporaryDirectory() as t:
            fixture=Path(t)/'package';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__','.DS_Store'))
            path=fixture/'command-coverage.json';coverage=json.loads(path.read_text());coverage['nativeCatalogStatus']='DISCOVERED';coverage['nativeCommands']=[{'id':'file.new','ownerSkill':'designcraft-cli','validationStatus':'DISCOVERED'}];path.write_text(json.dumps(coverage))
            with self.assertRaisesRegex(ValueError,'native_catalog_identity_invalid'):
                self._validate_fixture(fixture)

    def test_native_catalog_identity_accepts_versioned_hash_bound_inventory(self):
        with tempfile.TemporaryDirectory() as t:
            fixture=Path(t)/'package';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__','.DS_Store'))
            path=fixture/'command-coverage.json';coverage=json.loads(path.read_text());coverage['nativeCatalogStatus']='DISCOVERED';coverage['nativeCatalogIdentity']={'cliVersion':'0.2.1','binarySha256':'a'*64,'catalogSha256':'b'*64};coverage['nativeCommands']=[{'id':'file.new','ownerSkill':'designcraft-cli','validationStatus':'DISCOVERED'}];path.write_text(json.dumps(coverage))
            result=self._validate_fixture(fixture)
            self.assertEqual(result['nativeInstallation'],'NOT_RUN')

    def test_research_source_inventory_cannot_be_promoted_to_native_catalog(self):
        with tempfile.TemporaryDirectory() as t:
            fixture=Path(t)/'package';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__','.DS_Store'))
            path=fixture/'research-command-inventory.json';inventory=json.loads(path.read_text());inventory['commands'][0]['validationStatus']='NATIVE_TESTED';path.write_text(json.dumps(inventory))
            with self.assertRaisesRegex(ValueError,'research_inventory_invalid'):
                self._validate_fixture(fixture)

    def test_research_inventory_reference_keeps_native_catalog_not_run(self):
        coverage=json.loads((ROOT/'command-coverage.json').read_text())
        self.assertEqual(coverage['researchSourceInventory'],'research-command-inventory.json')
        self.assertEqual(coverage['nativeCatalogStatus'],'NOT_RUN')
        self.assertEqual(coverage['nativeCommands'],[])

    def test_routing_matrix_requires_every_skill_and_unrelated_examples(self):
        with tempfile.TemporaryDirectory() as t:
            fixture=Path(t)/'package';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__','.DS_Store'))
            path=fixture/'skill-routing.json';routing=json.loads(path.read_text());routing['routes'][0]['skill']='missing-skill';path.write_text(json.dumps(routing))
            with self.assertRaisesRegex(ValueError,'skill_routing_matrix_invalid'):
                self._validate_fixture(fixture)

    def test_invalid_skill_set_frontmatter_length_and_resource_are_rejected(self):
        mutations=(
            ('skill_set',lambda fixture:(fixture/'skills/extra').mkdir()),
            ('frontmatter',lambda fixture:(fixture/'skills/designcraft-use/SKILL.md').write_text('---\nname: wrong\ndescription: invalid\n---\n')),
            ('line_limit',lambda fixture:(fixture/'skills/designcraft-use/SKILL.md').write_text((fixture/'skills/designcraft-use/SKILL.md').read_text()+'\n'+'\n'.join('extra' for _ in range(500)))),
            ('resource_drift',lambda fixture:(fixture/'skills/designcraft-use/scripts/cli.py').write_text('drift')),
        )
        for label,mutate in mutations:
            with self.subTest(contract=label),tempfile.TemporaryDirectory() as t:
                fixture=Path(t)/'package';shutil.copytree(ROOT,fixture,ignore=shutil.ignore_patterns('openspec','__pycache__','.DS_Store'))
                mutate(fixture)
                with self.assertRaises(ValueError):
                    self._validate_fixture(fixture)

    def test_each_skill_gateway_runs_alone_in_python_isolated_mode(self):
        raw=[{'name':'doc_info','input_schema':{'type':'object','properties':{}}}] if DOMAIN=='printcraft' else [{'id':'file.new','label':'New','params':'','menu':['File']}]
        for source in sorted(p for p in (ROOT/'skills').iterdir() if p.is_dir()):
            with self.subTest(skill=source.name),tempfile.TemporaryDirectory(prefix='独立 技能 ') as t:
                root=Path(t);skill=root/source.name;shutil.copytree(source,skill)
                catalog=root/'catalog.json';catalog.write_text(json.dumps(raw))
                plan=root/'plan.json';plan.write_text(json.dumps({'domain':DOMAIN,'steps':[{'command':raw[0].get('name',raw[0].get('id')),'params':{}}]}))
                cli=[sys.executable,'-I','-B',str(skill/'scripts/commands.py')]
                for action,args in (('list',[]),('describe',[raw[0].get('name',raw[0].get('id'))]),('check',[str(plan)])):
                    with self.subTest(action=action):
                        out=subprocess.run([*cli,action,*args,'--catalog',str(catalog)],capture_output=True,text=True)
                        self.assertEqual(out.returncode,0,out.stdout+out.stderr)
                        reply=json.loads(out.stdout)
                        if action=='list':self.assertEqual(reply['count'],1)
                        if action=='describe':self.assertEqual(reply['id'],raw[0].get('name',raw[0].get('id')))
                        if action=='check':self.assertEqual(reply['structuralCheck'],'PASS')

    def test_invalid_native_subcommand_rejects_before_installation(self):
        with tempfile.TemporaryDirectory() as t:
            runtime=Path(t)/'runtime'
            out=subprocess.run([sys.executable,'-I','-B',str(ROOT/'skills'/f'{DOMAIN}-use'/'scripts/cli.py'),'--runtime-home',str(runtime),'--','sh'],capture_output=True,text=True)
            self.assertNotEqual(out.returncode,0)
            self.assertIn('unsupported_cli_subcommand',out.stderr)
            self.assertFalse(runtime.exists())

    def test_offline_catalog_cannot_start_run_or_create_output(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);catalog=root/'catalog.json';catalog.write_text(json.dumps([{'id':'file.new','label':'New','params':'','menu':['File']}]))
            plan=root/'plan.json';plan.write_text(json.dumps({'domain':DOMAIN,'steps':[{'command':'file.new','params':{}}]}))
            runtime=root/'runtime';output=root/'output'
            out=subprocess.run([sys.executable,'-I','-B',str(ROOT/'skills'/f'{DOMAIN}-use'/'scripts/commands.py'),'run',str(plan),'--catalog',str(catalog),'--runtime-home',str(runtime),'--output',str(output)],capture_output=True,text=True)
            self.assertNotEqual(out.returncode,0)
            self.assertIn('run_requires_live_catalog_and_new_output',out.stdout+out.stderr)
            self.assertFalse(runtime.exists())
            self.assertFalse(output.exists())

if __name__=='__main__':unittest.main()
