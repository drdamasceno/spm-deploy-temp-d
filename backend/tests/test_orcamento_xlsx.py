"""Testes do parser de orçamento XLSX."""
from pathlib import Path
import pytest

from backend.src.orcamento_xlsx import (
    OrcamentoParser,
    NaturezaOrcamento,
    OrcamentoLinhaParsed,
)

FIXTURES = Path(__file__).parent / "fixtures"
ARQUIVO_ORCAMENTO = FIXTURES / "SPM_Orcamento_04_2026.xlsx"


def test_detecta_todas_6_secoes():
    parser = OrcamentoParser()
    secoes = parser.detectar_secoes(ARQUIVO_ORCAMENTO)
    # Cada item: (linha_inicio, natureza)
    naturezas = [n for (_, n) in secoes]
    assert NaturezaOrcamento.DESPESA_FIXA in naturezas
    assert NaturezaOrcamento.TRIBUTO in naturezas
    assert NaturezaOrcamento.SALARIO_VARIAVEL in naturezas
    assert NaturezaOrcamento.COMISSAO in naturezas
    assert NaturezaOrcamento.VALOR_VARIAVEL in naturezas
    assert NaturezaOrcamento.DESPESA_PROFISSIONAIS in naturezas
    assert len(secoes) == 6


def test_ordem_secoes_esperada():
    parser = OrcamentoParser()
    secoes = parser.detectar_secoes(ARQUIVO_ORCAMENTO)
    naturezas_ordem = [n for (_, n) in secoes]
    assert naturezas_ordem == [
        NaturezaOrcamento.DESPESA_FIXA,       # primeira, começa antes linha 10
        NaturezaOrcamento.TRIBUTO,
        NaturezaOrcamento.SALARIO_VARIAVEL,
        NaturezaOrcamento.COMISSAO,
        NaturezaOrcamento.VALOR_VARIAVEL,
        NaturezaOrcamento.DESPESA_PROFISSIONAIS,
    ]


def test_extrair_linhas_despesa_fixa_contagem():
    parser = OrcamentoParser()
    linhas = parser.extrair_linhas_secao(ARQUIVO_ORCAMENTO, NaturezaOrcamento.DESPESA_FIXA)
    # Sabemos pelo arquivo real que DESPESAS FIXAS tem ~56 linhas válidas.
    assert 40 <= len(linhas) <= 65, f"Esperado 40-65 linhas, obtido {len(linhas)}"
    for linha in linhas:
        assert linha.natureza == NaturezaOrcamento.DESPESA_FIXA
        assert linha.titular_razao_social
        assert linha.valor_previsto > 0


def test_extrair_linhas_despesa_fixa_tem_hugo():
    parser = OrcamentoParser()
    linhas = parser.extrair_linhas_secao(ARQUIVO_ORCAMENTO, NaturezaOrcamento.DESPESA_FIXA)
    nomes = [l.titular_razao_social.upper() for l in linhas]
    assert any("HUGO FERNANDES DAMASCENO" in n for n in nomes), \
        "Esperado encontrar HUGO FERNANDES DAMASCENO na seção DESPESAS FIXAS"


def test_extrair_linhas_tributos():
    parser = OrcamentoParser()
    linhas = parser.extrair_linhas_secao(ARQUIVO_ORCAMENTO, NaturezaOrcamento.TRIBUTO)
    categorias = {l.categoria for l in linhas if l.categoria}
    assert "COFINS FATURAMENTO" in categorias or any("COFINS" in c for c in categorias)


def test_parse_completo_retorna_todas_linhas():
    parser = OrcamentoParser()
    resultado = parser.parse_completo(ARQUIVO_ORCAMENTO)
    assert resultado.total_linhas > 100, \
        f"Esperado >100 linhas no orcamento completo, obtido {resultado.total_linhas}"
    assert resultado.linhas_por_secao[NaturezaOrcamento.DESPESA_FIXA] > 30
    assert resultado.linhas_por_secao[NaturezaOrcamento.TRIBUTO] >= 5
    # B5b: após fix, seção profissional = 55 linhas (antes 82 por causa de
    # contaminação com INVESTIMENTOS, DESPESAS PESSOAIS, cartões, empréstimos).
    assert 40 <= resultado.linhas_por_secao[NaturezaOrcamento.DESPESA_PROFISSIONAIS] <= 70, \
        f"Esperado 40-70 linhas DESPESA_PROFISSIONAIS (sem contaminação), obtido {resultado.linhas_por_secao[NaturezaOrcamento.DESPESA_PROFISSIONAIS]}"


def test_secao_profissionais_nao_inclui_investimentos_pessoais():
    """B5b: garantir que parser detecta fim de DESPESA_PROFISSIONAIS e não
    inclui linhas de INVESTIMENTOS, DESPESAS PESSOAIS DR HUGO, Cartões de Crédito,
    amortização Bradesco ou linhas-resumo."""
    parser = OrcamentoParser()
    linhas = parser.extrair_linhas_secao(
        ARQUIVO_ORCAMENTO, NaturezaOrcamento.DESPESA_PROFISSIONAIS
    )
    razoes_upper = [l.titular_razao_social.upper() for l in linhas]
    categorias_upper = [(l.categoria or "").upper() for l in linhas]

    # Investimentos pessoais / imobiliários do Hugo
    assert not any("ESTANCIA ALBATROZ" in r for r in razoes_upper), \
        "ESTANCIA ALBATROZ (investimento imobiliário) não pode aparecer em DESPESA_PROFISSIONAIS"
    assert not any("CANGUSSU" in r for r in razoes_upper), \
        "CANGUSSU (imóvel pessoal) não pode aparecer em DESPESA_PROFISSIONAIS"
    assert not any("PAYSAGE" in r for r in razoes_upper), \
        "PAYSAGE (condomínio pessoal) não pode aparecer"
    assert not any("ODIR PONTALTI" in r for r in razoes_upper), \
        "ODIR PONTALTI (terreno) não pode aparecer"
    assert not any("LAGOA AZUL PISCINAS" in r for r in razoes_upper), \
        "LAGOA AZUL PISCINAS (despesa pessoal) não pode aparecer"
    assert not any("NETDIGITAL" in r for r in razoes_upper), \
        "NETDIGITAL (despesa pessoal) não pode aparecer"
    assert not any("FATOR SEGURADORA" in r for r in razoes_upper), \
        "FATOR SEGURADORA (despesa pessoal) não pode aparecer"

    # Amortização de empréstimo Bradesco (41.666,67) — não é profissional
    bradesco_amortizacao = [
        l for l in linhas
        if "BRADESCO" in l.titular_razao_social.upper()
        and 41000 < l.valor_previsto < 42000
    ]
    assert not bradesco_amortizacao, \
        f"Amortização Bradesco 41.666 não pode aparecer em DESPESA_PROFISSIONAIS: {bradesco_amortizacao}"

    # Categoria "Pagamento de Empréstimos" não deve aparecer
    assert not any("EMPRÉSTIMOS" in c or "EMPRESTIMOS" in c for c in categorias_upper), \
        "Categorias de empréstimo não podem aparecer em DESPESA_PROFISSIONAIS"

    # Cartões de crédito pessoais
    cartoes_titulares = {"BB", "ITAÚ", "ITAU", "UNICRED", "SISPRIME", "SISPRIME ⚠️"}
    assert not any(r.strip() in cartoes_titulares for r in razoes_upper), \
        "Linhas de cartão de crédito pessoal não podem aparecer"

    # Sanity: todas as linhas válidas estão entre a linha 160 (header) e linha 225
    # (última linha válida antes dos blocos extras)
    for l in linhas:
        assert 160 <= l.linha_xlsx <= 225, \
            f"Linha {l.linha_xlsx} fora do intervalo esperado [160, 225]"


def test_empresa_derivada_sufixo_projeto():
    parser = OrcamentoParser()
    resultado = parser.parse_completo(ARQUIVO_ORCAMENTO)
    # Linhas com projeto terminando em "-FD" -> empresa FD
    linhas_fd = [l for l in resultado.linhas if l.empresa_codigo == "FD"]
    linhas_spm = [l for l in resultado.linhas if l.empresa_codigo == "SPM"]
    assert len(linhas_fd) >= 3, "Esperado pelo menos 3 linhas FD"
    assert len(linhas_spm) > len(linhas_fd), "Esperado mais linhas SPM que FD"


def test_parse_completo_hugo_spm():
    parser = OrcamentoParser()
    resultado = parser.parse_completo(ARQUIVO_ORCAMENTO)
    hugo = [l for l in resultado.linhas if "HUGO" in l.titular_razao_social.upper()]
    assert hugo, "Hugo deve aparecer no orcamento"
    assert all(l.empresa_codigo == "SPM" for l in hugo)
