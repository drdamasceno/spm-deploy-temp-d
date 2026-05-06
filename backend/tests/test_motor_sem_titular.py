"""Testes do motor de conciliação — proteção contra match-por-valor sem titular.

Caso real (Henrique Storino ↔ Eduarda Vitor, abril/2026): motor casava PIX por
valor exato quando não havia candidato por nome — atribuía pagamento de outro
prestador ao registro_pp atual, gerando falso positivo cross-prestador exibido
como "Pago" em /contratos com risco de pagamento duplicado.

Regra ancorada (CLAUDE.md): "Match válido EXIGE titular_pix == nome_prestador
ou razao_social_pj. NUNCA conciliar só por valor coincidente sem titularidade
confirmada."
"""
from __future__ import annotations

from backend.src.conciliacao_spm import conciliar


def _pix(fitid, valor, titular):
    return {
        'fitid': fitid,
        'valor': valor,  # negativo = saída
        'tipo': 'PIX_SAIDA',
        'titular_pix': titular,
        'trntype': 'DEBIT',
    }


def _pp(prestador, contrato, mes, saldo, doc='', tipo='PJ', razao=''):
    return {
        'nome_prestador': prestador,
        'contrato': contrato,
        'mes_competencia': mes,
        'saldo': saldo,
        'razao_social_pj': razao,
        'tipo_doc': tipo,
        'chave_pix': doc,
        'documento': doc,
    }


def test_pix_de_outro_prestador_com_valor_coincidente_nao_associa():
    """Caso Henrique Storino ↔ Eduarda Vitor.

    Henrique tem saldo PP 10980. PIX de R$ 10980 saiu pra Eduarda Vitor.
    Motor NÃO deve associar — sem titular batendo, registro fica
    NAO_CLASSIFICADO. Isso impede `registro_pp_id` de ser populado errado.
    """
    pp_data = [_pp('HENRIQUE STORINO NETO', 'SP-Sertaozinho', '2026-03', 10980.00)]
    extrato = [_pix('tx-eduarda', -10980.00, 'DRA EDUARDA VITOR MAR')]

    out = conciliar(pp_data, extrato)
    reg = out['registros'][0]

    assert reg['status'] == 'NAO_CLASSIFICADO', \
        f"esperado NAO_CLASSIFICADO, veio {reg['status']}"
    assert reg['pix_matched'] == [], \
        "PIX da Eduarda nao pode ser associado ao Henrique Storino"
    assert reg['valor_pix_total'] == 0.0


def test_pix_com_titular_correto_e_valor_exato_continua_match_automatico():
    """Sanity check: caso correto continua funcionando — não regredimos o
    fluxo MATCH_AUTOMATICO ao consertar o fluxo VALOR_SEM_TITULAR."""
    pp_data = [_pp('HENRIQUE STORINO NETO', 'SP-Sertaozinho', '2026-02', 9880.00,
                   razao='HENRIQUE STORINO CIRURGIA VASCULAR LTDA')]
    extrato = [_pix('tx-storino', -9880.00, 'HENRIQUE STORINO CIRU')]

    out = conciliar(pp_data, extrato)
    reg = out['registros'][0]

    assert reg['status'] == 'MATCH_AUTOMATICO'
    assert reg['valor_pix_total'] == 9880.00
    assert reg['divergencia'] == 0.0


def test_titular_diferente_e_valor_diferente_continua_nao_classificado():
    """Sanity: nem titular bate, nem valor bate → NAO_CLASSIFICADO (sem
    associação). Comportamento já existia, este teste guarda contra regressão."""
    pp_data = [_pp('JANE DOE', 'SP-X', '2026-03', 5000.00)]
    extrato = [_pix('tx-other', -3000.00, 'JOHN SMITH')]

    out = conciliar(pp_data, extrato)
    reg = out['registros'][0]

    assert reg['status'] == 'NAO_CLASSIFICADO'
    assert reg['pix_matched'] == []


def test_titular_bate_mas_valor_diverge_continua_manual_pendente():
    """Sanity: branch separada — quando há candidatos por nome MAS valor
    diverge do saldo, fica MANUAL_PENDENTE (caso legítimo de revisão humana,
    NÃO afetado pelo hotfix #1). Hotfix #2 (filtro de _pix_por_chave) garante
    que isso nao apareça como pago em /contratos."""
    pp_data = [_pp('CARLOS LIMA', 'SP-Y', '2026-03', 5000.00)]
    extrato = [_pix('tx-carlos', -3500.00, 'CARLOS LIMA')]

    out = conciliar(pp_data, extrato)
    reg = out['registros'][0]

    assert reg['status'] == 'MANUAL_PENDENTE'
    # PIX entra no pix_matched porque titular bate — operador decide manualmente
    assert len(reg['pix_matched']) == 1
