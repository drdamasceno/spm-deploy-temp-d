"""Testes unitários do endpoint /dashboard/compromissos."""
from unittest.mock import MagicMock, patch

from backend.api.routers.dashboard_compromissos_recebiveis import compromissos


def _make_client(pp_rows, linhas, concs):
    """Monta client mock com registro_pp, orcamento_linha, conciliacao_orcamento."""
    client = MagicMock()

    def table_side(nome):
        m = MagicMock()
        if nome == "registro_pp":
            m.select.return_value.eq.return_value.execute.return_value.data = pp_rows
        elif nome == "orcamento_linha":
            (
                m.select.return_value
                .not_.is_.return_value
                .lte.return_value
                .execute.return_value
            ).data = linhas
        elif nome == "conciliacao_orcamento":
            m.select.return_value.in_.return_value.execute.return_value.data = concs
        return m

    client.table.side_effect = table_side
    return client


def test_compromissos_vazio():
    """Sem PP nem faturas: total=0, listas vazias."""
    mocked_client = _make_client([], [], [])
    with patch(
        "backend.api.routers.dashboard_compromissos_recebiveis.get_supabase_authed",
        return_value=mocked_client,
    ):
        resp = compromissos(current={"jwt": "fake"})
    assert resp.total == 0.0
    assert resp.por_fonte == {"PP": 0.0, "FATURAS": 0.0}
    assert resp.itens == []


def test_compromissos_com_pp_e_fatura():
    """PP (200) + fatura (pendente 500): total = 700, ordenado por valor desc."""
    pp_rows = [
        {"nome_prestador": "DR FULANO", "saldo_pp": "200.00"},
    ]
    linhas = [
        {
            "id": "L1",
            "titular_razao_social": "FORNECEDOR X",
            "valor_previsto": "500.00",
            "data_previsao": "2026-05-01",
        },
    ]
    concs: list = []  # ainda não pago

    mocked_client = _make_client(pp_rows, linhas, concs)
    with patch(
        "backend.api.routers.dashboard_compromissos_recebiveis.get_supabase_authed",
        return_value=mocked_client,
    ):
        resp = compromissos(current={"jwt": "fake"})

    assert resp.total == 700.0
    assert resp.por_fonte["PP"] == 200.0
    assert resp.por_fonte["FATURAS"] == 500.0
    assert len(resp.itens) == 2
    # Ordenado por valor desc: fatura (500) antes de PP (200)
    assert resp.itens[0].fonte == "FATURA"
    assert resp.itens[0].valor == 500.0
    assert resp.itens[1].fonte == "PP"


def test_compromissos_fatura_parcialmente_paga():
    """Fatura de 500, paga 200: saldo 300 aparece como compromisso."""
    linhas = [
        {
            "id": "L1",
            "titular_razao_social": "X",
            "valor_previsto": "500.00",
            "data_previsao": "2026-05-01",
        },
    ]
    concs = [{"orcamento_linha_id": "L1", "valor_aplicado": "200.00"}]

    mocked_client = _make_client([], linhas, concs)
    with patch(
        "backend.api.routers.dashboard_compromissos_recebiveis.get_supabase_authed",
        return_value=mocked_client,
    ):
        resp = compromissos(current={"jwt": "fake"})

    assert resp.total == 300.0
    assert resp.itens[0].valor == 300.0
