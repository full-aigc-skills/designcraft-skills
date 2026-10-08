"""AV-04 binds authorized revisions to impact, fresh reviews and revalidated exports."""
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
SCRIPT=ROOT/'skills/designcraft-cli-export/scripts/revision_evidence.py'
SPEC=importlib.util.spec_from_file_location('revision_evidence',SCRIPT)
MODULE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class RevisionEvidenceContract(unittest.TestCase):
    def fixture(self,root,story=False):
        sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
        brief=root/'brief.md';brief.write_text('Revise only the page-three headline')
        cases=[]
        for version in ('before','after'):
            folder=root/version;folder.mkdir()
            project=folder/'book.designcraft';project.write_bytes(f'{version} project'.encode())
            pdf=folder/'book.pdf';pdf.write_bytes(f'{version} export'.encode())
            pages=[]
            for number in range(1,5):
                preview=folder/f'page-{number}.png';preview.write_bytes(f'{version} preview {number}'.encode())
                pages.append({'page':number,'previewPath':preview.name,'previewSha256':sha(preview),'checks':[{'criterion':criterion,'status':'PASS','note':'reviewed'} for criterion in MODULE.REVIEW_MODULE.CRITERIA]})
            run_id=str(uuid.uuid4())
            artifact={'schemaVersion':1,'runId':run_id,'projectArtifactId':'project','artifacts':[
                {'id':'project','kind':'project','path':project.name,'format':'designcraft','byteCount':project.stat().st_size,'sha256':sha(project)},
                {'id':'pdf','kind':'export','path':pdf.name,'format':'pdf','byteCount':pdf.stat().st_size,'sha256':sha(pdf)}],
                'expectations':{'pageCount':4,'pageDimensionsMm':[{'page':n,'width':210.0,'height':297.0} for n in range(1,5)],'criticalText':['Annual report'],'linkedAssets':[]},
                'reopenCheck':{'status':'PASS','sessionId':f'{version}-fresh-session','projectSha256':sha(project),'pageCount':4,
                    'pageDimensionsMm':[{'page':n,'width':210.0,'height':297.0} for n in range(1,5)],'criticalText':['Annual report'],'linkedAssets':[],
                    'verifiedBy':'reviewer-01','verifiedAt':'2026-10-08T10:00:00Z'}}
            artifact_path=folder/'artifact-manifest.json';artifact_path.write_text(json.dumps(artifact))
            review={'schemaVersion':1,'contractVersion':'designcraft-page-review/v1','runId':run_id,'projectSha256':sha(project),
                'artifactManifestSha256':sha(artifact_path),'rubricVersion':'designcraft-layout-rubric/v1',
                'basis':{'type':'task-spec','path':'../brief.md','sha256':sha(brief)},'reviewer':{'kind':'human','identity':'reviewer-01'},
                'reviewedAt':'2026-10-08T10:05:00Z','pages':pages,
                'conclusions':{name:{'status':'PASS','note':'verified'} for name in ('structure','visual','output','editability')}}
            review_path=folder/'page-review.json';review_path.write_text(json.dumps(review))
            # Preview and brief references must remain inside the artifact root.
            # Copy the task specification into each revision evidence directory.
            local_brief=folder/'brief.md';local_brief.write_text(brief.read_text())
            review['basis']={'type':'task-spec','path':'brief.md','sha256':sha(local_brief)}
            review['artifactManifestSha256']=sha(artifact_path)
            review_path.write_text(json.dumps(review))
            snapshot_objects=[]
            for number in range(1,5):
                story_id='story-main' if story and number in (2,3) else None
                content_hash=('b' if version=='after' and number==3 else 'a')*64
                snapshot_objects.append({'id':f'headline-p{number}','page':number,'contentSha256':content_hash,'storyId':story_id})
            snapshot={'schemaVersion':1,'projectSha256':sha(project),'objects':snapshot_objects}
            snapshot_path=folder/'revision-snapshot.json';snapshot_path.write_text(json.dumps(snapshot))
            cases.append({'folder':folder,'artifact':artifact_path,'review':review_path,'snapshot':snapshot_path,'snapshotSha':sha(snapshot_path),'pdfSha':sha(pdf)})
        before,after=cases
        record={'schemaVersion':1,'contractVersion':'designcraft-revision/v1',
            'authorization':{'scope':{'type':'page','page':3},'authorizationText':'Change only the page-three headline'},
            'before':{'artifactManifestPath':'before/artifact-manifest.json','artifactManifestSha256':sha(before['artifact']),'pageReviewPath':'before/page-review.json','pageReviewSha256':sha(before['review']),'snapshotPath':'before/revision-snapshot.json','snapshotSha256':before['snapshotSha']},
            'after':{'artifactManifestPath':'after/artifact-manifest.json','artifactManifestSha256':sha(after['artifact']),'pageReviewPath':'after/page-review.json','pageReviewSha256':sha(after['review']),'snapshotPath':'after/revision-snapshot.json','snapshotSha256':after['snapshotSha']},
            'affectedPages':[3], 'revalidatedExports':[{'artifactId':'pdf','format':'pdf','sha256':after['pdfSha'],'status':'PASS'}]}
        if story:
            record['authorization']={'scope':{'type':'story','storyId':'story-main'},'authorizationText':'Revise the authorized text story'}
            # A change in the page-two member can affect every page carrying this story.
            after_snapshot=json.loads(after['snapshot'].read_text())
            after_snapshot['objects'][1]['contentSha256']='b'*64
            after['snapshot'].write_text(json.dumps(after_snapshot));after['snapshotSha']=sha(after['snapshot'])
            record['after']['snapshotSha256']=after['snapshotSha']
            record['affectedPages']=[2,3]
        path=root/'revision.json';path.write_text(json.dumps(record))
        return path,record,before,after

    def test_page_three_title_revision_binds_before_after_reviews_and_fresh_export(self):
        with tempfile.TemporaryDirectory() as temp:
            path,_,_,_=self.fixture(Path(temp))
            result=MODULE.validate_revision(Path(temp),path)
            self.assertEqual(result['status'],'PASS')
            self.assertEqual(result['affectedPages'],[3])
            self.assertEqual(result['revalidatedExports'],['pdf'])
            self.assertNotEqual(result['beforeProjectSha256'],result['afterProjectSha256'])
            self.assertFalse(result['completeAcceptance'])

    def test_story_revision_includes_all_pages_in_the_affected_flow(self):
        with tempfile.TemporaryDirectory() as temp:
            path,_,_,_=self.fixture(Path(temp),story=True)
            result=MODULE.validate_revision(Path(temp),path)
            self.assertEqual(result['status'],'PASS')
            self.assertEqual(result['affectedPages'],[2,3])

    def test_out_of_scope_change_or_incomplete_story_impact_is_rejected(self):
        for mutation,expected in (('scope','revision_out_of_scope'),('impact','revision_affected_pages_mismatch')):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as temp:
                root=Path(temp);path,record,_,after=self.fixture(root)
                snapshot=json.loads(after['snapshot'].read_text())
                if mutation=='scope':snapshot['objects'][1]['contentSha256']='c'*64
                else:record['affectedPages']=[]
                if mutation=='scope':
                    after['snapshot'].write_text(json.dumps(snapshot));record['after']['snapshotSha256']=hashlib.sha256(after['snapshot'].read_bytes()).hexdigest()
                path.write_text(json.dumps(record))
                with self.assertRaisesRegex(ValueError,expected):MODULE.validate_revision(root,path)

    def test_stale_or_unreviewed_export_cannot_pass_revision(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path,record,_,_=self.fixture(root)
            record['revalidatedExports'][0]['sha256']='0'*64
            path.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError,'revision_export_identity_mismatch'):MODULE.validate_revision(root,path)

    def test_changed_snapshot_after_review_or_cli_report_cannot_claim_completion(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path,record,_,after=self.fixture(root)
            snapshot=json.loads(after['snapshot'].read_text());snapshot['objects'][2]['contentSha256']='c'*64
            after['snapshot'].write_text(json.dumps(snapshot))
            with self.assertRaisesRegex(ValueError,'after_snapshot_identity_mismatch'):MODULE.validate_revision(root,path)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path,_,_,_=self.fixture(root)
            run=subprocess.run([sys.executable,'-I','-B',str(SCRIPT),'--root',str(root),'--revision',str(path)],capture_output=True,text=True)
            report=json.loads(run.stdout)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertEqual(report['status'],'PASS')
            self.assertFalse(report['result']['completeAcceptance'])

if __name__=='__main__':unittest.main()
