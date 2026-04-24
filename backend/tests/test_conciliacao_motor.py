"""
Testes unitários do motor backend/src/conciliacao_spm.py.

Fixtures baseadas na rodada real 491cbb56 (São Mateus do Sul 03/2026)
— 22 registros_pp, 7 PIX de saída relevantes. Todos os dados foram
extraídos dos arquivos ~/Downloads/SPM - FB - Sao Mateus do Sul - 03.26.xlsx
e ~/Downloads/EXTRATO_POR_PERIODO_240426_010813.ofx em 2026-04-24.
"""
from __future__ import annotations

import pytest

from backend.src import conciliacao_spm


# PP: apenas os registros com saldo > 0 necessários para cobrir os 16 casos
# (MATCH_AUTOMATICO + MANUAL_PENDENTE + NAO_CLASSIFICADO) da rodada.
PP_SAO_MATEUS = [
    {"nome_prestador": "DR ADRIANO PEREIRA GIOVANNI DA COSTA", "saldo": 4600.00,
     "razao_social_pj": "", "tipo_doc": "", "documento": "",
     "contrato": "SAO MATEUS DO SUL", "mes_competencia": "2026-03"},
    {"nome_prestador": "DR AUGUSTO PINTO JÚNIOR", "saldo": 5376.37,
     "razao_social_pj": "A P J SERVICOS MEDICOS LTDA", "tipo_doc": "CNPJ",
     "documento": "50.065.880/0001-52",
     "contrato": "SAO MATEUS DO SUL", "mes_competencia": "2026-03"},
    {"nome_prestador": "DR ENMANUEL RIVERA LEON", "saldo": 1130.00,
     "razao_social_pj": "", "tipo_doc": "CPF", "documento": "082.979.361-55",
     "contrato": "SAO MATEUS DO SUL", "mes_competencia": "2026-03"},
    {"nome_prestador": "DR JAIR PAIXÃO JUNIOR", "saldo": 1106.20,
     "razao_social_pj": "JAIR PAIXAO JUNIOR SERVICOS MEDICOS LTDA",
     "tipo_doc": "CNPJ", "documento": "36.423.822/0001-22",
     "contrato": "SAO MATEUS DO SUL", "mes_competencia": "2026-03"},
    {"nome_prestador": "DR JOÃO FELIPE ROCHA PINHEIRO", "saldo": 12438.33,
     "razao_social_pj": "", "tipo_doc": "Email", "documento": "",
     "contrato": "SAO MATEUS DO SUL", "mes_competencia": "2026-03"},
    {"nome_prestador": "DR RAFAEL SAMBUICHI", "saldo": 5253.37,
     "razao_social_pj": "RBS SERVICOS MEDICOS LTDA", "tipo_doc": "CNPJ",
     "documento": "55.404.197/0001-16",
     "contrato": "SAO MATEUS DO SUL", "mes_competencia": "2026-03"},
    {"nome_prestador": "DR VINICIUS HARUO KITA", "saldo": 1130.00,
     "razao_social_pj": "vhk - serviços de saúde ltda", "tipo_doc": "CNPJ",
     "documento": "59.822.967/0001-00",
     "contrato": "SAO MATEUS DO SUL", "mes_competencia": "2026-03"},
    {"nome_prestador": "DR YOIRE ALFONSO PUERTAS", "saldo": 7000.00,
     "razao_social_pj": "Yoire Alfonso", "tipo_doc": "CPF",
     "documento": "067.470.581-51",
     "contrato": "SAO MATEUS DO SUL", "mes_competencia": "2026-03"},
    {"nome_prestador": "DRA ALINE CORRÊA DA SILVA", "saldo": 1180.00,
     "razao_social_pj": "ALINE CORRÊA DA SILVA Observação: SÓCIO COTISTA",
     "tipo_doc": "Telefone", "documento": "",
     "contrato": "SAO MATEUS DO SUL", "mes_competencia": "2026-03"},
    {"nome_prestador": "DRA BEATRIZ DE OLIVEIRA NOBRE", "saldo": 1200.00,
     "razao_social_pj": "RBS SERVICOS MEDICOS LTDA", "tipo_doc": "CNPJ",
     "documento": "55.404.197/0001-16",
     "contrato": "SAO MATEUS DO SUL", "mes_competencia": "2026-03"},
    {"nome_prestador": "DRA BIANCA DA SILVA ORMIANIN", "saldo": 9480.00,
     "razao_social_pj": "ORMIANIN SERVICOS MEDICOS LTDA", "tipo_doc": "CNPJ",
     "documento": "64.468.244/0001-86",
     "contrato": "SAO MATEUS DO SUL", "mes_competencia": "2026-03"},
    {"nome_prestador": "DRA CLAUDINEIA SOARES DIAS", "saldo": 3480.00,
     "razao_social_pj": "", "tipo_doc": "CPF", "documento": "009.447.729-94",
     "contrato": "SAO MATEUS DO SUL", "mes_competencia": "2026-03"},
    {"nome_prestador": "DRA FRANTHIESKA LILY RODRIGUES GRUNDMANN",
     "saldo": 15130.00,
     "razao_social_pj": "ROBLE & GRUNDMANN MEDICINA E SAUDE LTDA",
     "tipo_doc": "CNPJ", "documento": "62.060.869/0001-89",
     "contrato": "SAO MATEUS DO SUL", "mes_competencia": "2026-03"},
    {"nome_prestador": "DRA GABRIELLE CRISTINA FERREIRA", "saldo": 2500.00,
     "razao_social_pj": "GC FERREIRA MEDICINA LTDA", "tipo_doc": "CNPJ",
     "documento": "53.541.995/0001-64",
     "contrato": "SAO MATEUS DO SUL", "mes_competencia": "2026-03"},
    {"nome_prestador": "DRA JAQUELINE DOS SANTOS CHARGAS", "saldo": 1130.00,
     "razao_social_pj": "", "tipo_doc": "CPF", "documento": "090.067.919-03",
     "contrato": "SAO MATEUS DO SUL", "mes_competencia": "2026-03"},
    {"nome_prestador": "DRA LAILA NAIANE DA SILVA BAHIA", "saldo": 3530.00,
     "razao_social_pj": "", "tipo_doc": "Email", "documento": "",
     "contrato": "SAO MATEUS DO SUL", "mes_competencia": "2026-03"},
    {"nome_prestador": "DRA VANILSE VALENTE DO AMARAL", "saldo": 1200.00,
     "razao_social_pj": "", "tipo_doc": "Aleatoria", "documento": "",
     "contrato": "SAO MATEUS DO SUL", "mes_competencia": "2026-03"},
]


# Extrato: só os PIX de saída relevantes para os testes.
# tipo='PIX_SAIDA', valor negativo (convenção do parser bradesco).
EXTRATO_SAO_MATEUS = [
    {"fitid": "t01", "valor": -37521.66, "titular_pix": "DR ADRIANO PEREIRA GI",
     "tipo": "PIX_SAIDA", "data": "2026-04-16", "memo": "PIX DR ADRIANO"},
    {"fitid": "t02", "valor": -5376.37, "titular_pix": "A P J SERVICOS MEDICO",
     "tipo": "PIX_SAIDA", "data": "2026-04-16", "memo": "PIX A P J"},
    {"fitid": "t03", "valor": -1130.00, "titular_pix": "DR ENMANUEL RIVERA LE",
     "tipo": "PIX_SAIDA", "data": "2026-04-16", "memo": "PIX ENMANUEL"},
    {"fitid": "t04", "valor": -2983.20, "titular_pix": "AMDO SERVICOS MEDICOS",
     "tipo": "PIX_SAIDA", "data": "2026-04-14", "memo": "PIX AMDO"},
    {"fitid": "t05", "valor": -3580.00, "titular_pix": "PVNR SERVICOS MEDICOS",
     "tipo": "PIX_SAIDA", "data": "2026-04-14", "memo": "PIX PVNR"},
    {"fitid": "t06", "valor": -24000.00, "titular_pix": "AM SERVICOS MEDICOS L",
     "tipo": "PIX_SAIDA", "data": "2026-04-14", "memo": "PIX AM"},
    {"fitid": "t07", "valor": -7253.37, "titular_pix": "RBS SERVICOS MEDICOS",
     "tipo": "PIX_SAIDA", "data": "2026-04-16", "memo": "PIX RBS 1"},
    {"fitid": "t08", "valor": -15136.77, "titular_pix": "RBS SERVICOS MEDICOS",
     "tipo": "PIX_SAIDA", "data": "2026-04-16", "memo": "PIX RBS 2"},
    {"fitid": "t09", "valor": -2302.32, "titular_pix": "CKC SERVICOS MEDICOS",
     "tipo": "PIX_SAIDA", "data": "2026-04-14", "memo": "PIX CKC"},
    {"fitid": "t10", "valor": -12438.33, "titular_pix": "DR JOAO FELIPE ROCHA",
     "tipo": "PIX_SAIDA", "data": "2026-04-16", "memo": "PIX JOAO"},
    {"fitid": "t11", "valor": -1130.00, "titular_pix": "VHK - SERVICOS DE SAU",
     "tipo": "PIX_SAIDA", "data": "2026-04-14", "memo": "PIX VHK"},
    {"fitid": "t12", "valor": -19930.00, "titular_pix": "DR YOIRE ALFONSO PUER",
     "tipo": "PIX_SAIDA", "data": "2026-04-16", "memo": "PIX YOIRE"},
    {"fitid": "t13", "valor": -1180.00, "titular_pix": "DRA ALINE CORREA DA S",
     "tipo": "PIX_SAIDA", "data": "2026-04-14", "memo": "PIX ALINE"},
    {"fitid": "t14", "valor": -1200.00, "titular_pix": "PATUCCI SERVICOS EM S",
     "tipo": "PIX_SAIDA", "data": "2026-04-14", "memo": "PIX PATUCCI"},
    {"fitid": "t15", "valor": -2000.00, "titular_pix": "MKAZ SERVICOS MEDICOS",
     "tipo": "PIX_SAIDA", "data": "2026-04-16", "memo": "PIX MKAZ"},
    {"fitid": "t16", "valor": -3480.00, "titular_pix": "DRA CLAUDINEIA SOARES",
     "tipo": "PIX_SAIDA", "data": "2026-04-14", "memo": "PIX CLAUDINEIA"},
    {"fitid": "t17", "valor": -15130.00, "titular_pix": "ROBLE",
     "tipo": "PIX_SAIDA", "data": "2026-04-16", "memo": "PIX ROBLE"},
    {"fitid": "t18", "valor": -2500.00, "titular_pix": "GC FERREIRA MEDICINA",
     "tipo": "PIX_SAIDA", "data": "2026-04-14", "memo": "PIX GC"},
    {"fitid": "t19", "valor": -1130.00, "titular_pix": "JAQUELINE DOS SANTOS",
     "tipo": "PIX_SAIDA", "data": "2026-04-14", "memo": "PIX JAQUELINE"},
    {"fitid": "t20", "valor": -3530.00, "titular_pix": "DRA LAILA NAIANE DA S",
     "tipo": "PIX_SAIDA", "data": "2026-04-16", "memo": "PIX LAILA"},
    {"fitid": "t21", "valor": -9230.00, "titular_pix": "DRA VANILSE VALENTE D",
     "tipo": "PIX_SAIDA", "data": "2026-04-16", "memo": "PIX VANILSE"},
]


def _status_por_prestador(resultado: dict) -> dict:
    """Extrai {nome_prestador: status} da saída do motor."""
    return {r["nome_prestador"]: r["status"] for r in resultado["registros"]}


def test_sao_mateus_match_automatico_dos_10_legitimos():
    """
    Os 10 MATCH_AUTOMATICO legítimos (substring/exato + valor exato).
    Este teste estabelece o baseline — deve passar ANTES e DEPOIS do fix.
    """
    resultado = conciliacao_spm.conciliar(PP_SAO_MATEUS, EXTRATO_SAO_MATEUS, excecoes_pj={})
    status = _status_por_prestador(resultado)

    esperados_match = [
        "DR AUGUSTO PINTO JÚNIOR",
        "DR ENMANUEL RIVERA LEON",
        "DR JOÃO FELIPE ROCHA PINHEIRO",
        "DR VINICIUS HARUO KITA",
        "DRA ALINE CORRÊA DA SILVA",
        "DRA CLAUDINEIA SOARES DIAS",
        "DRA FRANTHIESKA LILY RODRIGUES GRUNDMANN",
        "DRA GABRIELLE CRISTINA FERREIRA",
        "DRA JAQUELINE DOS SANTOS CHARGAS",
        "DRA LAILA NAIANE DA SILVA BAHIA",
    ]
    for nome in esperados_match:
        assert status[nome] == "MATCH_AUTOMATICO", \
            f"{nome} deveria ser MATCH_AUTOMATICO, veio {status[nome]}"


def test_jair_nao_deve_ter_candidatos_fuzzy():
    """
    DR JAIR tem razão social 'JAIR PAIXAO JUNIOR SERVICOS MEDICOS LTDA'.
    Hoje o fuzzy partial_ratio >= 85 casa PJs não relacionadas que compartilham
    tokens 'SERVICOS MEDICOS LTDA' (AMDO, PVNR, AM, RBS, CKC).
    Após fix, JAIR deve cair em NAO_CLASSIFICADO — nenhum PIX legítimo existe
    para ele no extrato e fuzzy sobre PJ é proibido.
    """
    resultado = conciliacao_spm.conciliar(PP_SAO_MATEUS, EXTRATO_SAO_MATEUS, excecoes_pj={})
    jair = next(r for r in resultado["registros"]
                if r["nome_prestador"] == "DR JAIR PAIXÃO JUNIOR")
    assert jair["status"] == "NAO_CLASSIFICADO", \
        f"JAIR deveria ser NAO_CLASSIFICADO, veio {jair['status']} " \
        f"com {len(jair['pix_matched'])} candidatos"
    assert len(jair["pix_matched"]) == 0, \
        f"JAIR não deveria ter candidatos, tem {len(jair['pix_matched'])}"


def test_bianca_nao_deve_casar_mkaz_via_fuzzy():
    """
    DRA BIANCA tem razão 'ORMIANIN SERVICOS MEDICOS LTDA'.
    MKAZ SERVICOS MEDICOS é outra PJ — colisão de tokens 'SERVICOS MEDICOS'
    aciona fuzzy hoje. Após fix, BIANCA cai em NAO_CLASSIFICADO.
    """
    resultado = conciliacao_spm.conciliar(PP_SAO_MATEUS, EXTRATO_SAO_MATEUS, excecoes_pj={})
    bianca = next(r for r in resultado["registros"]
                  if r["nome_prestador"] == "DRA BIANCA DA SILVA ORMIANIN")
    assert bianca["status"] == "NAO_CLASSIFICADO", \
        f"BIANCA deveria ser NAO_CLASSIFICADO, veio {bianca['status']}"


def test_resultado_independente_da_ordem_do_pp():
    """
    Motor deve produzir resultado idêntico independente da ordem dos
    registros em pp_data. Hoje o consumo em MANUAL_PENDENTE é ordem-dependente
    (primeiro prestador a achar um candidato consome o PIX).
    """
    resultado_1 = conciliacao_spm.conciliar(PP_SAO_MATEUS, EXTRATO_SAO_MATEUS, excecoes_pj={})
    resultado_2 = conciliacao_spm.conciliar(list(reversed(PP_SAO_MATEUS)),
                                            EXTRATO_SAO_MATEUS, excecoes_pj={})

    status_1 = _status_por_prestador(resultado_1)
    status_2 = _status_por_prestador(resultado_2)

    assert status_1 == status_2, \
        f"Ordem mudou resultado. Diff: " \
        f"{[k for k in status_1 if status_1[k] != status_2[k]]}"
