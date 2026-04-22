"""Testes dos endpoints de contratos. Integração real fica skipped (requer JWT + banco)."""
import pytest
from fastapi.testclient import TestClient
from backend.api.main import app

client = TestClient(app)


@pytest.mark.skip(reason="integração real — requer JWT + banco")
def test_listar_contratos_agrupa_por_cidade():
    resp = client.get("/contratos?competencia=2026-02", headers={"Authorization": "Bearer TEST"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 15
    ufs = {row["uf"] for row in data}
    assert "MG" in ufs and "SP" in ufs and "PR" in ufs


@pytest.mark.skip(reason="integração real")
def test_listar_anteriores():
    resp = client.get("/contratos/anteriores?ate=2026-04", headers={"Authorization": "Bearer TEST"})
    assert resp.status_code == 200


def test_openapi_rotas_registradas():
    """Sanity check: as 4 rotas de contratos estão no OpenAPI schema."""
    schema = app.openapi()
    paths = schema["paths"]
    assert "/contratos" in paths
    assert "/contratos/anteriores" in paths
    assert "/contratos/{contrato_id}" in paths
    assert "/contratos/{contrato_id}/competencia/{competencia}" in paths
    # Método certo em cada
    assert "get" in paths["/contratos"]
    assert "get" in paths["/contratos/anteriores"]
    assert "patch" in paths["/contratos/{contrato_id}"]
    assert "get" in paths["/contratos/{contrato_id}/competencia/{competencia}"]
