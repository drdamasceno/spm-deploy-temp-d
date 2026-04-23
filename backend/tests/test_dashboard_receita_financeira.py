"""Testes unitários do endpoint /dashboard/receita-financeira."""
from unittest.mock import MagicMock, patch

from backend.api.routers.dashboard_receita_financeira import receita_financeira


def _make_client(tx_mes, tx_ano, apls, snaps):
    """Monta client mock. Router faz 2 chamadas distintas a transacao_bancaria
    (mês e ano), então precisamos retornar um MagicMock diferente em cada chamada."""
    client = MagicMock()

    tx_call_count = {"n": 0}

    def table_side(nome):
        m = MagicMock()
        if nome == "transacao_bancaria":
            tx_call_count["n"] += 1
            data = tx_mes if tx_call_count["n"] == 1 else tx_ano
            (
                m.select.return_value
                .eq.return_value
                .eq.return_value
                .gte.return_value
                .lte.return_value
                .execute.return_value
            ).data = data
        elif nome == "aplicacao_financeira":
            m.select.return_value.eq.return_value.execute.return_value.data = apls
        elif nome == "saldo_caixa_diario":
            (
                m.select.return_value
                .gte.return_value
                .lte.return_value
                .execute.return_value
            ).data = snaps
        return m

    client.table.side_effect = table_side
    return client


def test_receita_financeira_vazio():
    """Sem transações nem aplicações: zero em tudo."""
    mocked_client = _make_client([], [], [], [])
    with patch(
        "backend.api.routers.dashboard_receita_financeira.get_supabase_authed",
        return_value=mocked_client,
    ), patch(
        "backend.api.routers.dashboard_receita_financeira.get_liquidez_total",
        return_value=0.0,
    ):
        resp = receita_financeira(competencia="2026-04", current={"jwt": "fake"})

    assert resp.rendimento_mes == 0.0
    assert resp.acumulado_ano == 0.0
    assert resp.rentabilidade_pct == 0.0
    assert resp.cdi_mes_pct == 0.83
    assert resp.percent_cdi == 0.0


def test_receita_financeira_com_dados_tipicos():
    """10 de rendimento mês, 50 ano, saldo médio 1000 -> rentabilidade 1%."""
    tx_mes = [{"valor": "10.00"}]
    tx_ano = [{"valor": "50.00"}]
    apls: list = []
    snaps = [{"liquidez_total": "1000.00"}]

    mocked_client = _make_client(tx_mes, tx_ano, apls, snaps)
    with patch(
        "backend.api.routers.dashboard_receita_financeira.get_supabase_authed",
        return_value=mocked_client,
    ):
        resp = receita_financeira(competencia="2026-04", current={"jwt": "fake"})

    assert resp.rendimento_mes == 10.0
    assert resp.acumulado_ano == 50.0
    assert resp.rentabilidade_pct == 1.0
    assert resp.cdi_mes_pct == 0.83
    # 1.0 / 0.83 * 100 ≈ 120.48
    assert 120.0 < resp.percent_cdi < 121.0
