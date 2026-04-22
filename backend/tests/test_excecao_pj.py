"""
Testes Bloco D — CRUD de excecao_pj.

Cobertura:
  T1  nao-CEO tenta POST           -> 403
  T2  CEO POST valido              -> 201 + registro no DB + log_auditoria INSERT
  T3  CEO POST CNPJ invalido       -> 422 (validator Pydantic)
  T4  CEO POST duplicata ativa     -> 1a 201, 2a 409 (UNIQUE parcial)
  T5  soft-delete + recria         -> 2 linhas no DB, 1 ativa, 1 inativa
  T12 anonimo sem JWT              -> 401
"""
from __future__ import annotations

import uuid


def _payload_valido(prestador_id: str, cnpj: str = "12345678000195") -> dict:
    return {
        "prestador_id": prestador_id,
        "razao_social_autorizada": "CLINICA DR FABIO TESTE",
        "cnpj": cnpj,
        "data_aprovacao": "2026-04-20",
        "justificativa": "Teste automatizado Bloco D",
    }


# ---------------------------------------------------------------------------
# T1 — nao-CEO faz POST
# ---------------------------------------------------------------------------

def test_nao_ceo_post_403(client, usuario_normal_headers, prestador_valido):
    resp = client.post(
        "/excecoes_pj",
        headers=usuario_normal_headers,
        json=_payload_valido(prestador_valido),
    )
    assert resp.status_code == 403
    assert "error" in resp.json()


# ---------------------------------------------------------------------------
# T2 — CEO POST valido
# ---------------------------------------------------------------------------

def test_ceo_post_valido_201(
    client, ceo_headers, ceo_id, prestador_valido, service_role_client
):
    resp = client.post(
        "/excecoes_pj",
        headers=ceo_headers,
        json=_payload_valido(prestador_valido),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    excecao_id = body["id"]

    # registro no DB
    db_row = (
        service_role_client.table("excecao_pj")
        .select("*")
        .eq("id", excecao_id)
        .limit(1)
        .execute()
    )
    assert db_row.data, "registro nao encontrado no DB"
    row = db_row.data[0]
    assert row["prestador_id"] == prestador_valido
    assert row["cnpj"] == "12345678000195"
    assert row["ativo"] is True
    assert row["aprovado_por"] == ceo_id

    # log_auditoria com acao=INSERT
    log = (
        service_role_client.table("log_auditoria")
        .select("acao")
        .eq("tabela", "excecao_pj")
        .eq("registro_id", excecao_id)
        .eq("acao", "INSERT")
        .execute()
    )
    assert log.data, "entrada INSERT em log_auditoria nao encontrada"

    # cleanup
    service_role_client.table("excecao_pj").delete().eq("id", excecao_id).execute()


# ---------------------------------------------------------------------------
# T3 — CEO POST CNPJ invalido
# ---------------------------------------------------------------------------

def test_ceo_post_cnpj_invalido_422(client, ceo_headers, prestador_valido):
    payload = _payload_valido(prestador_valido, cnpj="abc123")
    resp = client.post("/excecoes_pj", headers=ceo_headers, json=payload)
    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# T4 — CEO POST duplicata ativa
# ---------------------------------------------------------------------------

def test_ceo_post_duplicata_ativa_409(
    client, ceo_headers, prestador_valido, service_role_client
):
    cnpj = "98765432000100"
    payload = _payload_valido(prestador_valido, cnpj=cnpj)

    r1 = client.post("/excecoes_pj", headers=ceo_headers, json=payload)
    assert r1.status_code == 201, r1.text
    id1 = r1.json()["id"]

    r2 = client.post("/excecoes_pj", headers=ceo_headers, json=payload)
    assert r2.status_code == 409, r2.text

    # cleanup
    service_role_client.table("excecao_pj").delete().eq("id", id1).execute()


# ---------------------------------------------------------------------------
# T5 — soft-delete + recria
# ---------------------------------------------------------------------------

def test_ceo_soft_delete_depois_recria_ok(
    client, ceo_headers, prestador_valido, service_role_client
):
    cnpj = "11222333000144"
    payload = _payload_valido(prestador_valido, cnpj=cnpj)

    r1 = client.post("/excecoes_pj", headers=ceo_headers, json=payload)
    assert r1.status_code == 201, r1.text
    id1 = r1.json()["id"]

    rdel = client.delete(f"/excecoes_pj/{id1}", headers=ceo_headers)
    assert rdel.status_code == 200, rdel.text
    assert rdel.json()["ativo"] is False

    r2 = client.post("/excecoes_pj", headers=ceo_headers, json=payload)
    assert r2.status_code == 201, r2.text
    id2 = r2.json()["id"]
    assert id2 != id1

    # 2 linhas: 1 ativa, 1 inativa, mesmo (prestador_id, cnpj)
    rows = (
        service_role_client.table("excecao_pj")
        .select("id, ativo")
        .eq("prestador_id", prestador_valido)
        .eq("cnpj", cnpj)
        .execute()
    )
    estados = sorted(r["ativo"] for r in rows.data or [])
    assert estados == [False, True], f"estados inesperados: {estados}"

    # cleanup
    service_role_client.table("excecao_pj").delete().eq("id", id1).execute()
    service_role_client.table("excecao_pj").delete().eq("id", id2).execute()


# ---------------------------------------------------------------------------
# T12 — anonimo
# ---------------------------------------------------------------------------

def test_usuario_anonimo_401(client, prestador_valido):
    fake_id = str(uuid.uuid4())

    r_list = client.get("/excecoes_pj")
    assert r_list.status_code == 401

    r_get = client.get(f"/excecoes_pj/{fake_id}")
    assert r_get.status_code == 401

    r_post = client.post("/excecoes_pj", json=_payload_valido(prestador_valido))
    assert r_post.status_code == 401

    r_patch = client.patch(f"/excecoes_pj/{fake_id}", json={"ativo": False})
    assert r_patch.status_code == 401

    r_delete = client.delete(f"/excecoes_pj/{fake_id}")
    assert r_delete.status_code == 401
