"""同步器必须保留用户漂移和已发布快照；只修改临时测试副本。"""
import importlib.util
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import shutil
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
DOMAIN=ROOT.name.removesuffix('-skills')

class SnapshotSyncContract(unittest.TestCase):
    def module(self):
        path=ROOT/'scripts/sync_local_snapshot.py'
        spec=importlib.util.spec_from_file_location('snapshot_sync',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def plugin_fixture(self,root):
        target=root/'plugin';shutil.copytree(ROOT/'skills',target/'skills')
        suite=json.loads((ROOT/'skill-suite.json').read_text());module=self.module();names=suite['skills']
        lock={'sourceStatus':'local-unpublished-candidate','sourceProject':ROOT.name,'sourceVersion':suite['version'],'bundledSourceIdentity':{'sourceProject':ROOT.name,'sourceVersion':suite['version'],'skills':names,'releaseTag':None},'skillFileSha256':module.inventory(target/'skills',names),'releaseTag':None}
        (target/'candidate-source.json').write_text(json.dumps(lock));(target/'plugin.json').write_text(json.dumps({'name':DOMAIN}))
        return target

    def test_user_snapshot_edits_are_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            target=self.plugin_fixture(Path(t))
            skill=target/'skills'/f'{DOMAIN}-use'/'SKILL.md'
            skill.write_text(skill.read_text()+'\nUser edit must survive\n')
            before=skill.read_bytes();lock=(target/'candidate-source.json').read_bytes()
            with self.assertRaisesRegex(ValueError,'preserve_modified_plugin_snapshot'):
                self.module().sync(target)
            self.assertEqual(skill.read_bytes(),before)
            self.assertEqual((target/'candidate-source.json').read_bytes(),lock)

    def test_published_source_identity_is_never_replaced_by_local_candidate(self):
        with tempfile.TemporaryDirectory() as t:
            target=self.plugin_fixture(Path(t))
            path=target/'candidate-source.json';data=json.loads(path.read_text());data['releaseTag']='v0.1.0';path.write_text(json.dumps(data))
            before=path.read_bytes()
            with self.assertRaisesRegex(ValueError,'not_current_local_candidate'):
                self.module().sync(target)
            self.assertEqual(path.read_bytes(),before)

    def test_legacy_candidate_migration_keeps_backup_and_revalidates_snapshot(self):
        with tempfile.TemporaryDirectory() as t:
            target=self.plugin_fixture(Path(t));metadata=target/'candidate-source.json';original=metadata.read_bytes()
            legacy=json.loads(original);legacy.pop('bundledSourceIdentity');metadata.write_text(json.dumps(legacy))
            original=metadata.read_bytes()
            result=self.module().upgrade_legacy_candidate(target)
            updated=json.loads(metadata.read_text());backup=metadata.with_name(metadata.name+'.legacy')
            self.assertEqual(backup.read_bytes(),original)
            self.assertEqual((result['migration'],updated['schemaVersion'],updated['bundledSourceIdentity']['releaseTag']),('PASS',1,None))
            self.assertEqual(self.module().sync(target)['snapshot'],'PASS')

    def test_legacy_candidate_migration_refuses_snapshot_drift(self):
        with tempfile.TemporaryDirectory() as t:
            target=self.plugin_fixture(Path(t));metadata=target/'candidate-source.json';original=metadata.read_bytes()
            legacy=json.loads(original);legacy.pop('bundledSourceIdentity');metadata.write_text(json.dumps(legacy));original=metadata.read_bytes()
            skill=target/'skills'/f'{DOMAIN}-use'/'SKILL.md';skill.write_text(skill.read_text()+'\nlocal drift\n')
            with self.assertRaisesRegex(ValueError,'legacy_snapshot_drift'):
                self.module().upgrade_legacy_candidate(target)
            self.assertEqual(metadata.read_bytes(),original)
            self.assertFalse(metadata.with_name(metadata.name+'.legacy').exists())

    def test_source_project_identity_mismatch_is_refused(self):
        with tempfile.TemporaryDirectory() as t:
            target=self.plugin_fixture(Path(t));path=target/'candidate-source.json';data=json.loads(path.read_text());data['sourceProject']='foreign-skills';path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'not_current_local_candidate'):
                self.module().sync(target)

    def test_sync_runs_against_independent_source_and_plugin_fixture(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/'fixture-skills';plugin=root/'fixture-plugin'
            source_skill=source/'skills/fixture-use/SKILL.md';source_skill.parent.mkdir(parents=True);source_skill.write_text('version two')
            (source/'skill-suite.json').write_text(json.dumps({'domain':'fixture','version':'2.0.0','skills':['fixture-use']}))
            plugin_skill=plugin/'skills/fixture-use/SKILL.md';plugin_skill.parent.mkdir(parents=True);plugin_skill.write_text('version one')
            local=plugin/'skills/fixture-harness/SKILL.md';local.parent.mkdir(parents=True);local.write_text('local skill stays')
            digest=hashlib.sha256(plugin_skill.read_bytes()).hexdigest()
            lock={'sourceStatus':'local-unpublished-candidate','sourceProject':'fixture-skills','sourceVersion':'1.0.0','bundledSourceIdentity':{'sourceProject':'fixture-skills','sourceVersion':'1.0.0','skills':['fixture-use'],'releaseTag':None},'skillFileSha256':{'fixture-use/SKILL.md':digest},'releaseTag':None}
            (plugin/'candidate-source.json').write_text(json.dumps(lock));(plugin/'plugin.json').write_text(json.dumps({'name':'fixture'}))
            module=self.module();module.ROOT=source
            result=module.sync(plugin)
            refreshed=json.loads((plugin/'candidate-source.json').read_text())
            self.assertEqual((result['snapshot'],plugin_skill.read_text(),local.read_text()),('PASS','version two','local skill stays'))
            self.assertEqual((refreshed['sourceVersion'],refreshed['bundledSourceIdentity']['skills']),('2.0.0',['fixture-use']))

    def test_interrupted_copy_leaves_candidate_unverifiable(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/'fixture-skills';plugin=root/'fixture-plugin';(source/'skills/fixture-use').mkdir(parents=True);(plugin/'skills/fixture-use').mkdir(parents=True)
            source_files={'a.md':'new a','b.md':'new b'};old_files={'a.md':'old a','b.md':'old b'}
            for name,value in source_files.items():(source/'skills/fixture-use'/name).write_text(value)
            for name,value in old_files.items():(plugin/'skills/fixture-use'/name).write_text(value)
            (source/'skill-suite.json').write_text(json.dumps({'domain':'fixture','version':'2.0.0','skills':['fixture-use']}))
            hashes={f'fixture-use/{name}':hashlib.sha256(value.encode()).hexdigest() for name,value in old_files.items()}
            lock={'sourceStatus':'local-unpublished-candidate','sourceProject':'fixture-skills','sourceVersion':'1.0.0','bundledSourceIdentity':{'sourceProject':'fixture-skills','sourceVersion':'1.0.0','skills':['fixture-use'],'releaseTag':None},'skillFileSha256':hashes,'releaseTag':None}
            (plugin/'candidate-source.json').write_text(json.dumps(lock));(plugin/'plugin.json').write_text(json.dumps({'name':'fixture'}))
            module=self.module();module.ROOT=source;copy=shutil.copyfile;calls=[]
            def interrupted(src,dst):
                calls.append(src);copy(src,dst)
                if len(calls)==1:raise OSError('simulated interruption')
            with patch.object(module.shutil,'copyfile',side_effect=interrupted):
                with self.assertRaisesRegex(OSError,'simulated interruption'):module.sync(plugin)
            current=module.inventory(plugin/'skills',['fixture-use'])
            self.assertNotEqual(current,lock['skillFileSha256'])
            with self.assertRaisesRegex(ValueError,'preserve_modified_plugin_snapshot'):
                module.sync(plugin)

    def test_source_file_removal_requires_review(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/'fixture-skills';plugin=root/'fixture-plugin'
            src=source/'skills/fixture-use/SKILL.md';src.parent.mkdir(parents=True);src.write_text('current source')
            current=plugin/'skills/fixture-use';current.mkdir(parents=True);(current/'SKILL.md').write_text('current source');(current/'obsolete.md').write_text('old source file')
            (source/'skill-suite.json').write_text(json.dumps({'domain':'fixture','version':'2.0.0','skills':['fixture-use']}))
            inventory={'fixture-use/SKILL.md':hashlib.sha256(b'current source').hexdigest(),'fixture-use/obsolete.md':hashlib.sha256(b'old source file').hexdigest()}
            lock={'sourceStatus':'local-unpublished-candidate','sourceProject':'fixture-skills','sourceVersion':'1.0.0','bundledSourceIdentity':{'sourceProject':'fixture-skills','sourceVersion':'1.0.0','skills':['fixture-use'],'releaseTag':None},'skillFileSha256':inventory,'releaseTag':None}
            (plugin/'candidate-source.json').write_text(json.dumps(lock));(plugin/'plugin.json').write_text(json.dumps({'name':'fixture'}))
            module=self.module();module.ROOT=source
            with self.assertRaisesRegex(ValueError,'source_removal_requires_review'):module.sync(plugin)

    def test_source_symlink_is_rejected_before_any_snapshot_copy(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/'fixture-skills';plugin=root/'fixture-plugin';skill=source/'skills/fixture-use';skill.mkdir(parents=True)
            (skill/'SKILL.md').write_text('source skill');outside=root/'outside.txt';outside.write_text('outside');(skill/'escape.txt').symlink_to(outside)
            (source/'skill-suite.json').write_text(json.dumps({'domain':'fixture','version':'2.0.0','skills':['fixture-use']}))
            plugin_skill=plugin/'skills/fixture-use/SKILL.md';plugin_skill.parent.mkdir(parents=True);plugin_skill.write_text('source skill')
            hashes={'fixture-use/SKILL.md':hashlib.sha256(b'source skill').hexdigest()}
            lock={'sourceStatus':'local-unpublished-candidate','sourceProject':'fixture-skills','sourceVersion':'2.0.0','bundledSourceIdentity':{'sourceProject':'fixture-skills','sourceVersion':'2.0.0','skills':['fixture-use'],'releaseTag':None},'skillFileSha256':hashes,'releaseTag':None}
            (plugin/'candidate-source.json').write_text(json.dumps(lock));(plugin/'plugin.json').write_text(json.dumps({'name':'fixture'}))
            module=self.module();module.ROOT=source
            with self.assertRaisesRegex(ValueError,'snapshot_symlink'):module.sync(plugin)
            self.assertEqual(plugin_skill.read_text(),'source skill')

    def test_python_and_desktop_cache_files_are_excluded_from_snapshot_identity(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);skill=root/'skills/fixture-use';(skill/'scripts/__pycache__').mkdir(parents=True)
            (skill/'SKILL.md').write_text('source skill');(skill/'scripts/run.pyc').write_bytes(b'bytecode');(skill/'scripts/__pycache__/run.cpython-314.pyc').write_bytes(b'cached');(skill/'.DS_Store').write_bytes(b'desktop')
            inventory=self.module().inventory(root/'skills',['fixture-use'])
            self.assertEqual(set(inventory),{'fixture-use/SKILL.md'})

if __name__=='__main__':unittest.main()
