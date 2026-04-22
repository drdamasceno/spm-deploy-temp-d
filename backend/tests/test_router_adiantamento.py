import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    reason="SERVICE_ROLE_KEY ausente",
)


def _tag() -> str:
    return uuid.uuid4().hex[:8]


def test_listar_adiantamentos(client, ceo_headers):
    r = client.get("/adiantamentos", headers=ceo_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_compensar_adiantamento_fluxo_feliz(client, ceo_headers, service_role_client, request):
    # Setup: cria prestador + registro_pp + adiantamento todos vinculados.
    tag = _tag()
    prestador = service_role_client.table("prestador").insert({
        "nome": f"TEST_ADIANT_PRESTADOR_{tag}",
        "ficticio": True,
        "tipo_doc": "CPF",
        "cpf_cnpj": f"TEST:{tag}",
    }).execute().data[0]
    prestador_id = prestador["id"]

    # Pega um contrato qualquer pra criar registro_pp
    contrato = service_role_client.table("contrato").select("id").limit(1).execute().data[0]
    contrato_id = contrato["id"]

    rpp = service_role_client.table("registro_pp").insert({
        "prestador_id": prestador_id,
        "contrato_id": contrato_id,
        "mes_competencia": "2099-01",
        "saldo_pp": 10600.00,
        "status_saldo": "ELEGIVEL",
    }).execute().data[0]
    rpp_id = rpp["id"]

    # Pega Hugo CEO para ser autorizado_por
    ceo = service_role_client.table("usuario").select("id").eq("perfil", "CEO").limit(1).execute().data[0]
    ceo_id = ceo["id"]

    adi = service_role_client.table("adiantamento").insert({
        "prestador_id": prestador_id,
        "valor_bruto_solicitado": 10000.00,
        "percentual_desconto": 6.00,
        "valor_liquido_pago": 9400.00,
        "autorizado_por": ceo_id,
        "data_pagamento": "2099-01-05",
        "status": "ABERTO",
    }).execute().data[0]
    adi_id = adi["id"]

    def _cleanup():
        service_role_client.table("adiantamento").delete().eq("id", adi_id).execute()
        service_role_client.table("registro_pp").delete().eq("id", rpp_id).execute()
        service_role_client.table("prestador").delete().eq("id", prestador_id).execute()
    request.addfinalizer(_cleanup)

    # Chama endpoint de compensar
    r = client.post(f"/adiantamentos/{adi_id}/compensar", headers=ceo_headers, json={"registro_pp_id": rpp_id})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "COMPENSADO_TOTAL"
    assert data["compensado_em_registro_pp_id"] == rpp_id


def test_compensar_prestador_divergente_rejeita(client, ceo_headers, service_role_client, request):
    """registro_pp de outro prestador -> 400."""
    # Setup: 2 prestadores, 1 adiantamento do prestador A, 1 registro_pp do prestador B
    tag_a = _tag()
    tag_b = _tag()
    p_a = service_role_client.table("prestador").insert({
        "nome": f"TEST_A_{tag_a}",
        "ficticio": True,
        "tipo_doc": "CPF",
        "cpf_cnpj": f"TEST:{tag_a}",
    }).execute().data[0]
    p_b = service_role_client.table("prestador").insert({
        "nome": f"TEST_B_{tag_b}",
        "ficticio": True,
        "tipo_doc": "CPF",
        "cpf_cnpj": f"TEST:{tag_b}",
    }).execute().data[0]
    contrato_id = service_role_client.table("contrato").select("id").limit(1).execute().data[0]["id"]
    ceo_id = service_role_client.table("usuario").select("id").eq("perfil", "CEO").limit(1).execute().data[0]["id"]

    rpp_b = service_role_client.table("registro_pp").insert({
        "prestador_id": p_b["id"], "contrato_id": contrato_id,
        "mes_competencia": "2099-02", "saldo_pp": 5000, "status_saldo": "ELEGIVEL",
    }).execute().data[0]

    adi_a = service_role_client.table("adiantamento").insert({
        "prestador_id": p_a["id"], "valor_bruto_solicitado": 3000,
        "percentual_desconto": 5, "valor_liquido_pago": 2850,
        "autorizado_por": ceo_id, "data_pagamento": "2099-02-05", "status": "ABERTO",
    }).execute().data[0]

    def _cleanup():
        service_role_client.table("adiantamento").delete().eq("id", adi_a["id"]).execute()
        service_role_client.table("registro_pp").delete().eq("id", rpp_b["id"]).execute()
        service_role_client.table("prestador").delete().in_("id", [p_a["id"], p_b["id"]]).execute()
    request.addfinalizer(_cleanup)

    r = client.post(f"/adiantamentos/{adi_a['id']}/compensar", headers=ceo_headers, json={"registro_pp_id": rpp_b["id"]})
    assert r.status_code == 400
