import unittest
from pathlib import Path

from core.version import APP_VERSION


class VersionTests(unittest.TestCase):
    def test_release_version_uses_semantic_versioning(self):
        self.assertRegex(APP_VERSION, r'^\d+\.\d+\.\d+$')

    def test_release_artifacts_use_the_canonical_version(self):
        root = Path(__file__).resolve().parents[1]
        spec = (root / 'NetGuard_Professional.spec').read_text(encoding='utf-8')
        build_script = (root / 'build_exe.bat').read_text(encoding='utf-8')
        self.assertIn('from core.version import APP_VERSION', spec)
        self.assertIn('APP_VERSION.replace', spec)
        self.assertIn('from core.version import APP_VERSION; print(APP_VERSION)', build_script)
        self.assertIn('NetGuard_Professional_%APP_VERSION:.=_%.exe', build_script)
        self.assertIn('py -3.13', build_script)
        self.assertIn('.build-venv-py313', build_script)
        self.assertIn('NetGuard_Admin_Recovery', build_script)
        self.assertIn('reset_admin_password.py', build_script)
