"""Testes unit do helper _pix_por_chave (mock do supabase client).

Garante que PIX classificados a registros_pp de QUALQUER rodada que
compartilhem (contrato, comp, prestador) são agregados sob a mesma chave.
"""
from __future__ import annotations

from unittest.mock import MagicMock

from backend.api.routers.contratos_competencia import _pix_por_chave


def _build_client(rpps_data, txs_data):
    """Mock client. Tabela registro_pp retorna rpps_data; transacao_bancaria
    retorna txs_data."""
    client = MagicMock()

    def table_side_effect(nome):
        qb = MagicMock()
        in_filters: list[tuple[str, list]] = []
        for m in ("select", "eq", "lt", "limit", "order", "not_", "is_", "gte", "lte"):
            getattr(qb, m).return_value = qb

        def in_side_effect(col, vals):
            in_filters.append((col, list(vals)))
            return qb
        qb.in_.side_effect = in_side_effect

        def exec_filtered(rows):
            for col, vals in in_filters:
                rows = [r for r in rows if r.get(col) in vals]
            return MagicMock(data=rows)

        if nome == "registro_pp":
            qb.execute.side_effect = lambda: exec_filtered(rpps_data)
        elif nome == "transacao_bancaria":
            qb.execute.side_effect = lambda: exec_filtered(txs_data)
        else:
            qb.execute.return_value = MagicMock(data=[])
        return qb
    client.table.side_effect = table_side_effect
    return client


def test_chaves_vazias_retorna_dict_vazio():
    client = MagicMock()
    out = _pix_por_chave(client, set())
    assert out == {}


def test_pix_de_uma_rodada_so_agrega_corretamente():
    """Chave (C1, 2026-02, P1) tem 1 registro em R1, 2 PIX classificados."""
    chaves = {("C1", "2026-02", "P1")}
    rpps = [
        {"id": "rpp1", "contrato_id": "C1", "mes_competencia": "2026-02",
         "prestador_id": "P1"},
    ]
    txs = [
        {"registro_pp_id": "rpp1", "valor": -1000.00, "data_extrato": "2026-04-15", "status_conciliacao": "MATCH_AUTOMATICO"},
        {"registro_pp_id": "rpp1", "valor": -500.00, "data_extrato": "2026-04-20", "status_conciliacao": "MATCH_AUTOMATICO"},
    ]
    client = _build_client(rpps, txs)
    out = _pix_por_chave(client, chaves)
    assert out[("C1", "2026-02", "P1")]["pago"] == 1500.00
    assert out[("C1", "2026-02", "P1")]["data_max"] == "2026-04-20"


def test_pix_de_rodadas_distintas_da_mesma_chave_sao_somados():
    """Caso operacional: (C1, 2026-02, P1) tem registros em R1 (rpp_a) e R2 (rpp_b).
    PIX classificados em rpp_a (rodada antiga) e rpp_b (rodada nova) somam juntos."""
    chaves = {("C1", "2026-02", "P1")}
    rpps = [
        {"id": "rpp_a", "contrato_id": "C1", "mes_competencia": "2026-02",
         "prestador_id": "P1"},
        {"id": "rpp_b", "contrato_id": "C1", "mes_competencia": "2026-02",
         "prestador_id": "P1"},
    ]
    txs = [
        {"registro_pp_id": "rpp_a", "valor": -700.00, "data_extrato": "2026-04-10", "status_conciliacao": "MATCH_AUTOMATICO"},
        {"registro_pp_id": "rpp_b", "valor": -300.00, "data_extrato": "2026-06-12", "status_conciliacao": "MATCH_AUTOMATICO"},
    ]
    client = _build_client(rpps, txs)
    out = _pix_por_chave(client, chaves)
    assert out[("C1", "2026-02", "P1")]["pago"] == 1000.00
    assert out[("C1", "2026-02", "P1")]["data_max"] == "2026-06-12"


def test_chave_sem_pix_retorna_zero_e_none():
    chaves = {("C1", "2026-02", "P1")}
    rpps = [
        {"id": "rpp1", "contrato_id": "C1", "mes_competencia": "2026-02",
         "prestador_id": "P1"},
    ]
    txs = []
    client = _build_client(rpps, txs)
    out = _pix_por_chave(client, chaves)
    assert out[("C1", "2026-02", "P1")]["pago"] == 0.0
    assert out[("C1", "2026-02", "P1")]["data_max"] is None


def test_chaves_multiplas_isoladas():
    chaves = {("C1", "2026-02", "P1"), ("C2", "2026-03", "P2")}
    rpps = [
        {"id": "r1", "contrato_id": "C1", "mes_competencia": "2026-02", "prestador_id": "P1"},
        {"id": "r2", "contrato_id": "C2", "mes_competencia": "2026-03", "prestador_id": "P2"},
    ]
    txs = [
        {"registro_pp_id": "r1", "valor": -100.00, "data_extrato": "2026-04-01", "status_conciliacao": "MATCH_AUTOMATICO"},
        {"registro_pp_id": "r2", "valor": -200.00, "data_extrato": "2026-05-10", "status_conciliacao": "MATCH_AUTOMATICO"},
    ]
    client = _build_client(rpps, txs)
    out = _pix_por_chave(client, chaves)
    assert out[("C1", "2026-02", "P1")] == {"pago": 100.00, "data_max": "2026-04-01"}
    assert out[("C2", "2026-03", "P2")] == {"pago": 200.00, "data_max": "2026-05-10"}


def test_rpp_fantasma_nao_contamina_chave_errada():
    """Cartesian guard: C1 esta em 2 chaves (compete diferente). DB pode retornar
    rpps de ambas comp via .in_() em todas as 3 dimensoes; o guard if chave in chaves
    deve impedir que PIX de uma comp vaze para a outra."""
    chaves = {("C1", "2026-02", "P1"), ("C1", "2026-03", "P1")}
    rpps = [
        {"id": "rA", "contrato_id": "C1", "mes_competencia": "2026-02", "prestador_id": "P1"},
        {"id": "rB", "contrato_id": "C1", "mes_competencia": "2026-03", "prestador_id": "P1"},
    ]
    txs = [
        {"registro_pp_id": "rA", "valor": -100.0, "data_extrato": "2026-04-01", "status_conciliacao": "MATCH_AUTOMATICO"},
        {"registro_pp_id": "rB", "valor": -999.0, "data_extrato": "2026-04-02", "status_conciliacao": "MATCH_AUTOMATICO"},
    ]
    client = _build_client(rpps, txs)
    out = _pix_por_chave(client, chaves)
    assert out[("C1", "2026-02", "P1")]["pago"] == 100.0
    assert out[("C1", "2026-03", "P1")]["pago"] == 999.0
    # Buckets nao se misturam — sem o guard, ambos teriam 1099.0


def test_filtra_manual_pendente_e_nao_classificado():
    """MANUAL_PENDENTE e NAO_CLASSIFICADO NÃO contam como pago em /contratos.

    Regra critica do dominio: PIX cuja titularidade nao foi confirmada
    (caso real Henrique Storino ↔ Eduarda Vitor — match-por-valor sem
    titular criou registro_pp_id apontando pra prestador alheio) não pode
    aparecer como pago na tela. Risco de pagamento duplicado pela Thais.
    """
    chaves = {("C1", "2026-02", "P1")}
    rpps = [
        {"id": "rpp1", "contrato_id": "C1", "mes_competencia": "2026-02",
         "prestador_id": "P1"},
    ]
    txs = [
        # Match real do motor — conta como pago
        {"registro_pp_id": "rpp1", "valor": -1000.00, "data_extrato": "2026-04-01",
         "status_conciliacao": "MATCH_AUTOMATICO"},
        # Match fracionado real — conta como pago
        {"registro_pp_id": "rpp1", "valor": -500.00, "data_extrato": "2026-04-02",
         "status_conciliacao": "FRACIONADO"},
        # Match por categoria (ex: EXCECAO_PJ_PRESTADOR) — conta como pago
        {"registro_pp_id": "rpp1", "valor": -200.00, "data_extrato": "2026-04-03",
         "status_conciliacao": "CONCILIADO_POR_CATEGORIA"},
        # Match suspeito — NAO conta. Caso Henrique Storino: PIX da Eduarda
        # com valor coincidente, sem titular batendo. registro_pp_id setado
        # mas titularidade nao foi confirmada.
        {"registro_pp_id": "rpp1", "valor": -10980.00, "data_extrato": "2026-04-27",
         "status_conciliacao": "MANUAL_PENDENTE"},
        # Não classificado — NAO conta
        {"registro_pp_id": "rpp1", "valor": -777.00, "data_extrato": "2026-04-28",
         "status_conciliacao": "NAO_CLASSIFICADO"},
    ]
    client = _build_client(rpps, txs)
    out = _pix_por_chave(client, chaves)
    # Apenas MATCH_AUTOMATICO + FRACIONADO + CONCILIADO_POR_CATEGORIA somam: 1700
    assert out[("C1", "2026-02", "P1")]["pago"] == 1700.00
    # data_max é a data do CONCILIADO_POR_CATEGORIA (2026-04-03), não a do
    # MANUAL_PENDENTE 2026-04-27 (excluído). Sem o filtro, viria 04-28.
    assert out[("C1", "2026-02", "P1")]["data_max"] == "2026-04-03"
