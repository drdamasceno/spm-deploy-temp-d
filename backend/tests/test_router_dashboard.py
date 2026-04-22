"""Testes do router /dashboard — KPIs + previsto x realizado + alertas.

Focam em contrato (estrutura do response) + validação de querystring.
Testes de agregação ponta-a-ponta ficam em test_smoke_e2e.py.
"""
import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    reason="SERVICE_ROLE_KEY ausente",
)


def test_dashboard_competencia_atual_responde(client, ceo_headers):
    """Dashboard de competência sem dados deve responder com estrutura válida."""
    r = client.get("/dashboard?competencia=2099-12&empresa=SPM", headers=ceo_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["competencia"] == "2099-12"
    assert data["empresa_filtro"] == "SPM"
    assert "kpis" in data
    assert "previsto_x_realizado" in data
    assert isinstance(data["alertas"], list)
    # Sem orçamento, previsto_a_pagar deve ser 0
    assert data["kpis"]["previsto_a_pagar"] == 0.0


def test_dashboard_competencia_invalida(client, ceo_headers):
    """Competência fora do formato YYYY-MM deve cair na validação Pydantic."""
    r = client.get("/dashboard?competencia=invalido&empresa=SPM", headers=ceo_headers)
    assert r.status_code == 422  # Pydantic validation


def test_dashboard_empresa_todas(client, ceo_headers):
    """Filtro TODAS deve responder agregando SPM + FD."""
    r = client.get("/dashboard?competencia=2099-12&empresa=TODAS", headers=ceo_headers)
    assert r.status_code == 200
    assert r.json()["empresa_filtro"] == "TODAS"
