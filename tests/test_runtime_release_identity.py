"""固定发行版本与资产身份必须在安装前一致；不执行原生程序。"""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import hashlib
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
DOMAIN = ROOT.name.removesuffix('-skills')

class ReleaseIdentity(unittest.TestCase):
    def setUp(self):
        path = ROOT/'skills'/f'{DOMAIN}-use/scripts/bootstrap.py'
        spec = importlib.util.spec_from_file_location('bootstrap', path)
        self.bootstrap = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.bootstrap)
        self.lock = json.loads(path.with_name('runtime.lock.json').read_text())

    def assert_refused_before_install(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary)/'runtime'
            with patch.object(self.bootstrap, 'download', side_effect=AssertionError('download must not start')):
                with self.assertRaisesRegex(ValueError, 'runtime_release_identity_mismatch'):
                    self.bootstrap.install(self.lock, runtime, platform_key='darwin-arm64')
            self.assertFalse(runtime.exists())

    def test_release_tag_must_match_lock(self):
        item = self.lock['artifacts']['darwin-arm64']
        item['url'] = item['url'].replace('/v0.2.1/', '/v0.2.0/')
        self.assert_refused_before_install()

    def test_archive_name_must_match_runtime_identity(self):
        item = self.lock['artifacts']['darwin-arm64']
        item['url'] = item['url'].replace('/'+DOMAIN+'-cli-', '/foreign-cli-')
        self.assert_refused_before_install()

    def test_unsupported_platform_is_rejected_before_runtime_directory_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime=Path(temporary)/'runtime'
            with self.assertRaisesRegex(ValueError,'unsupported_platform'):
                self.bootstrap.install(self.lock,runtime,platform_key='windows-x86_64')
            self.assertFalse(runtime.exists())

    def test_corrupt_archive_checksum_is_rejected_without_installing_binary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);runtime=root/'runtime';archive=root/'broken.zip';archive.write_bytes(b'not the pinned archive')
            with patch.object(self.bootstrap,'download',side_effect=AssertionError('explicit archive must not download')):
                with self.assertRaisesRegex(ValueError,'archive_checksum_mismatch'):
                    self.bootstrap.install(self.lock,runtime,archive=archive,platform_key='darwin-arm64')
            self.assertFalse((runtime/'designcraft-cli'/'0.2.1'/'designcraft-cli').exists())

    def test_checksum_matched_non_zip_is_rejected_before_binary_install(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);runtime=root/'runtime';archive=root/'broken.zip';archive.write_bytes(b'corrupt payload')
            self.lock['artifacts']['darwin-arm64']['archiveSha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
            with patch.object(self.bootstrap,'download',side_effect=AssertionError('explicit archive must not download')):
                with self.assertRaises(zipfile.BadZipFile):
                    self.bootstrap.install(self.lock,runtime,archive=archive,platform_key='darwin-arm64')
            self.assertFalse((runtime/'designcraft-cli'/'0.2.1'/'designcraft-cli').exists())

if __name__ == '__main__':
    unittest.main()
