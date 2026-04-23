"""Testes unitários do endpoint /dashboard/historico."""
from unittest.mock import MagicMock, patch

from backend.api.routers.dashboard_historico import (
    _competencia_anterior,
    historico,
)


def test_competencia_anterior_mes_comum():
    assert _competencia_anterior("2026-04") == "2026-03"


def test_competencia_anterior_vira_ano():
    assert _competencia_anterior("2026-01") == "2025-12"


def _make_client_vazio():
    """Cliente que retorna [] para todas as queries possíveis."""
    client = MagicMock()

    def table_side(nome):
        m = MagicMock()
        if nome == "saldo_caixa_diario":
            (
                m.select.return_value
                .gte.return_value
                .lte.return_value
                .order.return_value
                .limit.return_value
                .execute.return_value
            ).data = []
        elif nome == "transacao_bancaria":
            (
                m.select.return_value
                .eq.return_value
                .gte.return_value
                .lte.return_value
                .execute.return_value
            ).data = []
        elif nome == "rodada":
            (
                m.select.return_value
                .contains.return_value
                .execute.return_value
            ).data = []
        elif nome == "registro_pp":
            (
                m.select.return_value
                .eq.return_value
                .in_.return_value
                .execute.return_value
            ).data = []
        return m

    client.table.side_effect = table_side
    return client


def test_historico_vazio_retorna_n_meses():
    """Com DB vazio: retorna N meses zerados."""
    mocked_client = _make_client_vazio()
    with patch(
        "backend.api.routers.dashboard_historico.get_supabase_authed",
        return_value=mocked_client,
    ):
        resp = historico(meses=3, current={"jwt": "fake"})

    assert len(resp.meses) == 3
    for mes in resp.meses:
        assert mes.liquidez == 0.0
        assert mes.faturamento == 0.0
        assert mes.despesa_fixa == 0.0
        assert mes.despesa_variavel == 0.0
        assert mes.tributo == 0.0
        assert mes.compromissos_abertos == 0.0
        assert mes.recebiveis_atraso == 0.0


def test_historico_com_dados_tipicos():
    """Um mês com: liquidez 5000, faturamento 1000, despesas de 3 tipos."""
    client = MagicMock()

    # Por mês o router faz duas chamadas a transacao_bancaria:
    # 1ª = CREDITO (faturamento), 2ª = DEBITO (despesas).
    # Cada chamada vira um table_side com novo MagicMock.
    tx_call = {"n": 0}

    def table_side(nome):
        m = MagicMock()
        if nome == "saldo_caixa_diario":
            (
                m.select.return_value
                .gte.return_value
                .lte.return_value
                .order.return_value
                .limit.return_value
                .execute.return_value
            ).data = [{"data": "2026-04-29", "liquidez_total": "5000.00"}]
        elif nome == "transacao_bancaria":
            tx_call["n"] += 1
            if tx_call["n"] == 1:
                data = [{"valor": "1000.00"}]
            else:
                data = [
                    {"valor": "-300.00", "natureza_lancamento": "DESPESA_FIXA"},
                    {"valor": "-100.00", "natureza_lancamento": "VALOR_VARIAVEL"},
                    {"valor": "-50.00", "natureza_lancamento": "TRIBUTO"},
                ]
            (
                m.select.return_value
                .eq.return_value
                .gte.return_value
                .lte.return_value
                .execute.return_value
            ).data = data
        elif nome == "rodada":
            (
                m.select.return_value
                .contains.return_value
                .execute.return_value
            ).data = []
        elif nome == "registro_pp":
            (
                m.select.return_value
                .eq.return_value
                .in_.return_value
                .execute.return_value
            ).data = []
        return m

    client.table.side_effect = table_side

    with patch(
        "backend.api.routers.dashboard_historico.get_supabase_authed",
        return_value=client,
    ):
        resp = historico(meses=1, current={"jwt": "fake"})

    assert len(resp.meses) == 1
    mes = resp.meses[0]
    assert mes.liquidez == 5000.0
    assert mes.faturamento == 1000.0
    assert mes.despesa_fixa == 300.0
    assert mes.despesa_variavel == 100.0
    assert mes.tributo == 50.0
