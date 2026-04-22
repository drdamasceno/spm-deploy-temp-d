"""Testes do classificador de conciliação (3 camadas + cascata)."""
import pytest

from backend.src.classificador_conciliacao import (
    Sugestao,
    Transacao,
    LinhaOrcamento,
    Regra,
    eh_pagamento_intragrupo,
    eh_transferencia_interna,
    sugerir_por_regra,
    sugerir_por_similaridade,
    sugerir_por_valor,
    sugerir_cascata,
    normalizar_titular,
)


def test_normalizar_remove_acento_upper_trim():
    assert normalizar_titular("  José da Silva  ") == "JOSE DA SILVA"
    assert normalizar_titular("COND. Duque Hall SL0706") == "COND. DUQUE HALL SL0706"


def test_normalizar_preserva_numeros_e_pontuacao_util():
    assert normalizar_titular("04.368.898/0001-06 COPEL-DIS") == "04.368.898/0001-06 COPEL-DIS"


def test_normalizar_str_vazia_ou_none():
    assert normalizar_titular("") == ""
    assert normalizar_titular(None) == ""


def test_normalizar_colapsa_espacos():
    assert normalizar_titular("COND   DUQUE   HALL") == "COND DUQUE HALL"


def test_sugerir_por_regra_match_direto():
    tx = Transacao(id="tx1", titular_pix="Condominio Duque Hall", valor=-581.82, data_movimento="2026-04-09", origem_banco="UNICRED")
    linha = LinhaOrcamento(id="l1", titular_razao_social="CENTRO EMPRESARIAL DUQUE HALL SL0705", valor_previsto=580.46, saldo_pendente=580.46)
    regra = Regra(id="r1", titular_pix_padrao="CONDOMINIO DUQUE HALL", orcamento_linha_id="l1", confianca_base=0.95, ativa=True)

    sugs = sugerir_por_regra(tx, [linha], [regra])
    assert len(sugs) == 1
    assert sugs[0].orcamento_linha_id == "l1"
    assert sugs[0].origem == "REGRA"
    assert sugs[0].confianca >= 0.95


def test_sugerir_por_regra_ignora_inativa():
    tx = Transacao(id="tx1", titular_pix="Fornecedor X", valor=-100.0, data_movimento="2026-04-09", origem_banco="UNICRED")
    regra = Regra(id="r1", titular_pix_padrao="FORNECEDOR X", orcamento_linha_id="l1", confianca_base=0.95, ativa=False)
    assert sugerir_por_regra(tx, [], [regra]) == []


def test_sugerir_por_regra_sem_match():
    tx = Transacao(id="tx1", titular_pix="Outro Titular", valor=-100.0, data_movimento="2026-04-09", origem_banco="UNICRED")
    regra = Regra(id="r1", titular_pix_padrao="CONDOMINIO DUQUE HALL", orcamento_linha_id="l1", confianca_base=0.95, ativa=True)
    assert sugerir_por_regra(tx, [], [regra]) == []


def test_sugerir_por_similaridade_match_alto():
    tx = Transacao(id="tx1", titular_pix="COPEL-DIS", valor=-88.53, data_movimento="2026-04-09", origem_banco="UNICRED")
    linha = LinhaOrcamento(id="l1", titular_razao_social="COPEL DISTRIBUICAO S.A.", valor_previsto=88.53, saldo_pendente=88.53)
    sugs = sugerir_por_similaridade(tx, [linha])
    assert len(sugs) == 1
    assert sugs[0].orcamento_linha_id == "l1"
    assert sugs[0].origem == "SIMILARIDADE"
    assert 0.70 <= sugs[0].confianca <= 0.95


def test_sugerir_por_similaridade_valor_divergente():
    tx = Transacao(id="tx1", titular_pix="COPEL-DIS", valor=-500.00, data_movimento="2026-04-09", origem_banco="UNICRED")
    linha = LinhaOrcamento(id="l1", titular_razao_social="COPEL DISTRIBUICAO S.A.", valor_previsto=88.53, saldo_pendente=88.53)
    # valor diverge >2% → não sugere
    assert sugerir_por_similaridade(tx, [linha]) == []


def test_sugerir_por_similaridade_titular_diverge():
    tx = Transacao(id="tx1", titular_pix="MAGMA MATERIAIS", valor=-88.53, data_movimento="2026-04-09", origem_banco="UNICRED")
    linha = LinhaOrcamento(id="l1", titular_razao_social="COPEL DISTRIBUICAO S.A.", valor_previsto=88.53, saldo_pendente=88.53)
    # nomes distintos → similarity baixa → não sugere
    assert sugerir_por_similaridade(tx, [linha]) == []


def test_sugerir_por_valor_unico_match():
    tx = Transacao(id="tx1", titular_pix="UNKNOWN TITULAR", valor=-776.74, data_movimento="2026-04-09", origem_banco="UNICRED")
    linha = LinhaOrcamento(id="l1", titular_razao_social="COPEL SL 2003", valor_previsto=776.74, saldo_pendente=776.74)
    outra = LinhaOrcamento(id="l2", titular_razao_social="CLARO", valor_previsto=244.18, saldo_pendente=244.18)
    sugs = sugerir_por_valor(tx, [linha, outra])
    assert len(sugs) == 1
    assert sugs[0].orcamento_linha_id == "l1"
    assert sugs[0].origem == "VALOR"
    assert 0.30 <= sugs[0].confianca <= 0.60


def test_sugerir_por_valor_multiplas_candidatas_descarta():
    tx = Transacao(id="tx1", titular_pix="X", valor=-100.0, data_movimento="2026-04-09", origem_banco="UNICRED")
    l1 = LinhaOrcamento(id="l1", titular_razao_social="A", valor_previsto=100.0, saldo_pendente=100.0)
    l2 = LinhaOrcamento(id="l2", titular_razao_social="B", valor_previsto=100.0, saldo_pendente=100.0)
    # 2 candidatas por valor — ambiguidade → não sugere
    assert sugerir_por_valor(tx, [l1, l2]) == []


def test_cascata_regra_vence():
    tx = Transacao(id="tx1", titular_pix="Condominio Duque Hall", valor=-581.82, data_movimento="2026-04-09", origem_banco="UNICRED")
    linha_pela_regra = LinhaOrcamento(id="l1", titular_razao_social="CENTRO DUQUE HALL SL0705", valor_previsto=580.46, saldo_pendente=580.46)
    linha_pela_similaridade = LinhaOrcamento(id="l2", titular_razao_social="CENTRO DUQUE HALL SL0706", valor_previsto=581.82, saldo_pendente=581.82)
    regra = Regra(id="r1", titular_pix_padrao="CONDOMINIO DUQUE HALL", orcamento_linha_id="l1", confianca_base=0.95, ativa=True)

    sugs = sugerir_cascata(tx, [linha_pela_regra, linha_pela_similaridade], [regra])
    assert sugs[0].origem == "REGRA"  # vence mesmo com valor menos exato


def test_cascata_fallback_similaridade():
    tx = Transacao(id="tx1", titular_pix="COPEL-DIS", valor=-88.53, data_movimento="2026-04-09", origem_banco="UNICRED")
    linha = LinhaOrcamento(id="l1", titular_razao_social="COPEL DISTRIBUICAO S.A.", valor_previsto=88.53, saldo_pendente=88.53)
    sugs = sugerir_cascata(tx, [linha], regras=[])
    assert len(sugs) == 1
    assert sugs[0].origem == "SIMILARIDADE"


def test_cascata_fallback_valor():
    tx = Transacao(id="tx1", titular_pix="UNKNOWN", valor=-776.74, data_movimento="2026-04-09", origem_banco="UNICRED")
    linha = LinhaOrcamento(id="l1", titular_razao_social="COPEL SL 2003", valor_previsto=776.74, saldo_pendente=776.74)
    sugs = sugerir_cascata(tx, [linha], regras=[])
    assert len(sugs) == 1
    assert sugs[0].origem == "VALOR"


def test_cascata_sem_sugestao():
    tx = Transacao(id="tx1", titular_pix="UNKNOWN", valor=-999.99, data_movimento="2026-04-09", origem_banco="UNICRED")
    linha = LinhaOrcamento(id="l1", titular_razao_social="COPEL", valor_previsto=100.0, saldo_pendente=100.0)
    assert sugerir_cascata(tx, [linha], regras=[]) == []


def test_eh_transferencia_interna_detecta_razao_propria():
    tx = Transacao(
        id="x",
        titular_pix="SOCIEDADE PARANAENSE DE MEDICINA LTDA",
        valor=-60000,
        data_movimento="2026-04-17",
        origem_banco="BRADESCO",
    )
    assert eh_transferencia_interna(tx) is True


def test_eh_transferencia_interna_falso_para_terceiro():
    tx = Transacao(
        id="x",
        titular_pix="JOAO DA SILVA LTDA",
        valor=-100,
        data_movimento="2026-04-17",
        origem_banco="UNICRED",
    )
    assert eh_transferencia_interna(tx) is False


def test_eh_transferencia_interna_falso_para_fd():
    """FD agora é PAGAMENTO_INTRAGRUPO, não TRANSFERENCIA_INTERNA."""
    tx = Transacao(
        id="x",
        titular_pix="FD GESTAO INTELIGENTE DE NEGOCIOS LTDA",
        valor=-55473.33,
        data_movimento="2026-04-13",
        origem_banco="UNICRED",
    )
    assert eh_transferencia_interna(tx) is False
    assert eh_pagamento_intragrupo(tx) is True


def test_eh_pagamento_intragrupo_detecta_fd():
    tx = Transacao(
        id="x",
        titular_pix="FD GESTAO INTELIGENTE",
        valor=-55473.33,
        data_movimento="2026-04-13",
        origem_banco="UNICRED",
    )
    assert eh_pagamento_intragrupo(tx) is True


def test_eh_pagamento_intragrupo_falso_para_spm():
    tx = Transacao(
        id="x",
        titular_pix="SOCIEDADE PARANAENSE DE MEDICINA LTDA",
        valor=-1000,
        data_movimento="2026-04-17",
        origem_banco="BRADESCO",
    )
    assert eh_pagamento_intragrupo(tx) is False


def test_cascata_transferencia_interna_retorna_vazio():
    tx = Transacao(
        id="x",
        titular_pix="SOCIEDADE PARANAENSE DE MEDICINA LTDA",
        valor=-60000,
        data_movimento="2026-04-17",
        origem_banco="BRADESCO",
    )
    linha = LinhaOrcamento(
        id="l1",
        titular_razao_social="HUGO FERNANDES DAMASCENO",
        valor_previsto=60000,
        saldo_pendente=60000,
    )
    assert sugerir_cascata(tx, [linha], []) == []


def test_cascata_pagamento_intragrupo_retorna_vazio():
    """FD também sai do pool (evita match falso com prestador PP)."""
    tx = Transacao(
        id="x",
        titular_pix="FD GESTAO INTELIGENTE",
        valor=-55473.33,
        data_movimento="2026-04-13",
        origem_banco="UNICRED",
    )
    linha = LinhaOrcamento(
        id="l1",
        titular_razao_social="ALGUM PRESTADOR CLT",
        valor_previsto=55473.33,
        saldo_pendente=55473.33,
    )
    assert sugerir_cascata(tx, [linha], []) == []
