"""CLI 的版本化状态文件保持原生输出通道独立并支持长驻 MCP。"""
import importlib.util
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]

class NativeResultContract(unittest.TestCase):
    def load_cli(self,root):
        shutil_cli=root/'cli.py';shutil_cli.write_bytes((ROOT/'skills/designcraft-use/scripts/cli.py').read_bytes())
        (root/'bootstrap.py').write_text('def install(lock,home,archive=None):\n return {"executable":"fake-native"}\n')
        (root/'runtime.lock.json').write_text('{}\n')
        spec=importlib.util.spec_from_file_location('test_cli_'+str(id(root)),shutil_cli)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def invoke(self,module,root,command,result):
        result_file=root/'machine-result.json'
        argv=['cli.py','--runtime-home',str(root/'runtime'),'--result-file',str(result_file),'--timeout','7','--',*command]
        with patch.object(sys,'argv',argv),patch.object(module.subprocess,'run',return_value=result) as run:
            self.assertEqual(module.main(),result.returncode)
        return json.loads(result_file.read_text()),run.call_args.kwargs

    def test_native_exit_writes_versioned_result_without_changing_exit(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);module=self.load_cli(root)
            receipt,kwargs=self.invoke(module,root,['script','plan.json'],subprocess.CompletedProcess([],0))
            self.assertEqual(receipt['schemaVersion'],1)
            self.assertEqual(receipt['status'],'NATIVE_EXIT_ZERO_REVIEW_REQUIRED')
            self.assertTrue(receipt['terminationVerified'])
            self.assertEqual(kwargs['timeout'],7.0)

    def test_machine_metadata_uses_result_file_not_native_stdout(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);module=self.load_cli(root);result_file=root/'result.json';output=io.StringIO()
            argv=['cli.py','--runtime-home',str(root/'runtime'),'--result-file',str(result_file),'--','script','plan.json']
            with patch.object(sys,'argv',argv),patch.object(module.subprocess,'run',return_value=subprocess.CompletedProcess([],0)),contextlib.redirect_stdout(output):
                self.assertEqual(module.main(),0)
            self.assertEqual(output.getvalue(),'')
            self.assertTrue(result_file.is_file())

    def test_timeout_writes_unknown_and_mcp_has_no_short_task_timeout(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);module=self.load_cli(root)
            timed_out=subprocess.TimeoutExpired(['fake-native'],7,output=b'partial')
            with patch.object(sys,'argv',['cli.py','--runtime-home',str(root/'runtime'),'--result-file',str(root/'timeout.json'),'--','script','plan.json']),patch.object(module.subprocess,'run',side_effect=timed_out):
                self.assertEqual(module.main(),1)
            receipt=json.loads((root/'timeout.json').read_text())
            self.assertEqual((receipt['status'],receipt['reason']),('UNKNOWN','native_timeout'))
            self.assertEqual(receipt['stdout'],'partial')
            mcp_result,kwargs=self.invoke(module,root,['mcp'],subprocess.CompletedProcess([],0))
            self.assertEqual(kwargs['timeout'],None)

    def test_launch_failure_is_not_started_and_interrupt_stays_unknown(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);module=self.load_cli(root)
            with patch.object(sys,'argv',['cli.py','--runtime-home',str(root/'runtime'),'--result-file',str(root/'launch.json'),'--','script','plan.json']),patch.object(module.subprocess,'run',side_effect=FileNotFoundError('binary missing')),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(),1)
            failed=json.loads((root/'launch.json').read_text())
            self.assertEqual((failed['status'],failed['started']),('NOT_STARTED',False))
            with patch.object(sys,'argv',['cli.py','--runtime-home',str(root/'runtime'),'--result-file',str(root/'interrupt.json'),'--','script','plan.json']),patch.object(module.subprocess,'run',side_effect=KeyboardInterrupt()),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(),1)
            interrupted=json.loads((root/'interrupt.json').read_text())
            self.assertEqual((interrupted['status'],interrupted['reason']),('UNKNOWN','user_interrupted'))

if __name__=='__main__':unittest.main()
