"""Testes dos endpoints de dashboard que tocam registro_pp."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def _build_mock(rpps, txs=None, rodadas=None, orcs=None, concs=None):
    client = MagicMock()
    def side(nome):
        qb = MagicMock()
        for m in ("select", "eq", "lt", "in_", "limit", "order", "not_", "is_", "gte", "lte", "contains"):
            getattr(qb, m).return_value = qb
        if nome == "registro_pp":
            qb.execute.return_value = MagicMock(data=rpps)
        elif nome == "rodada":
            qb.execute.return_value = MagicMock(data=rodadas or [])
        elif nome == "transacao_bancaria":
            qb.execute.return_value = MagicMock(data=txs or [])
        elif nome == "orcamento_linha":
            qb.execute.return_value = MagicMock(data=orcs or [])
        elif nome == "conciliacao_orcamento":
            qb.execute.return_value = MagicMock(data=concs or [])
        else:
            qb.execute.return_value = MagicMock(data=[])
        return qb
    client.table.side_effect = side
    return client


def test_compromissos_filtra_pela_rodada_mais_recente():
    """soma_pp deve refletir apenas a rodada mais recente por chave."""
    from backend.api.routers.dashboard_compromissos_recebiveis import compromissos

    rpps = [
        {"id": "old", "contrato_id": "C1", "mes_competencia": "2026-02",
         "prestador_id": "P1", "rodada_id": "R_OLD", "saldo_pp": 1000.00,
         "status_saldo": "ELEGIVEL", "nome_prestador": "Dr Old"},
        {"id": "new", "contrato_id": "C1", "mes_competencia": "2026-02",
         "prestador_id": "P1", "rodada_id": "R_NEW", "saldo_pp": 500.00,
         "status_saldo": "ELEGIVEL", "nome_prestador": "Dr New"},
    ]
    rodadas = [
        {"id": "R_OLD", "criado_em": "2026-04-19T10:00:00+00:00"},
        {"id": "R_NEW", "criado_em": "2026-04-25T10:00:00+00:00"},
    ]
    mock_client = _build_mock(rpps, rodadas=rodadas)
    fake_user = {"jwt": "fake", "id": "u1"}
    with patch(
        "backend.api.routers.dashboard_compromissos_recebiveis.get_supabase_authed",
        return_value=mock_client,
    ):
        resp = compromissos(current=fake_user)

    # Esperado: soma so R_NEW = R$ 500. Sem fix viria 1500.
    assert resp.por_fonte["PP"] == 500.00


def test_historico_compromissos_abertos_filtra_pela_rodada_mais_recente():
    """compromissos_abertos da competencia 2026-02 nao deve somar registros
    de R_OLD com R_NEW da mesma chave."""
    from unittest.mock import patch as _patch
    import datetime
    from backend.api.routers.dashboard_historico import historico

    # rodadas que cobrem 2026-02
    rodadas_da_comp = [
        {"id": "R_OLD"},
        {"id": "R_NEW"},
    ]
    rpps = [
        {"id": "old", "contrato_id": "C1", "mes_competencia": "2026-02",
         "prestador_id": "P1", "rodada_id": "R_OLD", "saldo_pp": 1000.00,
         "status_saldo": "ELEGIVEL"},
        {"id": "new", "contrato_id": "C1", "mes_competencia": "2026-02",
         "prestador_id": "P1", "rodada_id": "R_NEW", "saldo_pp": 500.00,
         "status_saldo": "ELEGIVEL"},
    ]
    rodadas_meta = [
        {"id": "R_OLD", "criado_em": "2026-04-19T10:00:00+00:00"},
        {"id": "R_NEW", "criado_em": "2026-04-25T10:00:00+00:00"},
    ]

    # Mock que retorna rodadas_da_comp para rodada.contains, rodadas_meta para rodada.in_
    client = MagicMock()
    table_calls = {"rodada_count": 0}

    def side(nome):
        qb = MagicMock()
        for m in ("select", "eq", "lt", "in_", "limit", "order", "not_", "is_", "gte", "lte", "contains"):
            getattr(qb, m).return_value = qb
        if nome == "registro_pp":
            qb.execute.return_value = MagicMock(data=rpps)
        elif nome == "rodada":
            # Primeira chamada (contains) retorna rodadas da competencia
            # Segunda chamada (in_ created_at) retorna rodadas_meta
            table_calls["rodada_count"] += 1
            if table_calls["rodada_count"] == 1:
                qb.execute.return_value = MagicMock(data=rodadas_da_comp)
            else:
                qb.execute.return_value = MagicMock(data=rodadas_meta)
        elif nome == "transacao_bancaria":
            qb.execute.return_value = MagicMock(data=[])
        else:
            qb.execute.return_value = MagicMock(data=[])
        return qb

    client.table.side_effect = side

    fake_user = {"jwt": "fake", "id": "u1"}

    # Fixar data para que competencia_atual == "2026-02"
    fixed_date = datetime.date(2026, 2, 15)
    with _patch("backend.api.routers.dashboard_historico.date") as mock_date, \
         _patch(
             "backend.api.routers.dashboard_historico.get_supabase_authed",
             return_value=client,
         ):
        mock_date.today.return_value = fixed_date

        out = historico(meses=1, current=fake_user)

    mes_02 = next(m for m in out.meses if m.competencia == "2026-02")
    # Sem fix: 1500. Com fix: 500.
    assert mes_02.compromissos_abertos == 500.0
