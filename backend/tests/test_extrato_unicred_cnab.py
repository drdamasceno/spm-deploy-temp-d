"""Testes do parser CNAB-240 do extrato Unicred (banco 136).

Fixture é arquivo real exportado pelo internet banking Unicred em 05/05/2026
(período 01/04 → 05/05/2026, conta 6688055). 163 lançamentos confirmados,
saldo final R$ 943,01 (verificado contra extrato PDF do mesmo dia).
"""
from pathlib import Path

import pytest

from backend.src.extrato_unicred import NaturezaLancamento
from backend.src.extrato_unicred_cnab import (
    eh_cnab240_unicred,
    parse_extrato_unicred_cnab240,
)


FIXTURES = Path(__file__).parent / "fixtures"
ARQUIVO = FIXTURES / "extrato_unicred_05052026.cnab240"


@pytest.fixture(scope="module")
def raw_bytes() -> bytes:
    with open(ARQUIVO, "rb") as f:
        return f.read()


def test_detector_aceita_arquivo_unicred(raw_bytes: bytes):
    assert eh_cnab240_unicred(raw_bytes) is True


def test_detector_rejeita_pdf():
    assert eh_cnab240_unicred(b"%PDF-1.4\n" + b"x" * 300) is False


def test_detector_rejeita_arquivo_curto():
    assert eh_cnab240_unicred(b"abc") is False


def test_detector_rejeita_outro_banco():
    # Linha de 240 chars, banco '237' (Bradesco) em vez de '136'
    fake = ("237" + "0000" + "0" + " " * 232).encode("latin-1")
    assert eh_cnab240_unicred(fake) is False


def test_parse_extrai_163_transacoes(raw_bytes: bytes):
    _, txs = parse_extrato_unicred_cnab240(raw_bytes)
    assert len(txs) == 163, f"Esperado 163, obtido {len(txs)}"


def test_parse_metadados(raw_bytes: bytes):
    meta, _ = parse_extrato_unicred_cnab240(raw_bytes)
    assert meta.banco == "UNICRED"
    assert meta.periodo_inicio == "2026-04-07"
    assert meta.periodo_fim == "2026-05-05"
    assert abs(meta.saldo_final - 943.01) < 0.01, f"saldo_final={meta.saldo_final}"


def test_parse_saldo_bate_com_creditos_menos_debitos(raw_bytes: bytes):
    """Saldo final do trailer deve igualar soma de créditos − débitos."""
    meta, txs = parse_extrato_unicred_cnab240(raw_bytes)
    creditos = sum(t.valor for t in txs if t.valor > 0)
    debitos = sum(t.valor for t in txs if t.valor < 0)
    assert abs((creditos + debitos) - meta.saldo_final) < 0.01, (
        f"créditos {creditos:.2f} + débitos {debitos:.2f} = "
        f"{creditos + debitos:.2f} ≠ saldo_final {meta.saldo_final:.2f}"
    )


def test_parse_distribuicao_por_natureza(raw_bytes: bytes):
    """Sanidade: distribuição esperada (verificada manualmente em 2026-05-06)."""
    _, txs = parse_extrato_unicred_cnab240(raw_bytes)
    contagens: dict[str, int] = {}
    for t in txs:
        contagens[t.natureza.value] = contagens.get(t.natureza.value, 0) + 1

    # Pelo menos um de cada natureza esperada
    assert contagens.get("PIX_CREDITO", 0) > 0
    assert contagens.get("PIX_DEBITO", 0) > 0
    assert contagens.get("LIQUIDACAO_TITULO", 0) > 0
    assert contagens.get("ARRECADACAO", 0) > 0
    assert contagens.get("ESTORNO", 0) > 0
    assert contagens.get("TARIFA_CONTA", 0) > 0
    assert contagens.get("INTEGRALIZACAO_CAPITAL", 0) > 0


def test_parse_titular_extraido_apos_barra(raw_bytes: bytes):
    """Histórico 'CRED PIX / SOCIEDADE PARANAENSE...' produz titular_pix."""
    _, txs = parse_extrato_unicred_cnab240(raw_bytes)
    com_titular = [t for t in txs if t.titular_pix]
    assert len(com_titular) > 100, "esperado maioria das txs com titular extraído"

    primeira_credito = next(t for t in txs if t.natureza == NaturezaLancamento.PIX_CREDITO)
    assert "PARANAENSE" in (primeira_credito.titular_pix or "")


def test_parse_sinais_corretos(raw_bytes: bytes):
    """Crédito (sinal C no CNAB) deve gerar valor positivo; débito (D), negativo."""
    _, txs = parse_extrato_unicred_cnab240(raw_bytes)
    creditos = [t for t in txs if t.natureza == NaturezaLancamento.PIX_CREDITO]
    debitos = [t for t in txs if t.natureza == NaturezaLancamento.PIX_DEBITO]
    assert all(t.valor > 0 for t in creditos), "PIX_CREDITO deveria ter valor positivo"
    assert all(t.valor < 0 for t in debitos), "PIX_DEBITO deveria ter valor negativo"


def test_parse_tarifa_conta_pj(raw_bytes: bytes):
    """Linhas 'PJ CONTA PJ 1' (cód 1046051, R$ 51,50) devem virar TARIFA_CONTA."""
    _, txs = parse_extrato_unicred_cnab240(raw_bytes)
    tarifas = [t for t in txs if t.natureza == NaturezaLancamento.TARIFA_CONTA]
    # Pelo menos 7 tarifas observadas no arquivo real (R$ 51,50 cada)
    assert len(tarifas) >= 7
    assert all(abs(abs(t.valor) - 51.50) < 0.01 for t in tarifas), (
        "tarifa PJ deveria ser sempre R$ 51,50"
    )


def test_parse_estorno_arrecadacao(raw_bytes: bytes):
    """ESTORNO tem prioridade sobre o código histórico — descrição contém 'EST ARREC'."""
    _, txs = parse_extrato_unicred_cnab240(raw_bytes)
    estornos = [t for t in txs if t.natureza == NaturezaLancamento.ESTORNO]
    # 12 estornos de multas + 2 estornos PIX = 14
    assert len(estornos) >= 12
    # Estornos de arrecadação são créditos (devolveram dinheiro)
    estornos_credito = [t for t in estornos if t.valor > 0]
    assert len(estornos_credito) >= 12
