"""Testa fixes de bugs do Dashboard (Track B)."""
from unittest.mock import MagicMock
from backend.api.routers.saldos import get_liquidez_total


def test_get_liquidez_total_soma_cc_e_aplicacoes():
    """2 contas (snapshots 100 e 50) + 1 aplicação ativa (1000) = 1150."""
    client = MagicMock()

    saldos_por_conta = {"c1": "100", "c2": "50"}

    def table_side(nome):
        m = MagicMock()
        if nome == "conta_bancaria":
            m.select.return_value.execute.return_value.data = [{"id": "c1"}, {"id": "c2"}]
        elif nome == "saldo_conta_snapshot":
            # O chamador faz: .select(...).eq("conta_bancaria_id", cid).order(...).order(...).limit(1).execute()
            # Capturamos cid no .eq() e devolvemos o snapshot correspondente.
            def eq_side(coluna, cid):
                sub = MagicMock()
                sub.order.return_value.order.return_value.limit.return_value.execute.return_value.data = [
                    {"saldo_valor": saldos_por_conta[cid]}
                ]
                return sub
            m.select.return_value.eq.side_effect = eq_side
        elif nome == "aplicacao_financeira":
            m.select.return_value.eq.return_value.execute.return_value.data = [
                {"valor_atual": "1000.00"}
            ]
        return m

    client.table.side_effect = table_side
    total = get_liquidez_total(client)
    assert abs(total - 1150.0) < 0.01


def test_schema_kpis_tem_entradas_do_mes():
    from backend.api.schemas.dashboard import KPIs
    fields = KPIs.model_fields
    assert "entradas_do_mes" in fields
    assert "saldo_inicial" not in fields
