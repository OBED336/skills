"""Integration evidence: real link-checker CLI, isolated faults and recovery."""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class EvidenciaEnlacesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "scripts").mkdir()
        shutil.copyfile(Path(__file__).with_name("check_links.py"),
                        self.root / "scripts" / "check_links.py")
        (self.root / "evals").mkdir()
        self.source = self.root / "README.md"
        self.target = self.root / "evals" / "guia.md"
        self.target.write_text("# Instalacion\n", encoding="utf-8")
        self.source.write_text("[Guia](evals/guia.md#instalacion)\n", encoding="utf-8")

    def check(self, expected_code, expected_text):
        result = subprocess.run(
            [sys.executable, str(self.root / "scripts" / "check_links.py")],
            cwd=self.root, text=True, capture_output=True, timeout=20,
        )
        output = result.stdout + result.stderr
        self.assertEqual(expected_code, result.returncode, output)
        self.assertIn(expected_text, output)
        print(f"\n{self._testMethodName} | exit={result.returncode}\n{output.strip()}", flush=True)

    def healthy(self):
        self.check(0, "all local links are valid")

    def test_01_archivo_eliminado_detectado_y_recuperado(self):
        self.healthy()
        original = self.target.read_bytes()
        self.target.unlink()
        self.check(1, "README.md:1: target not found: evals/guia.md#instalacion")
        self.target.write_bytes(original)
        self.healthy()

    def test_02_encabezado_cambiado_detectado_y_corregido(self):
        self.healthy()
        self.target.write_text("# Configuracion\n", encoding="utf-8")
        self.check(1, "anchor not found in evals/guia.md: #instalacion")
        self.source.write_text("[Guia](evals/guia.md#configuracion)\n", encoding="utf-8")
        self.healthy()

    def test_03_escape_codificado_rechazado_y_corregido(self):
        self.healthy()
        self.source.write_text("[Fuera](%2e%2e/fuera.md)\n", encoding="utf-8")
        self.check(1, "target escapes repository: %2e%2e/fuera.md")
        self.source.write_text("[Guia](evals/guia.md)\n", encoding="utf-8")
        self.healthy()

    def test_04_varios_errores_se_reportan_juntos_y_se_corrigen(self):
        self.healthy()
        self.source.write_text(
            "[Falta](evals/ausente.md)\n[Ancla](evals/guia.md#ausente)\n",
            encoding="utf-8",
        )
        self.check(1, "2 broken Markdown link(s) found")
        (self.root / "evals" / "ausente.md").write_text("# Nueva guia\n", encoding="utf-8")
        self.target.write_text("# Instalacion\n## Ausente\n", encoding="utf-8")
        self.healthy()

    def test_05_destino_con_espacios_codificados_y_recuperacion(self):
        self.healthy()
        renamed = self.target.with_name("guia local.md")
        self.target.rename(renamed)
        self.source.write_text("[Guia](evals/guia%20local.md#instalacion)\n", encoding="utf-8")
        self.healthy()
        renamed.unlink()
        self.check(1, "target not found: evals/guia%20local.md#instalacion")
        renamed.write_text("# Instalacion\n", encoding="utf-8")
        self.healthy()


if __name__ == "__main__":
    unittest.main(verbosity=2)
