"""Testes do parser de extrato Unicred PDF."""
from pathlib import Path
import pytest
from backend.src.extrato_unicred import (
    UnicredParser,
    NaturezaLancamento,
    TransacaoUnicredParsed,
)

FIXTURES = Path(__file__).parent / "fixtures"
ARQUIVO = FIXTURES / "Comp_Unicred_20042026.pdf"


def test_parser_extrai_metadados_conta():
    parser = UnicredParser()
    meta = parser.extrair_metadados(ARQUIVO)
    assert meta.banco == "UNICRED"
    assert meta.conta == "6688055"
    assert meta.cliente_razao_social.upper().startswith("SOCIEDADE PARANAENSE")
    assert meta.periodo_inicio  # ex: "2026-03-22"
    assert meta.periodo_fim


def test_parser_extrai_pelo_menos_40_linhas():
    parser = UnicredParser()
    transacoes = parser.parse(ARQUIVO)
    assert len(transacoes) >= 40, f"Esperado >=40 linhas, obtido {len(transacoes)}"


def test_saldo_inicial_zero_saldo_final_positivo():
    parser = UnicredParser()
    meta = parser.extrair_metadados(ARQUIVO)
    assert meta.saldo_anterior == 0.0
    assert meta.saldo_final > 0.0


def test_parse_tem_pix_credito_e_debito():
    parser = UnicredParser()
    txs = parser.parse(ARQUIVO)
    creditos = [t for t in txs if t.natureza == NaturezaLancamento.PIX_CREDITO]
    debitos = [t for t in txs if t.natureza == NaturezaLancamento.PIX_DEBITO]
    assert creditos, "Esperado ao menos um PIX crédito"
    assert debitos, "Esperado ao menos um PIX débito"


def test_parse_soma_bate_com_saldo_final():
    parser = UnicredParser()
    meta = parser.extrair_metadados(ARQUIVO)
    txs = parser.parse(ARQUIVO)
    soma = meta.saldo_anterior + sum(t.valor for t in txs)
    # Tolerância de centavos
    assert abs(soma - meta.saldo_final) < 1.0, (
        f"Soma {soma} divergiu do saldo final {meta.saldo_final}"
    )
