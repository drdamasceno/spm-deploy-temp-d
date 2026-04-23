"""Verifica que migration 0015 deixou empresa e prestador no estado esperado."""
import os

import pytest
from supabase import create_client


@pytest.fixture(scope="module")
def client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        pytest.skip("SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY não configurados")
    return create_client(url, key)


def test_empresa_tem_regime_e_papel(client):
    rows = client.table("empresa").select("codigo,regime_tributario,papel,cnpj").execute().data
    codigos = {r["codigo"]: r for r in rows}
    assert "SPM" in codigos
    assert codigos["SPM"]["papel"] == "PRINCIPAL"
    assert codigos["SPM"]["regime_tributario"] == "LUCRO_REAL"
    assert "FD" in codigos
    assert codigos["FD"]["papel"] == "INTRAGRUPO"
    assert codigos["FD"]["regime_tributario"] == "SIMPLES_NACIONAL"
    assert codigos["FD"]["cnpj"] == "49.542.886/0001-94"


def test_prestador_tem_pj_empregadora_id(client):
    prest = client.table("prestador").select("id,pj_empregadora_id").limit(1).execute().data
    if not prest:
        pytest.skip("base sem prestadores — teste precisa de pelo menos 1")
    assert "pj_empregadora_id" in prest[0]
