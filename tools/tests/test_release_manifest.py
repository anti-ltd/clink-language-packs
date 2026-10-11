"""Exercise release selection without copying production language packs."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class ReleaseManifestTests(unittest.TestCase):
    def test_blocked_assets_are_excluded_and_reviewed_packs_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'tools').mkdir()
            (root / 'catalog').mkdir()
            (root / 'Lexicons').mkdir()
            script = root / 'tools/build-release-manifest.py'
            shutil.copy2(Path(__file__).resolve().parents[1] / script.name, script)
            catalogue = {
                'packs': [{'code': 'fil', 'status': 'blocked'},
                          {'code': 'ur_latn', 'status': 'complete'}],
                'imes': [{'code': 'ja_romaji', 'status': 'blocked'}],
            }
            (root / 'catalog/language-wave.json').write_text(json.dumps(catalogue))
            # Historical packs absent from the wave catalogue remain supported.
            for code in ('en', 'ur_latn', 'fil', 'ja_romaji'):
                (root / f'Lexicons/{code}.clex').write_bytes(b'fixture dictionary')
                (root / f'Lexicons/{code}.cngm').write_bytes(b'fixture next-word data')
            model = root / 'Lexicons/fil.mlmodelc'
            model.mkdir()
            (model / 'model.mil').write_text('blocked model')
            output = root / 'out'
            result = subprocess.run(
                [sys.executable, str(script), 'vtest', 'owner/repo', str(output)],
                capture_output=True, text=True, check=True,
            )
            manifest = json.loads((output / 'manifest.json').read_text())
            self.assertEqual([p['code'] for p in manifest['packs']], ['en', 'ur_latn'])
            self.assertEqual(len(list((output / 'assets').iterdir())), 4)
            for pack in manifest['packs']:
                self.assertEqual(pack['version'], 'vtest')
                self.assertEqual(len(pack['assets']), 2)
                for asset in pack['assets']:
                    self.assertIn('/releases/download/vtest/', asset['url'])
            self.assertIn('Skipping blocked language fil', result.stderr)
            self.assertIn('Skipping blocked language ja_romaji', result.stderr)


if __name__ == '__main__':
    unittest.main()
