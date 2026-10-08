"""AV-02 artifact identity stays separate from native reopen evidence."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'skills/designcraft-cli-export/scripts/artifact_manifest.py'
SPEC=importlib.util.spec_from_file_location('artifact_manifest',SCRIPT)
MODULE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class ArtifactManifestContract(unittest.TestCase):
    def fixture(self,root):
        artifacts=root/'deliverables';artifacts.mkdir()
        project=artifacts/'book.designcraft';project.write_bytes(b'native project')
        pdf=artifacts/'book.pdf';pdf.write_bytes(b'pdf export')
        def item(identifier,kind,path,fmt):
            data=path.read_bytes()
            return {'id':identifier,'kind':kind,'path':path.name,'format':fmt,'byteCount':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        manifest={
            'schemaVersion':1,
            'runId':str(uuid.uuid4()),
            'projectArtifactId':'project',
            'artifacts':[item('project','project',project,'designcraft'),item('pdf','export',pdf,'pdf')],
            'expectations':{'pageCount':1,'pageDimensionsMm':[{'page':1,'width':210.0,'height':297.0}],'criticalText':['Annual report'],'linkedAssets':[{'path':'images/cover.png','sha256':'a'*64}]},
            'reopenCheck':{'status':'NOT_RUN','sessionId':None,'projectSha256':None,'pageCount':None,'pageDimensionsMm':[],'criticalText':[],'linkedAssets':[],'verifiedBy':None,'verifiedAt':None}
        }
        return artifacts,manifest

    def test_files_are_bound_but_not_run_reopen_does_not_claim_acceptance(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);artifacts,manifest=self.fixture(root)
            result=MODULE.validate_manifest(artifacts,manifest)
            self.assertEqual(result['artifactIdentity'],'PASS')
            self.assertEqual(result['reopenEvidence'],'NOT_RUN')
            self.assertFalse(result['completeAcceptance'])

    def test_cli_preserves_not_run_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);artifacts,manifest=self.fixture(root);manifest_path=root/'manifest.json';manifest_path.write_text(json.dumps(manifest))
            result=subprocess.run([sys.executable,'-I','-B',str(SCRIPT),'--root',str(artifacts),'--manifest',str(manifest_path)],capture_output=True,text=True)
            payload=json.loads(result.stdout)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(payload['status'],'NOT_RUN')
            self.assertEqual(payload['result']['reopenEvidence'],'NOT_RUN')
            self.assertFalse(payload['result']['completeAcceptance'])

    def test_matching_reopen_evidence_is_bound_to_project_and_expectations(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);artifacts,manifest=self.fixture(root);project=artifacts/'book.designcraft'
            manifest['reopenCheck']={'status':'PASS','sessionId':'new-session-2','projectSha256':hashlib.sha256(project.read_bytes()).hexdigest(),'pageCount':1,'pageDimensionsMm':[{'page':1,'width':210.0,'height':297.0}],'criticalText':['Annual report'],'linkedAssets':[{'path':'images/cover.png','sha256':'a'*64}],'verifiedBy':'reviewer','verifiedAt':'2026-10-08T00:00:00Z'}
            result=MODULE.validate_manifest(artifacts,manifest)
            self.assertEqual(result['status'],'PASS')
            self.assertEqual(result['reopenEvidence'],'PASS')
            self.assertFalse(result['completeAcceptance'])

    def test_missing_project_and_receipt_paths_cannot_count_as_artifacts(self):
        mutations=('missing_project','receipt_path')
        for mutation in mutations:
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);artifacts,manifest=self.fixture(root)
                if mutation=='missing_project':manifest['artifacts']=manifest['artifacts'][1:]
                else:manifest['artifacts'][1]['path']='receipt.json'
                with self.assertRaises(ValueError):MODULE.validate_manifest(artifacts,manifest)

    def test_traversal_symlinks_and_identity_drift_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as outside:
            root=Path(temp);artifacts,manifest=self.fixture(root)
            manifest['artifacts'][0]['path']='../outside.designcraft'
            with self.assertRaisesRegex(ValueError,'artifact_path_invalid'):MODULE.validate_manifest(artifacts,manifest)
            manifest['artifacts'][0]['path']='book.designcraft'
            (artifacts/'linked.pdf').symlink_to(Path(outside)/'external.pdf')
            manifest['artifacts'][1]['path']='linked.pdf'
            with self.assertRaisesRegex(ValueError,'artifact_file_invalid'):MODULE.validate_manifest(artifacts,manifest)
            manifest['artifacts'][1]['path']='book.pdf';manifest['artifacts'][1]['sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'artifact_identity_mismatch'):MODULE.validate_manifest(artifacts,manifest)

    def test_reopen_page_content_and_link_mismatches_are_not_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);artifacts,manifest=self.fixture(root);project=artifacts/'book.designcraft'
            manifest['reopenCheck']={'status':'PASS','sessionId':'new-session-2','projectSha256':hashlib.sha256(project.read_bytes()).hexdigest(),'pageCount':2,'pageDimensionsMm':[{'page':1,'width':210.0,'height':297.0}],'criticalText':[],'linkedAssets':[],'verifiedBy':'reviewer','verifiedAt':'2026-10-08T00:00:00Z'}
            with self.assertRaisesRegex(ValueError,'reopen_page_count_mismatch'):MODULE.validate_manifest(artifacts,manifest)

if __name__=='__main__':unittest.main()
