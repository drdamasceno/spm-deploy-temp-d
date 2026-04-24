"""Teste da métrica de conciliação por rodada (fórmula corrigida)."""
from __future__ import annotations

from backend.src import conciliacao_spm


def test_percentual_nunca_excede_100():
    """
    Métrica % conciliado deve refletir 'quanto do PP foi casado a PIX'.
    Nunca pode ultrapassar 100% — seria sinal de que débitos não-PP
    (tarifas, CLTs, reembolsos) estão poluindo o numerador.

    Este teste replica a nova fórmula sobre o resultado direto do motor
    conciliar() — sem depender do DB. Valida que, com tarifas + PIX match,
    a proporção fica entre 0 e 100%.
    """
    pp = [
        {"nome_prestador": "DR ALPHA", "saldo": 1000.00,
         "razao_social_pj": "", "tipo_doc": "CPF",
         "contrato": "X", "mes_competencia": "2026-03"},
        {"nome_prestador": "DR BETA", "saldo": 500.00,
         "razao_social_pj": "", "tipo_doc": "CPF",
         "contrato": "X", "mes_competencia": "2026-03"},
    ]
    extrato = [
        {"fitid": "t01", "valor": -1000.00, "titular_pix": "DR ALPHA",
         "tipo": "PIX_SAIDA", "data": "2026-04-15", "memo": "a"},
        # Tarifas e outros débitos aparecem no extrato mas NÃO devem
        # afetar a métrica (não têm vínculo com PP).
        {"fitid": "t02", "valor": -1.60, "titular_pix": "",
         "tipo": "TARIFA_BANCARIA", "data": "2026-04-15", "memo": "TARIFA"},
        {"fitid": "t03", "valor": -2000.00, "titular_pix": "FORNECEDOR RANDOM",
         "tipo": "PIX_SAIDA", "data": "2026-04-15", "memo": "b"},
    ]
    resultado = conciliacao_spm.conciliar(pp, extrato, excecoes_pj={})

    valor_conciliado = sum(
        r["saldo_pp"] for r in resultado["registros"]
        if r["status"] in ("MATCH_AUTOMATICO", "FRACIONADO")
        or (r["status"] == "CONCILIADO_CATEGORIA" and r.get("categoria") == "EXCECAO_PJ_PRESTADOR")
    )
    valor_total = sum(r["saldo_pp"] for r in resultado["registros"] if r["saldo_pp"] > 0)
    pct = valor_conciliado / valor_total * 100.0 if valor_total > 0 else 0.0

    assert 0 <= pct <= 100.0, f"% = {pct} fora de [0, 100]"
    assert abs(pct - 66.666) < 0.1, f"Esperava ~66.67%, veio {pct}"
