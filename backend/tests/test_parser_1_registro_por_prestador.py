"""Parser PP: valida que gera 1 registro_pp por prestador (não N por local).

Regra ANCORADA: CLAUDE.md regra 1 — 1 arquivo PP = 1 contrato = 1 remessa
por prestador. Coluna "Local" do XLSX é unidade/setor dentro do mesmo contrato.
Parser NUNCA pode fragmentar saldo por variação de local.
"""
from __future__ import annotations
from io import BytesIO
from openpyxl import Workbook

from backend.src.pega_plantao import parse_relatorio


def _build_xlsx_adriano_dois_locais() -> bytes:
    """
    XLSX mínimo simulando bloco de DR ADRIANO com 2 locais:
    - PS URGENCIA: 2 plantões × R$ 1.150 = R$ 2.300
    - PLANTONISTA CLINICO: 1 plantão × R$ 1.150 = R$ 1.150
    Taxas: -R$ 10 (Sistema) -R$ 10 (PIX)
    Total: R$ 3.430 (linha Total explícita)
    """
    wb = Workbook()
    ws = wb.active
    # Linhas 1-3: cabeçalho global (parser pula)
    ws.append(["FINANCEIRO COM BONIFICAÇÃO"])
    ws.append(["01/03/2026~31/03/2026"])
    ws.append([])
    # Linha 4: header prestador
    ws.append(["DR ADRIANO PEREIRA GIOVANNI DA COSTA  -  45438/BA"])
    # Linha 5: info PIX
    ws.append(["Transação: PIX Tipo de Documento: CPF Chave Pix: 035.740.645-19 Documento: 035.740.645-19 Razão social: ADRIANO PEREIRA GIOVANNI DA COSTA"])
    # Linha 6: header colunas
    ws.append(["Data", "Local", "Tipo", "Duração (h)", "Valor", "Total", "Total Pago", "Saldo"])
    # Linhas 7-8: plantões PS URGENCIA
    ws.append(["01/03/2026 07:00", "PR - SÃO MATEUS DO SUL - PA - PS - URGENCIA E EMERGENCIA - SPM",
               "Normal", "12:00", 1150.0, 1150.0, 0.0, 1150.0])
    ws.append(["02/03/2026 19:00", "PR - SÃO MATEUS DO SUL - PA - PS - URGENCIA E EMERGENCIA - SPM",
               "Noturno", "12:00", 1150.0, 1150.0, 0.0, 1150.0])
    # Linha 9: plantão PLANTONISTA
    ws.append(["03/03/2026 19:00", "PR - SÃO MATEUS DO SUL - PA - PLANTONISTA CLINICO - SPM",
               "Noturno", "12:00", 1150.0, 1150.0, 0.0, 1150.0])
    # Linhas 10-11: taxas (coluna Local referenciando PLANTONISTA)
    ws.append(["PR - SÃO MATEUS DO SUL - PA - PLANTONISTA CLINICO - SPM",
               "PR - SÃO MATEUS DO SUL - PA - PLANTONISTA CLINICO - SPM",
               "SPM - Taxa - Pega Plantão", "SPM - Taxa - Pega Plantão", "SPM - Taxa - Pega Plantão",
               -10.0, 0.0, -10.0])
    ws.append(["PR - SÃO MATEUS DO SUL - PA - PLANTONISTA CLINICO - SPM",
               "PR - SÃO MATEUS DO SUL - PA - PLANTONISTA CLINICO - SPM",
               "SPM - Taxa - Transf", "SPM - Taxa - Transf", "SPM - Taxa - Transf",
               -10.0, 0.0, -10.0])
    # Linha 12: Total
    ws.append(["Total", "", "3 plantões", "36:00", "", 3430.0, 0.0, 3430.0])

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parser_adriano_dois_locais_gera_UM_registro():
    """Com 2 locais distintos, parser deve retornar 1 registro (não 2)
    com saldo = Total do XLSX (R$ 3.430)."""
    data = _build_xlsx_adriano_dois_locais()
    records = parse_relatorio(BytesIO(data))

    # Filtra só os registros do Adriano
    adriano = [r for r in records if "ADRIANO" in (r.get("nome_prestador") or "")]

    assert len(adriano) == 1, (
        f"Esperava 1 registro para ADRIANO, veio {len(adriano)}. "
        f"Parser não pode fragmentar por local (CLAUDE.md regra 1). "
        f"Registros: {adriano}"
    )
    assert abs(adriano[0]["saldo"] - 3430.0) < 0.01, (
        f"Esperava saldo R$ 3.430 (Total do XLSX), veio R$ {adriano[0]['saldo']:.2f}"
    )
