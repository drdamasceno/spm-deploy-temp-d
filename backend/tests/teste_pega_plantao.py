"""Testes do parser do Pega Plantao (dados hardcoded)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pega_plantao import extrair_cabecalho_prestador, extrair_pix_info


# ============================================================
# Dados de exemplo hardcoded (5 casos de teste)
# ============================================================

LINHA_A_EXEMPLOS = [
    ("JOAO DA SILVA  -  123456/SP",   {"nome_prestador": "JOAO DA SILVA",   "crm": "123456", "uf": "SP"}),
    ("MARIA SANTOS - 78901/RJ",        {"nome_prestador": "MARIA SANTOS",     "crm": "78901",  "uf": "RJ"}),
    ("CARLOS OLIVEIRA  -  CRM 54321/MG", {"nome_prestador": "CARLOS OLIVEIRA", "crm": "54321",  "uf": "MG"}),
    ("ANA PAULA FERREIRA",             {"nome_prestador": "ANA PAULA FERREIRA","crm": "",       "uf": ""}),
    ("DR. PEDRO SOUZA  -  99999/BA",   {"nome_prestador": "DR. PEDRO SOUZA",  "crm": "99999",  "uf": "BA"}),
]

LINHA_B_EXEMPLOS = [
    (
        "Transacao: PIX  Tipo de Documento: CPF  Chave Pix: 12345678900  Documento: 12345678900  Razao social: ",
        {"tipo_doc": "CPF", "chave_pix": "12345678900", "documento": "12345678900", "razao_social_pj": ""},
    ),
    (
        "Transacao: PIX  Tipo de Documento: CNPJ  Chave Pix: 12345678000190  Documento: 12345678000190  Razao social: CLINICA DR FABIO LTDA",
        {"tipo_doc": "CNPJ", "chave_pix": "12345678000190", "documento": "12345678000190", "razao_social_pj": "CLINICA DR FABIO LTDA"},
    ),
    (
        "Transacao: PIX  Tipo de Documento: CPF  Chave Pix: maria@email.com  Documento: 98765432100  Razao social: ",
        {"tipo_doc": "CPF", "chave_pix": "maria@email.com", "documento": "98765432100", "razao_social_pj": ""},
    ),
    (
        "Transacao: PIX  Tipo de Documento: CNPJ  Chave Pix: +5511999999999  Documento: 99887766000155  Razao social: GLENIO SERVICOS MEDICOS",
        {"tipo_doc": "CNPJ", "chave_pix": "+5511999999999", "documento": "99887766000155", "razao_social_pj": "GLENIO SERVICOS MEDICOS"},
    ),
    (
        "Transacao: PIX  Tipo de Documento: CPF  Chave Pix: 55544433322  Documento: 55544433322  Razao social: ",
        {"tipo_doc": "CPF", "chave_pix": "55544433322", "documento": "55544433322", "razao_social_pj": ""},
    ),
]


def test_cabecalho_prestador():
    """Testa extração de nome/CRM/UF da linha A."""
    print("Testando extrair_cabecalho_prestador...")
    for entrada, esperado in LINHA_A_EXEMPLOS:
        resultado = extrair_cabecalho_prestador(entrada)
        for campo, valor in esperado.items():
            assert resultado[campo] == valor, (
                "Falha em [{}] campo [{}]: esperado=[{}] obtido=[{}]".format(
                    entrada, campo, valor, resultado[campo]))
    print("  OK: {} casos passaram".format(len(LINHA_A_EXEMPLOS)))


def test_pix_info():
    """Testa extração de info PIX da linha B."""
    print("Testando extrair_pix_info...")
    for entrada, esperado in LINHA_B_EXEMPLOS:
        resultado = extrair_pix_info(entrada)
        for campo, valor in esperado.items():
            assert resultado[campo] == valor, (
                "Falha em campo [{}]: esperado=[{}] obtido=[{}]".format(
                    campo, valor, resultado[campo]))
    print("  OK: {} casos passaram".format(len(LINHA_B_EXEMPLOS)))


def test_parse_relatorio_arquivo_inexistente():
    """Garante que FileNotFoundError é lançado para arquivo inexistente."""
    from pega_plantao import parse_relatorio
    try:
        parse_relatorio("/nao/existe/arquivo.xlsx")
        assert False, "Deveria ter lançado FileNotFoundError"
    except FileNotFoundError:
        print("  OK: FileNotFoundError para arquivo inexistente")


if __name__ == '__main__':
    test_cabecalho_prestador()
    test_pix_info()
    test_parse_relatorio_arquivo_inexistente()
    print()
    print("Todos os testes passaram!")
