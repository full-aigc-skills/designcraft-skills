"""AV-03 page reviews bind rubric, project, previews and reviewer provenance."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'skills/designcraft-cli-export/scripts/page_review.py'
SPEC=importlib.util.spec_from_file_location('page_review',SCRIPT)
MODULE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
CRITERIA=('hierarchy','whitespace','alignment','readability','cropping','crossPageConsistency')

class PageReviewContract(unittest.TestCase):
    def fixture(self,root,reviewer_kind='human'):
        output=root/'deliverables';output.mkdir()
        project=output/'book.designcraft';project.write_bytes(b'project bytes')
        preview=output/'page-1.png';preview.write_bytes(b'preview pixels')
        brief=output/'brief.md';brief.write_text('Single page, readable title')
        sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
        run_id=str(uuid.uuid4())
        artifact={'schemaVersion':1,'runId':run_id,'projectArtifactId':'project','artifacts':[{'id':'project','kind':'project','path':project.name,'format':'designcraft','byteCount':project.stat().st_size,'sha256':sha(project)}],
            'expectations':{'pageCount':1,'pageDimensionsMm':[{'page':1,'width':210.0,'height':297.0}],'criticalText':['Title'],'linkedAssets':[]},
            'reopenCheck':{'status':'PASS','sessionId':'fresh-session','projectSha256':sha(project),'pageCount':1,'pageDimensionsMm':[{'page':1,'width':210.0,'height':297.0}],'criticalText':['Title'],'linkedAssets':[],'verifiedBy':'reviewer','verifiedAt':'2026-10-08T10:00:00Z'}}
        artifact_path=output/'artifact-manifest.json';artifact_path.write_text(json.dumps(artifact))
        review={'schemaVersion':1,'contractVersion':'designcraft-page-review/v1','runId':run_id,'projectSha256':sha(project),'artifactManifestSha256':sha(artifact_path),'rubricVersion':'designcraft-layout-rubric/v1',
            'basis':{'type':'task-spec','path':brief.name,'sha256':sha(brief)},
            'reviewer':{'kind':reviewer_kind,'identity':'reviewer-01'} if reviewer_kind=='human' else {'kind':'automated','identity':'review-bot','model':'vision-model-v1'},
            'reviewedAt':'2026-10-08T10:05:00Z','pages':[{'page':1,'previewPath':preview.name,'previewSha256':sha(preview),'checks':[{'criterion':criterion,'status':'PASS','note':'verified'} for criterion in CRITERIA]}],
            'conclusions':{name:{'status':'PASS','note':'checked separately'} for name in ('structure','visual','output','editability')}}
        review_path=output/'page-review.json';review_path.write_text(json.dumps(review))
        return output,artifact_path,review_path,review,sha

    def test_no_reference_image_is_valid_when_task_spec_is_the_review_basis(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);output,artifact,review,_,_=self.fixture(root)
            result=MODULE.validate_review(output,artifact,review)
            self.assertEqual(result['status'],'PASS')
            self.assertEqual(result['reviewSource'],'human')
            self.assertFalse(result['completeAcceptance'])

    def test_automated_reviewer_model_is_recorded(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);output,artifact,review,_,_=self.fixture(root,'automated')
            result=MODULE.validate_review(output,artifact,review)
            self.assertEqual(result['reviewSource'],'automated')
            self.assertEqual(result['pagesReviewed'],1)

    def test_stale_project_preview_rubric_or_artifact_binding_is_rejected(self):
        mutations=('project','preview','artifact_manifest','rubric')
        for mutation in mutations:
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);output,artifact,review,manifest,sha=self.fixture(root)
                if mutation=='project':manifest['projectSha256']='0'*64
                elif mutation=='preview':manifest['pages'][0]['previewSha256']='0'*64
                elif mutation=='artifact_manifest':manifest['artifactManifestSha256']='0'*64
                else:manifest['rubricVersion']='rubric-unknown'
                review.write_text(json.dumps(manifest))
                with self.assertRaises(ValueError):MODULE.validate_review(output,artifact,review)

    def test_missing_page_criterion_failed_conclusion_and_unbound_basis_are_rejected(self):
        cases=('missing_criterion','failed_conclusion','basis_hash')
        for case in cases:
            with self.subTest(case=case),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);output,artifact,review,data,_=self.fixture(root)
                if case=='missing_criterion':data['pages'][0]['checks'].pop()
                elif case=='failed_conclusion':data['conclusions']['visual']['status']='FAIL'
                else:data['basis']['sha256']='f'*64
                review.write_text(json.dumps(data))
                if case=='failed_conclusion':self.assertEqual(MODULE.validate_review(output,artifact,review)['status'],'FAIL')
                else:
                    with self.assertRaises(ValueError):MODULE.validate_review(output,artifact,review)

if __name__=='__main__':unittest.main()
