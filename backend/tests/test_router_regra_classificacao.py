import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    reason="SERVICE_ROLE_KEY ausente",
)


def test_listar_regras_retorna_lista(client, ceo_headers):
    r = client.get("/regras", headers=ceo_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_editar_regra_ativa_false(client, ceo_headers, service_role_client, request):
    # Cria regra via service_role
    inserida = service_role_client.table("regra_classificacao").insert({
        "titular_pix_padrao": "TEST REGRA PATCH",
        "confianca_base": 0.90,
        "ativa": True,
    }).execute().data[0]
    regra_id = inserida["id"]
    request.addfinalizer(lambda: service_role_client.table("regra_classificacao").delete().eq("id", regra_id).execute())

    # Edita via API
    r = client.patch(f"/regras/{regra_id}", headers=ceo_headers, json={"ativa": False})
    assert r.status_code == 200, r.text
    assert r.json()["ativa"] is False


def test_desativar_regra_soft_delete(client, ceo_headers, service_role_client, request):
    inserida = service_role_client.table("regra_classificacao").insert({
        "titular_pix_padrao": "TEST REGRA SOFT DELETE",
        "confianca_base": 0.85,
        "ativa": True,
    }).execute().data[0]
    regra_id = inserida["id"]
    request.addfinalizer(lambda: service_role_client.table("regra_classificacao").delete().eq("id", regra_id).execute())

    r = client.delete(f"/regras/{regra_id}", headers=ceo_headers)
    assert r.status_code == 204

    # Confirma soft delete (ainda existe mas ativa=false)
    check = service_role_client.table("regra_classificacao").select("ativa").eq("id", regra_id).single().execute()
    assert check.data["ativa"] is False
