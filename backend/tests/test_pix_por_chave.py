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
        for m in ("select", "eq", "lt", "in_", "limit", "order", "not_", "is_", "gte", "lte"):
            getattr(qb, m).return_value = qb
        if nome == "registro_pp":
            qb.execute.return_value = MagicMock(data=rpps_data)
        elif nome == "transacao_bancaria":
            qb.execute.return_value = MagicMock(data=txs_data)
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
        {"registro_pp_id": "rpp1", "valor": -1000.00, "data_extrato": "2026-04-15"},
        {"registro_pp_id": "rpp1", "valor": -500.00, "data_extrato": "2026-04-20"},
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
        {"registro_pp_id": "rpp_a", "valor": -700.00, "data_extrato": "2026-04-10"},
        {"registro_pp_id": "rpp_b", "valor": -300.00, "data_extrato": "2026-06-12"},
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
        {"registro_pp_id": "r1", "valor": -100.00, "data_extrato": "2026-04-01"},
        {"registro_pp_id": "r2", "valor": -200.00, "data_extrato": "2026-05-10"},
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
        {"registro_pp_id": "rA", "valor": -100.0, "data_extrato": "2026-04-01"},
        {"registro_pp_id": "rB", "valor": -999.0, "data_extrato": "2026-04-02"},
    ]
    client = _build_client(rpps, txs)
    out = _pix_por_chave(client, chaves)
    assert out[("C1", "2026-02", "P1")]["pago"] == 100.0
    assert out[("C1", "2026-03", "P1")]["pago"] == 999.0
    # Buckets nao se misturam — sem o guard, ambos teriam 1099.0
