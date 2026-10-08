"""Source acceptance evidence expires when its bound package or inputs change."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('source_evidence',ROOT/'scripts/evidence_freshness.py')
MODULE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class SourceEvidenceFreshness(unittest.TestCase):
    def fixture(self,root):
        (root/'skills/demo/scripts').mkdir(parents=True)
        (root/'scripts').mkdir()
        (root/'tests').mkdir()
        (root/'evidence').mkdir()
        (root/'skill-suite.json').write_text(json.dumps({'version':'0.1.0','nativeVersion':'0.2.1'}))
        (root/'command-coverage.json').write_text(json.dumps({'schemaVersion':1,'nativeCatalogStatus':'NOT_RUN'}))
        (root/'research-command-inventory.json').write_text(json.dumps({'sourceRevision':'a'*40}))
        (root/'skills/demo/scripts/runtime.lock.json').write_text(json.dumps({'artifact':'designcraft-cli','resolvedVersion':'0.2.1','artifacts':{'darwin-arm64':{'binarySha256':'b'*64}}}))
        (root/'scripts/validator.py').write_text('validator')
        (root/'tests/input.py').write_text('test input')
        (root/'evidence/report.json').write_text('{"status":"PASS"}')
        (root/'project-status.json').write_text(json.dumps({'offlineTests':'PASS','packageValidation':'PASS','nativeInstallation':'NOT_RUN','ci':'NOT_RUN','hostDiscovery':'NOT_RUN','targetPlatformAcceptance':'NOT_RUN','modelDispatch':'NOT_RUN','creativeAcceptance':'NOT_RUN','published':False}))

    def manifest(self,root):
        record=MODULE.create_record(root,record_id='offline',layer='offline',status='PASS',run_id=str(uuid.uuid4()),observed_at='2026-10-08T00:00:00Z',input_paths=['tests/input.py'],artifact_paths=['evidence/report.json'],environment={'os':'macOS','machine':'arm64','python':'3.14.3'})
        return {'schemaVersion':1,'records':[record,{'id':'native','layer':'native','status':'NOT_RUN'}]}

    def test_current_source_evidence_passes_and_unrun_layers_remain_visible(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root)
            result=MODULE.evaluate_manifest(root,self.manifest(root),environment={'os':'macOS','machine':'arm64','python':'3.14.3'})
            self.assertEqual(result,{'offline':'PASS','native':'NOT_RUN'})

    def test_source_code_runtime_catalog_input_artifact_and_environment_drift_stales_evidence(self):
        mutations=(
            ('scripts/validator.py','source'),
            ('skills/demo/scripts/runtime.lock.json','runtime'),
            ('command-coverage.json','catalog'),
            ('tests/input.py','input'),
            ('evidence/report.json','artifact'),
        )
        for relative,label in mutations:
            with self.subTest(subject=label),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);self.fixture(root);manifest=self.manifest(root)
                path=root/relative;path.write_text(path.read_text()+' drift')
                result=MODULE.evaluate_manifest(root,manifest,environment={'os':'macOS','machine':'arm64','python':'3.14.3'})
                self.assertEqual(result['offline'],'STALE')
                self.assertEqual(result['native'],'NOT_RUN')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root);manifest=self.manifest(root)
            result=MODULE.evaluate_manifest(root,manifest,environment={'os':'Windows','machine':'arm64','python':'3.14.3'})
            self.assertEqual(result['offline'],'STALE')

    def test_status_sources_must_match_every_recorded_acceptance_layer(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);self.fixture(root)
            statuses={'offline-tests':'PASS','package-validation':'PASS','native-runtime':'NOT_RUN','ci':'NOT_RUN','host':'NOT_RUN','target-platform':'NOT_RUN','model-dispatch':'NOT_RUN','creative':'NOT_RUN','release':'NOT_RUN'}
            self.assertEqual(MODULE.status_mismatches(root,statuses),[])
            statuses['native-runtime']='PASS'
            self.assertEqual(MODULE.status_mismatches(root,statuses),['native-runtime'])

if __name__=='__main__':unittest.main()
