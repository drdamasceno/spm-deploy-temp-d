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
ARQUIVO_LAYOUT_NOVO = FIXTURES / "Extrato_Unicred_30042026_layout_novo.pdf"


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


# ─────────────────── Layout novo do PDF Unicred (a partir 2026-05) ───────────────────
# A Unicred mudou o template do PDF — agora o histórico vem fragmentado em
# linhas adjacentes (anterior e posterior à linha de data+valor+saldo).
# Os formatos coexistem: alguns lançamentos saem inline ("DATA texto - R$ x R$ y"),
# outros split ("DATA - R$ x R$ y" + histórico nas linhas vizinhas).

def test_layout_novo_parser_lê_pelo_menos_100_transacoes():
    """Smoke test do PDF de 30/04/2026 exportado com layout novo."""
    parser = UnicredParser()
    txs = parser.parse(ARQUIVO_LAYOUT_NOVO)
    # Período 01-30/04 tem ~127 lançamentos no extrato real.
    assert len(txs) >= 100, f"Esperado >=100, obtido {len(txs)}"


def test_layout_novo_metadados_corretos():
    parser = UnicredParser()
    meta = parser.extrair_metadados(ARQUIVO_LAYOUT_NOVO)
    assert meta.banco == "UNICRED"
    assert meta.periodo_inicio == "2026-04-01"
    assert meta.periodo_fim == "2026-04-30"


def test_layout_novo_sinais_corretos():
    """INTEGRALIZACAO PARCIAL DE CAPITAL aparece como '- R$ 80,00' no PDF.
    Bug original: regex inline capturava o '-' como histórico e perdia o sinal.
    """
    parser = UnicredParser()
    txs = parser.parse(ARQUIVO_LAYOUT_NOVO)
    integralizacoes = [t for t in txs if t.natureza == NaturezaLancamento.INTEGRALIZACAO_CAPITAL]
    assert len(integralizacoes) >= 3
    # Todas devem ser débitos (valor negativo)
    assert all(t.valor < 0 for t in integralizacoes), (
        f"INTEGRALIZACAO deveria ter valor negativo: {[t.valor for t in integralizacoes]}"
    )


def test_layout_novo_classifica_pix_credito():
    """Pelo menos uma transação 'CREDITO RECEBIMENTO DE PIX' classifica como PIX_CREDITO."""
    parser = UnicredParser()
    txs = parser.parse(ARQUIVO_LAYOUT_NOVO)
    creditos_pix = [t for t in txs if t.natureza == NaturezaLancamento.PIX_CREDITO]
    assert len(creditos_pix) >= 5, "Esperava ≥5 PIX_CREDITO"
    assert all(t.valor > 0 for t in creditos_pix)
