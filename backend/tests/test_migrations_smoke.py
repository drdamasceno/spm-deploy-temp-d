# backend/tests/test_migrations_smoke.py
"""
Smoke test: criar registros nas tabelas novas (0007-0009) e ler de volta.
Roda contra o Supabase real usando supabase-py com service role.
Ignora RLS para simplicidade (teste é de schema, não de permissão).
"""
import os
import pytest
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://mkxehqhikcuykaxnpxff.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

pytestmark = pytest.mark.skipif(
    not SUPABASE_SERVICE_KEY,
    reason="SUPABASE_SERVICE_ROLE_KEY não definido",
)


@pytest.fixture
def client():
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def test_seeds_empresa_existem(client):
    r = client.table("empresa").select("codigo").execute()
    codigos = {row["codigo"] for row in r.data}
    assert "SPM" in codigos
    assert "FD" in codigos


def test_seeds_categoria_ao_menos_40(client):
    r = client.table("categoria_despesa").select("id").execute()
    assert len(r.data) >= 40


def test_criar_projeto_e_ler(client):
    # SPM id
    e = client.table("empresa").select("id").eq("codigo", "SPM").single().execute()
    empresa_id = e.data["id"]
    # Cria projeto
    p = client.table("projeto").insert({
        "codigo": "TEST-SMOKE-PROJECT",
        "descricao": "Projeto de smoke test",
        "empresa_id": empresa_id,
    }).execute()
    assert p.data and p.data[0]["codigo"] == "TEST-SMOKE-PROJECT"
    # Limpa
    client.table("projeto").delete().eq("codigo", "TEST-SMOKE-PROJECT").execute()


def test_orcamento_e_linha_integridade(client):
    e = client.table("empresa").select("id").eq("codigo", "SPM").single().execute()
    empresa_id = e.data["id"]
    o = client.table("orcamento").insert({
        "empresa_id": empresa_id,
        "competencia": "2099-12",
        "status": "RASCUNHO",
    }).execute()
    orcamento_id = o.data[0]["id"]
    linha = client.table("orcamento_linha").insert({
        "orcamento_id": orcamento_id,
        "natureza": "DESPESA_FIXA",
        "titular_razao_social": "SMOKE TEST TITULAR",
        "valor_previsto": 123.45,
    }).execute()
    assert linha.data
    # Limpeza cascata via delete do orcamento
    client.table("orcamento").delete().eq("id", orcamento_id).execute()


def test_regra_classificacao_unique_ativa(client):
    # Inserir uma regra ativa
    r1 = client.table("regra_classificacao").insert({
        "titular_pix_padrao": "SMOKE TEST TITULAR UNIQUE",
        "confianca_base": 0.9,
        "ativa": True,
    }).execute()
    assert r1.data
    regra_id = r1.data[0]["id"]
    # Inserir segunda regra ativa com o mesmo titular — deve falhar
    with pytest.raises(Exception):
        client.table("regra_classificacao").insert({
            "titular_pix_padrao": "SMOKE TEST TITULAR UNIQUE",
            "confianca_base": 0.8,
            "ativa": True,
        }).execute()
    client.table("regra_classificacao").delete().eq("id", regra_id).execute()
