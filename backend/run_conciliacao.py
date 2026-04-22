#!/usr/bin/env python3
"""
Script de execucao local — Conciliacao SPM.
Executa os parsers com os arquivos reais e mostra resultado.
"""

import sys
import subprocess
from pathlib import Path

PP_PATH = "/mnt/user-data/uploads/SPM_-_FB_-_Conf__01_a_09_04_2026_Claudexlsx.xlsx"
OFX_PATH = "/mnt/user-data/uploads/EXTRATO_POR_PERIODO_120426_221307.ofx"

def check_deps():
    """Verifica e instala dependencias."""
    try:
        import openpyxl
        print("OK openpyxl:", openpyxl.__version__)
    except ImportError:
        print("Instalando openpyxl...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "openpyxl", "-q"])


def main():
    check_deps()
    
    # Adicionar src ao path
    src_path = Path(__file__).parent / "src"
    sys.path.insert(0, str(src_path))
    
    # Rodar o CLI
    script = Path(__file__).parent / "conciliar_spm.py"
    cmd = [sys.executable, str(script), PP_PATH, OFX_PATH, "--output", "backend/output", "--debug"]
    print("Executando:", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
