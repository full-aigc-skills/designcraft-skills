"""任务回执与输入身份合同；全部子进程为模拟，不安装或运行原生工具。"""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
DOMAIN=ROOT.name.removesuffix('-skills')

class ReceiptContract(unittest.TestCase):
    def setUp(self):
        self.scripts=ROOT/'skills'/f'{DOMAIN}-use'/'scripts'
        spec=importlib.util.spec_from_file_location('gateway',self.scripts/'command_gateway.py')
        self.g=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.g)

    def catalog(self):
        return [{'name':'doc_info','input_schema':{'type':'object','properties':{}}}] if DOMAIN=='printcraft' else [{'id':'file.new','params':'','menu':[]}]

    def plan(self,root,steps=None):
        p=root/'plan.json'
        p.write_text(json.dumps({'domain':DOMAIN,'steps':steps or [{'command':'doc_info' if DOMAIN=='printcraft' else 'file.new','params':{}}]}))
        return p

    def invoke(self,argv,side_effect):
        calls=[]
        def dispatch(command,**kwargs):
            calls.append(command)
            if callable(side_effect):result=side_effect(command,**kwargs)
            else:
                effect=side_effect[len(calls)-1]
                if isinstance(effect,BaseException):raise effect
                result=effect
            if isinstance(result,subprocess.CompletedProcess) and '--result-file' in command:
                target=Path(command[command.index('--result-file')+1])
                status='NATIVE_EXIT_ZERO_REVIEW_REQUIRED' if result.returncode==0 else 'FAILED_OR_PARTIAL'
                target.write_text(json.dumps({'schemaVersion':1,'status':status,'reason':'native_exit','exitCode':result.returncode,'started':True,'startedAt':'2026-10-08T00:00:00+00:00','finishedAt':'2026-10-08T00:00:01+00:00','terminationVerified':True,'descendantsTerminationVerified':False}))
            return result
        with patch.object(sys,'argv',['commands.py',*argv]),patch.object(self.g.subprocess,'run',side_effect=dispatch) as run,contextlib.redirect_stdout(io.StringIO()):
            result=self.g.main(DOMAIN,self.scripts)
            return result,run.call_count

    def test_receipt_binds_explicit_input_and_actual_runtime_lock(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/'input.bin';source.write_bytes(b'original input');output=root/'output'
            discovery=subprocess.CompletedProcess([],0,json.dumps(self.catalog()),'')
            success=subprocess.CompletedProcess([],0,'native output','')
            result,count=self.invoke(['run',str(self.plan(root)),'--output',str(output),'--input',str(source)],[discovery,success])
            self.assertEqual((result,count),(0,2))
            receipt=json.loads((output/'receipt.json').read_text())
            self.assertEqual(receipt['inputSha256'][str(source)],hashlib.sha256(b'original input').hexdigest())
            self.assertEqual(receipt['runtimeLockSha256'],hashlib.sha256((self.scripts/'runtime.lock.json').read_bytes()).hexdigest())
            self.assertFalse(receipt['completeAcceptance'])
            self.assertEqual(receipt['status'],'NATIVE_EXIT_ZERO_REVIEW_REQUIRED')

    def test_receipt_persists_runtime_directory_and_single_session_step_identity(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);output=root/'output'
            command='doc_info' if DOMAIN=='printcraft' else 'file.new'
            steps=[{'command':command,'params':{'title':'first'}},{'command':command,'params':{'storyRef':'step:0'}}]
            def native(argv,**kwargs):
                if '--result-file' not in argv:return subprocess.CompletedProcess([],0,json.dumps(self.catalog()),'')
                started=json.loads((output/'receipt.json').read_text())
                self.assertEqual(started['status'],'STARTED')
                self.assertTrue(all(step['status']=='SUBMITTED' for step in started['stepResults']))
                return subprocess.CompletedProcess([],0,'native output','')
            result,count=self.invoke(['run',str(self.plan(root,steps)),'--output',str(output)],native)
            self.assertEqual((result,count),(0,2))
            receipt=json.loads((output/'receipt.json').read_text())
            runtime_lock=json.loads((self.scripts/'runtime.lock.json').read_text())
            self.assertEqual(receipt['runtimeIdentity']['verificationStatus'],'LOCKED_EXPECTATION')
            self.assertEqual(receipt['runtimeIdentity']['version'],runtime_lock['resolvedVersion'])
            self.assertEqual(receipt['runtimeIdentity']['lockSha256'],receipt['runtimeLockSha256'])
            self.assertEqual(receipt['directoryBaseline'],{'path':str(output),'state':'ABSENT','sha256':None})
            self.assertEqual([step['command'] for step in receipt['stepReferences']],[command,command])
            self.assertEqual([step['index'] for step in receipt['stepResults']],[0,1])
            self.assertTrue(all(step['status']=='BATCH_EXIT_ZERO_REVIEW_REQUIRED' for step in receipt['stepResults']))
            self.assertEqual(receipt['stepResultGranularity'],'single-native-session')
            native_plan=(output/'native-plan.json').read_text().splitlines()
            self.assertEqual([json.loads(line) for line in native_plan],steps)

    def test_designcraft_source_is_copied_and_native_edits_leave_original_intact(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/'source-project';source.mkdir();original=source/'page.json';original.write_text('{"title":"before"}')
            output=root/'output';calls=[]
            def native(argv,**kwargs):
                calls.append(argv)
                if '--result-file' in argv:
                    copied=Path(argv[argv.index('--in')+1])/'page.json'
                    self.assertNotEqual(copied,original)
                    self.assertEqual(json.loads(copied.read_text()),{'title':'before'})
                    copied.write_text('{"title":"after"}')
                    return subprocess.CompletedProcess([],0,'native output','')
                return subprocess.CompletedProcess([],0,json.dumps(self.catalog()),'')
            result,count=self.invoke(['run',str(self.plan(root)),'--output',str(output),'--source',str(source)],native)
            self.assertEqual((result,count),(0,2))
            receipt=json.loads((output/'receipt.json').read_text())
            self.assertEqual(original.read_text(),'{"title":"before"}')
            self.assertEqual(receipt['workingCopyPath'],str(output/'working-copy'/'source-project'))
            self.assertEqual(receipt['workingCopyBeforeSha256']['page.json'],hashlib.sha256(b'{"title":"before"}').hexdigest())
            self.assertEqual(receipt['workingCopyAfterSha256']['page.json'],hashlib.sha256(b'{"title":"after"}').hexdigest())

    def test_changed_input_during_discovery_blocks_native_edit(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/'input.bin';source.write_bytes(b'original');output=root/'output'
            def changed(argv,**kwargs):
                source.write_bytes(b'changed while installing')
                return subprocess.CompletedProcess([],0,json.dumps(self.catalog()),'')
            result,count=self.invoke(['run',str(self.plan(root)),'--output',str(output),'--input',str(source)],changed)
            self.assertEqual((result,count),(1,1))
            self.assertFalse(output.exists())

    def test_skill_resource_drift_during_discovery_blocks_native_edit(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);output=root/'output';initial=self.g.capture_resources(self.scripts);changed=dict(initial);changed['cli.py']='0'*64
            with patch.object(self.g,'capture_resources',side_effect=[initial,changed]):
                result,count=self.invoke(['run',str(self.plan(root)),'--output',str(output)],[subprocess.CompletedProcess([],0,json.dumps(self.catalog()),'')])
            self.assertEqual((result,count),(1,1))
            self.assertFalse(output.exists())

    def test_input_missing_is_rejected_before_discovery(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            result,count=self.invoke(['run',str(self.plan(root)),'--output',str(root/'out'),'--input',str(root/'missing')],AssertionError('must not start'))
            self.assertEqual((result,count),(1,0))

    def test_timeout_keeps_partial_logs_and_unknown_without_replay(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);output=root/'output'
            discovery=subprocess.CompletedProcess([],0,json.dumps(self.catalog()),'')
            timeout=subprocess.TimeoutExpired(['native'],900,output=b'partial output',stderr=b'partial error')
            result,count=self.invoke(['run',str(self.plan(root)),'--output',str(output)],[discovery,timeout])
            self.assertEqual((result,count),(1,2))
            receipt=json.loads((output/'receipt.json').read_text())
            self.assertEqual(receipt['status'],'UNKNOWN')
            self.assertEqual(receipt['stdout'],'partial output')
            self.assertEqual(receipt['stderr'],'partial error')
            self.assertFalse(receipt['automaticReplay'])
            self.assertTrue(all(step['status']=='UNKNOWN' for step in receipt['stepResults']))

    def test_gateway_preserves_unknown_from_real_child_process(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);scripts=root/'scripts';scripts.mkdir()
            for name in ('bootstrap.py','runtime.lock.json','commands.py','command_gateway.py'):
                shutil.copyfile(self.scripts/name,scripts/name)
            (scripts/'cli.py').write_text('''import json,sys\nfrom pathlib import Path\na=sys.argv[1:]\nif a[-1:] == ["commands"]:\n print(json.dumps([{"id":"file.new","params":"","menu":[]}]))\n raise SystemExit(0)\np=Path(a[a.index("--result-file")+1])\np.write_text(json.dumps({"schemaVersion":1,"status":"UNKNOWN","reason":"native_timeout","exitCode":1,"started":True,"startedAt":"2026-10-08T00:00:00+00:00","finishedAt":"2026-10-08T00:00:01+00:00","terminationVerified":False,"descendantsTerminationVerified":False}))\nprint(json.dumps({"result":"unknown","error":"native_timeout"}))\nraise SystemExit(1)\n''')
            output=root/'output'
            with patch.object(sys,'argv',['commands.py','run',str(self.plan(root)),'--output',str(output)]),contextlib.redirect_stdout(io.StringIO()):
                result=self.g.main(DOMAIN,scripts)
            receipt=json.loads((output/'receipt.json').read_text())
            self.assertEqual(result,1)
            self.assertEqual(receipt['status'],'UNKNOWN')
            self.assertEqual(receipt['reason'],'native_timeout')

    def test_missing_truncated_or_unknown_machine_result_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);path=root/'result.json'
            for content in (None,'{truncated','{"schemaVersion":99,"status":"NATIVE_EXIT_ZERO_REVIEW_REQUIRED","started":true,"terminationVerified":true,"exitCode":0}'):
                if content is None:path.unlink(missing_ok=True)
                else:path.write_text(content)
                result=self.g.read_native_result(path,0)
                self.assertEqual(result['status'],'UNKNOWN')
                self.assertFalse(result['terminationVerified'])

    def test_legacy_receipt_is_read_only_and_never_starts_native_cli(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);path=root/'old-receipt.json';path.write_text(json.dumps({'domain':DOMAIN,'status':'UNKNOWN','stdout':'partial log','automaticReplay':False}))
            output=io.StringIO()
            with patch.object(sys,'argv',['commands.py','receipt',str(path)]),patch.object(self.g.subprocess,'run',side_effect=AssertionError('receipt inspection must stay offline')),contextlib.redirect_stdout(output):
                result=self.g.main(DOMAIN,self.scripts)
            receipt=json.loads(output.getvalue())
            self.assertEqual(result,0)
            self.assertEqual((receipt['status'],receipt['legacyStatus']),('LEGACY_READ_ONLY','UNKNOWN'))
            self.assertFalse(receipt['resumeAllowed'])
            self.assertEqual(receipt['stdout'],'partial log')

    def test_receipt_reader_rejects_step_result_identity_drift(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'receipt.json';run_id='55ee72fa-d2ac-4cc3-a6d8-97e8f275f228'
            receipt={'schemaVersion':2,'runId':run_id,'domain':DOMAIN,'status':'UNKNOWN','stepResultGranularity':'single-native-session','stepReferences':[{'stepRef':run_id+':step:0','index':0,'command':'file.new','paramsSha256':'a'*64}],'stepResults':[{'stepRef':run_id+':step:1','index':1,'command':'file.new','status':'UNKNOWN','granularity':'single-native-session'}]}
            path.write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError,'receipt_step_identity_mismatch'):
                self.g.inspect_receipt(path,DOMAIN)

    def test_interrupted_started_receipt_remains_inspectable_without_replay(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'receipt.json'
            receipt={'schemaVersion':2,'runId':'55ee72fa-d2ac-4cc3-a6d8-97e8f275f228','domain':DOMAIN,'status':'STARTED','automaticReplay':False,'completeAcceptance':False}
            path.write_text(json.dumps(receipt))
            inspected=self.g.inspect_receipt(path,DOMAIN)
            self.assertEqual(inspected['status'],'STARTED')
            self.assertFalse(inspected['automaticReplay'])

    def test_unknown_future_receipt_version_is_rejected_offline(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'future.json';path.write_text(json.dumps({'domain':DOMAIN,'schemaVersion':99,'status':'NATIVE_EXIT_ZERO_REVIEW_REQUIRED'}))
            output=io.StringIO()
            with patch.object(sys,'argv',['commands.py','receipt',str(path)]),patch.object(self.g.subprocess,'run',side_effect=AssertionError('receipt inspection must stay offline')),contextlib.redirect_stdout(output):
                result=self.g.main(DOMAIN,self.scripts)
            self.assertEqual(result,1)
            self.assertIn('unsupported_receipt_schema',output.getvalue())

    def test_changed_input_on_zero_exit_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/'input.bin';source.write_bytes(b'original');output=root/'output';calls=[]
            def native(argv,**kwargs):
                calls.append(argv)
                if len(calls)==1:return subprocess.CompletedProcess([],0,json.dumps(self.catalog()),'')
                source.write_bytes(b'changed by native operation')
                return subprocess.CompletedProcess([],0,'','')
            result,count=self.invoke(['run',str(self.plan(root)),'--output',str(output),'--input',str(source)],native)
            self.assertEqual((result,count),(1,2))
            self.assertEqual(json.loads((output/'receipt.json').read_text())['status'],'INPUT_CHANGED_REVIEW_REQUIRED')

    def test_skill_resource_drift_after_native_zero_exit_invalidates_acceptance(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);output=root/'output';initial=self.g.capture_resources(self.scripts);changed=dict(initial);changed['runtime.lock.json']='f'*64
            discovery=subprocess.CompletedProcess([],0,json.dumps(self.catalog()),'');success=subprocess.CompletedProcess([],0,'native output','')
            with patch.object(self.g,'capture_resources',side_effect=[initial,initial,changed]):
                result,count=self.invoke(['run',str(self.plan(root)),'--output',str(output)],[discovery,success])
            self.assertEqual((result,count),(1,2))
            receipt=json.loads((output/'receipt.json').read_text())
            self.assertEqual(receipt['status'],'SKILL_CHANGED_REVIEW_REQUIRED')

if __name__=='__main__':unittest.main()
