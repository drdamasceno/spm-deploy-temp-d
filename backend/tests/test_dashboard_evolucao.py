"""Testes unitários do endpoint /dashboard/evolucao-caixa.

Chama a função do router diretamente com um client Supabase mockado,
evitando o overhead de montar TestClient + auth. Segue o padrão de
test_dashboard_fixes.py.
"""
from datetime import date
from unittest.mock import MagicMock, patch

from backend.api.routers.dashboard_evolucao import evolucao_caixa


def _make_client(snaps):
    """Monta client mock para saldo_caixa_diario retornar `snaps`."""
    client = MagicMock()
    tb = MagicMock()
    (
        tb.select.return_value
        .gte.return_value
        .lte.return_value
        .order.return_value
        .execute.return_value
    ).data = snaps
    client.table.return_value = tb
    return client


def test_evolucao_caixa_com_snapshots():
    """Quando há snapshots diários, usa abertura + último dia + sparkline."""
    snaps = [
        {"data": "2026-04-01", "liquidez_total": "100.00"},
        {"data": "2026-04-02", "liquidez_total": "110.00"},
        {"data": "2026-04-03", "liquidez_total": "120.00"},
    ]
    mocked_client = _make_client(snaps)

    with patch("backend.api.routers.dashboard_evolucao.get_supabase_authed", return_value=mocked_client):
        resp = evolucao_caixa(competencia="2026-04", current={"jwt": "fake"})

    assert resp.abertura_data == "2026-04-01"
    assert resp.abertura_valor == 100.0
    assert resp.hoje_data == "2026-04-03"
    assert resp.hoje_valor == 120.0
    assert resp.variacao_valor == 20.0
    assert resp.variacao_pct == 20.0
    assert resp.sparkline == [100.0, 110.0, 120.0]


def test_evolucao_caixa_fallback_sem_snapshots():
    """Sem saldo_caixa_diario, usa liquidez_total atual como fallback."""
    mocked_client = _make_client([])

    with patch("backend.api.routers.dashboard_evolucao.get_supabase_authed", return_value=mocked_client), \
         patch("backend.api.routers.dashboard_evolucao.get_liquidez_total", return_value=1500.0):
        resp = evolucao_caixa(competencia="2026-04", current={"jwt": "fake"})

    assert resp.abertura_valor == 1500.0
    assert resp.hoje_valor == 1500.0
    assert resp.variacao_valor == 0.0
    assert resp.sparkline == [1500.0]


def test_evolucao_caixa_competencia_passada_usa_fim_do_mes():
    """Competência < hoje: d_hoje é o último dia do mês, não hoje."""
    mocked_client = _make_client([])

    with patch("backend.api.routers.dashboard_evolucao.get_supabase_authed", return_value=mocked_client), \
         patch("backend.api.routers.dashboard_evolucao.get_liquidez_total", return_value=0.0):
        resp = evolucao_caixa(competencia="2020-02", current={"jwt": "fake"})

    # Fevereiro 2020 terminou dia 29 (bissexto)
    assert resp.hoje_data == "2020-02-29"
    assert resp.abertura_data == "2020-02-01"
