"""AV-01 必须来自当前重开工程的原始业务结果，不能接受自报 PASS。"""
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
SCRIPTS=ROOT/'skills/designcraft-cli-export/scripts'
SCRIPT=SCRIPTS/'business_evidence.py'
SPEC=importlib.util.spec_from_file_location('business_evidence',SCRIPT)
MODULE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(MODULE)

class BusinessEvidenceContract(unittest.TestCase):
    def fixture(self,root):
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        project=root/'book.designcraft';project.write_bytes(b'editable project')
        pdf=root/'book.pdf';pdf.write_bytes(b'pdf export')
        run=str(uuid.uuid4());candidate=sha(project)
        dimensions=[{'page':1,'width':210,'height':297}]
        manifest={'schemaVersion':1,'runId':str(uuid.uuid4()),'projectArtifactId':'project',
            'artifacts':[{'id':i,'kind':kind,'path':p.name,'format':fmt,'byteCount':p.stat().st_size,'sha256':sha(p)} for i,kind,p,fmt in [('project','project',project,'designcraft'),('pdf','export',pdf,'pdf')]],
            'expectations':{'pageCount':1,'pageDimensionsMm':dimensions,'criticalText':['Title'],'linkedAssets':[]},
            'reopenCheck':{'status':'PASS','sessionId':run,'projectSha256':candidate,'pageCount':1,'pageDimensionsMm':dimensions,'criticalText':['Title'],'linkedAssets':[],'verifiedBy':'fixture','verifiedAt':'2026-10-08T00:00:00Z'}}
        mp=root/'manifest.json';mp.write_text(json.dumps(manifest))
        refs=[{'index':i,'stepRef':f'{run}:step:{i}','command':command,'paramsSha256':'a'*64} for i,command in enumerate(('preflight.run','file.exportPdf'))]
        raw={'completed':2,'results':[{'errors':0,'warnings':0,'issues':[]},{'path':'/tmp/native.pdf','bytes':pdf.stat().st_size,'pages':1,'warnings':[]}]}
        lock=json.loads((SCRIPTS/'runtime.lock.json').read_text());lock_sha=sha(SCRIPTS/'runtime.lock.json')
        receipt={'schemaVersion':2,'domain':'designcraft','runId':run,'status':'NATIVE_EXIT_ZERO_REVIEW_REQUIRED','exitCode':0,'started':True,'terminationVerified':True,'automaticReplay':False,'completeAcceptance':False,
            'inputSha256':{str(project):candidate},'inputAfterSha256':{str(project):candidate},'skillResourceSha256':{'runtime.lock.json':lock_sha},'skillResourceAfterSha256':{'runtime.lock.json':lock_sha},
            'runtimeIdentity':{'verificationStatus':'LOCKED_EXPECTATION','name':lock['artifact'],'version':lock['resolvedVersion'],'platform':'darwin-arm64','runtimeHome':'/tmp/fixture-runtime','lockSha256':lock_sha,'expectedBinarySha256':lock['artifacts']['darwin-arm64']['binarySha256']},
            'stepResultGranularity':'single-native-session','stepReferences':refs,'stepResults':[dict(ref,status='BATCH_EXIT_ZERO_REVIEW_REQUIRED',granularity='single-native-session') for ref in refs],'stdout':json.dumps(raw)}
        receipt['businessAssessment']=MODULE._module('command_gateway').assess_business_results(receipt['stdout'],refs,'designcraft')
        rp=root/'receipt.json';rp.write_text(json.dumps(receipt))
        return mp,rp,receipt,raw

    def test_current_reopened_candidate_passes_with_raw_classification(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);mp,rp,receipt,raw=self.fixture(root)
            report=MODULE.validate_business(root,mp,rp)
            self.assertEqual(report['status'],'PASS');self.assertEqual(report['reopenRunId'],receipt['runId'])
            self.assertEqual(report['receiptSha256'],hashlib.sha256(rp.read_bytes()).hexdigest())
            self.assertFalse(report['completeAcceptance'])

    def test_forged_pass_cannot_hide_raw_warning_error_or_unknown_field(self):
        for field,value in [('warnings',['native warning']),('errors',1),('unknownIssue',True)]:
            with self.subTest(field=field),tempfile.TemporaryDirectory() as t:
                root=Path(t);mp,rp,receipt,raw=self.fixture(root)
                if field=='warnings':raw['results'][1][field]=value
                else:raw['results'][0][field]=value
                receipt['stdout']=json.dumps(raw);rp.write_text(json.dumps(receipt))
                with self.assertRaisesRegex(ValueError,'business_assessment_raw_result_mismatch'):
                    MODULE.validate_business(root,mp,rp)

    def test_matching_warning_classification_still_cannot_pass(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);mp,rp,receipt,raw=self.fixture(root)
            raw['results'][1]['warnings']=['format loss'];receipt['stdout']=json.dumps(raw)
            receipt['businessAssessment']=MODULE._module('command_gateway').assess_business_results(receipt['stdout'],receipt['stepReferences'],'designcraft');rp.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError,'business_assessment_not_pass:REVIEW_REQUIRED'):MODULE.validate_business(root,mp,rp)

    def test_wrong_session_project_runtime_or_export_is_rejected(self):
        mutations=[('session',lambda r:r.update(runId=str(uuid.uuid4()))),('project',lambda r:r.update(inputSha256={'other':'b'*64},inputAfterSha256={'other':'b'*64})),('runtime',lambda r:r['runtimeIdentity'].update(expectedBinarySha256='b'*64)),('status',lambda r:r.update(status='UNKNOWN'))]
        for label,mutate in mutations:
            with self.subTest(label=label),tempfile.TemporaryDirectory() as t:
                root=Path(t);mp,rp,receipt,raw=self.fixture(root);mutate(receipt);rp.write_text(json.dumps(receipt))
                with self.assertRaises(ValueError):MODULE.validate_business(root,mp,rp)
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);mp,rp,receipt,raw=self.fixture(root);raw['results'][1]['bytes']+=1;receipt['stdout']=json.dumps(raw);rp.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError,'business_export_identity_mismatch'):MODULE.validate_business(root,mp,rp)

    def test_single_skill_cli_isolated_imports_work_and_receipt_link_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);mp,rp,receipt,raw=self.fixture(root)
            run=subprocess.run([sys.executable,'-I','-B',str(SCRIPT),'--root',str(root),'--artifact-manifest',str(mp),'--receipt',str(rp)],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            link=root/'receipt-link.json';link.symlink_to(rp)
            with self.assertRaisesRegex(ValueError,'business_evidence_path_invalid'):MODULE.validate_business(root,mp,link)

if __name__=='__main__':unittest.main()
