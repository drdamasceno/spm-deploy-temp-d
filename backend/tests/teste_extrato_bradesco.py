"""Testes do parser do extrato Bradesco OFX (dados hardcoded)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from extrato_bradesco import extrair_titular_pix, classificar_transacao


# ============================================================
# 5 transacoes de exemplo hardcoded
# ============================================================

TRANSACOES_EXEMPLO = [
    {
        "trntype": "DEBIT",
        "dtposted": "20260401120000",
        "trnamt": "-1234,56",
        "fitid": "202604011",
        "memo": "TRANSFERENCIA PIX REM: JOAO DA SILVA   01/04",
        "esperado_tipo": "PIX_SAIDA",
        "esperado_titular": "JOAO DA SILVA",
        "esperado_data": "2026-04-01",
        "esperado_valor": -1234.56,
    },
    {
        "trntype": "CREDIT",
        "dtposted": "20260401140000",
        "trnamt": "5000,00",
        "fitid": "202604012",
        "memo": "TED-TRANSF ELET RECEBIDO HOSPITAL ABC",
        "esperado_tipo": "TED_ENTRADA",
        "esperado_titular": "",
        "esperado_data": "2026-04-01",
        "esperado_valor": 5000.0,
    },
    {
        "trntype": "DEBIT",
        "dtposted": "20260402080000",
        "trnamt": "-45,67",
        "fitid": "202604021",
        "memo": "TARIFA BANCARIA MANUTENCAO CONTA",
        "esperado_tipo": "TARIFA_BANCARIA",
        "esperado_titular": "",
        "esperado_data": "2026-04-02",
        "esperado_valor": -45.67,
    },
    {
        "trntype": "CREDIT",
        "dtposted": "20260403090000",
        "trnamt": "2000,00",
        "fitid": "202604031",
        "memo": "INVEST FACIL APLICACAO AUTOMATICA",
        "esperado_tipo": "INVEST_FACIL",
        "esperado_titular": "",
        "esperado_data": "2026-04-03",
        "esperado_valor": 2000.0,
    },
    {
        "trntype": "DEBIT",
        "dtposted": "20260407110000",
        "trnamt": "-987,65",
        "fitid": "202604071",
        "memo": "PIX REM: MARIA SANTOS   07/04",
        "esperado_tipo": "PIX_SAIDA",
        "esperado_titular": "MARIA SANTOS",
        "esperado_data": "2026-04-07",
        "esperado_valor": -987.65,
    },
]


def test_classificar_transacao():
    """Testa classificacao automatica por MEMO."""
    print("Testando classificar_transacao...")
    for t in TRANSACOES_EXEMPLO:
        tipo = classificar_transacao(t["memo"], t["trntype"])
        assert tipo == t["esperado_tipo"], (
            "MEMO=[{}] tipo=[{}] esperado=[{}]".format(t["memo"], tipo, t["esperado_tipo"]))
    print("  OK: {} casos passaram".format(len(TRANSACOES_EXEMPLO)))


def test_extrair_titular_pix():
    """Testa extracao do titular PIX do MEMO."""
    print("Testando extrair_titular_pix...")
    for t in TRANSACOES_EXEMPLO:
        titular = extrair_titular_pix(t["memo"])
        assert titular == t["esperado_titular"], (
            "MEMO=[{}] titular=[{}] esperado=[{}]".format(t["memo"], titular, t["esperado_titular"]))
    print("  OK: {} casos passaram".format(len(TRANSACOES_EXEMPLO)))


def test_parse_data():
    """Testa conversao de DTPOSTED para YYYY-MM-DD."""
    from extrato_bradesco import _parse_data, _parse_valor
    for t in TRANSACOES_EXEMPLO:
        data = _parse_data(t["dtposted"])
        assert data == t["esperado_data"], (
            "dtposted=[{}] data=[{}] esperado=[{}]".format(t["dtposted"], data, t["esperado_data"]))
        valor = _parse_valor(t["trnamt"])
        assert abs(valor - t["esperado_valor"]) < 0.001, (
            "trnamt=[{}] valor=[{}] esperado=[{}]".format(t["trnamt"], valor, t["esperado_valor"]))
    print("  OK: conversao de data e valor")


def test_parse_extrato_arquivo_inexistente():
    """Garante que FileNotFoundError é lançado para arquivo inexistente."""
    from extrato_bradesco import parse_extrato
    try:
        parse_extrato("/nao/existe/extrato.ofx")
        assert False, "Deveria ter lancado FileNotFoundError"
    except FileNotFoundError:
        print("  OK: FileNotFoundError para arquivo inexistente")


if __name__ == '__main__':
    test_classificar_transacao()
    test_extrair_titular_pix()
    test_parse_data()
    test_parse_extrato_arquivo_inexistente()
    print()
    print("Todos os testes passaram!")
