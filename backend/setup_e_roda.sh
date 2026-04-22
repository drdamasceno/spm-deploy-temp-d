#!/bin/bash
# Setup e execucao da conciliacao SPM
# Execute: bash backend/setup_e_roda.sh

set -e

PP_PATH="/mnt/user-data/uploads/SPM_-_FB_-_Conf__01_a_09_04_2026_Claudexlsx.xlsx"
OFX_PATH="/mnt/user-data/uploads/EXTRATO_POR_PERIODO_120426_221307.ofx"

echo "=== SPM Sistema Financeiro - Setup e Conciliacao ==="

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "ERRO: python3 nao encontrado"
    exit 1
fi

echo "Python: $(python3 --version)"

# Instalar dependencias
echo "Instalando dependencias..."
python3 -m pip install openpyxl -q

# Executar testes unitarios
echo ""
echo "=== TESTES UNITARIOS ==="
cd "$(dirname "$0")/.." || exit 1
python3 backend/tests/teste_pega_plantao.py
python3 backend/tests/teste_extrato_bradesco.py
python3 backend/tests/teste_integracao.py

# Verificar arquivos reais
echo ""
echo "=== VERIFICANDO ARQUIVOS REAIS ==="

if [ ! -f "$PP_PATH" ]; then
    echo "AVISO: Arquivo PP nao encontrado: $PP_PATH"
    echo "Execute o script com o caminho correto do arquivo"
    exit 1
fi

if [ ! -f "$OFX_PATH" ]; then
    echo "AVISO: Arquivo OFX nao encontrado: $OFX_PATH"
    exit 1
fi

echo "PP encontrado: $PP_PATH"
echo "OFX encontrado: $OFX_PATH"

# Executar diagnostico e conciliacao
echo ""
echo "=== EXECUTANDO CONCILIACAO ==="
python3 backend/diagnostico_e_concilia.py

echo ""
echo "=== CONCLUIDO ==="
echo "Relatorio em: backend/output/"
