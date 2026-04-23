"""Testes unitários do endpoint /dashboard/recebiveis.

É um placeholder seguro (aguarda Plano 04+). Devolve vazio; o teste só
valida o contrato.
"""
from backend.api.routers.dashboard_compromissos_recebiveis import recebiveis


def test_recebiveis_retorna_placeholder_vazio():
    resp = recebiveis(current={"jwt": "fake"})
    assert resp.total == 0.0
    assert resp.por_aging == {}
    assert resp.itens == []


def test_recebiveis_estrutura_resposta():
    """Garante que a resposta tem os campos esperados pelo RecebiveisResponse."""
    resp = recebiveis(current={"jwt": "fake"})
    # Acesso aos campos não deve explodir
    assert hasattr(resp, "total")
    assert hasattr(resp, "por_aging")
    assert hasattr(resp, "itens")
    assert isinstance(resp.itens, list)
