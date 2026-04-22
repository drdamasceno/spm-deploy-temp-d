"""Testes de integração dos endpoints de catálogo (empresa/projeto/categoria)."""
import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    reason="SERVICE_ROLE_KEY não disponível",
)


def test_listar_empresas(client, ceo_headers):
    r = client.get("/empresas", headers=ceo_headers)
    assert r.status_code == 200
    data = r.json()
    codigos = {e["codigo"] for e in data}
    assert {"SPM", "FD"}.issubset(codigos)


def test_listar_categorias_nao_vazio(client, ceo_headers):
    r = client.get("/categorias", headers=ceo_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 40


def test_criar_projeto_e_listar(client, ceo_headers):
    # Pega empresa SPM
    r = client.get("/empresas", headers=ceo_headers)
    spm = next(e for e in r.json() if e["codigo"] == "SPM")
    # Cria projeto
    payload = {"codigo": "TEST-R37-PROJ", "descricao": "Teste router catálogos", "empresa_id": spm["id"]}
    r = client.post("/projetos", headers=ceo_headers, json=payload)
    assert r.status_code == 201
    proj = r.json()
    assert proj["codigo"] == "TEST-R37-PROJ"
    # Lista projetos
    r = client.get("/projetos", headers=ceo_headers)
    assert any(p["codigo"] == "TEST-R37-PROJ" for p in r.json())
    # Cleanup
    client.delete(f"/projetos/{proj['id']}", headers=ceo_headers)
