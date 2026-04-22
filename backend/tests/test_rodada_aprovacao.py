"""
Testes Bloco D — aprovacao de rodada + rodada_snapshot.

Cobertura:
  T6  CEO aprova rodada           -> 201 + snapshot + rodada.aprovada_em + log INSERT
  T7  UPDATE rodada aprovada      -> trigger bloqueia (service_role nao bypassa trigger)
  T8  autenticado le snapshot     -> 200
  T9  UPDATE snapshot via JWT     -> RLS nega (payload nao muda)
  T10 reaprovar rodada ja aprovada-> 1a 201, 2a 409 (UNIQUE ux_rodada_snapshot_rodada)
  T11 hash SHA256 reproduzivel    -> recalculo bate
"""
from __future__ import annotations

import hashlib
import json


# ---------------------------------------------------------------------------
# T6 — CEO aprova rodada
# ---------------------------------------------------------------------------

def test_ceo_aprova_rodada_201(
    client, ceo_headers, rodada_nao_aprovada, service_role_client
):
    rid = rodada_nao_aprovada
    resp = client.post(f"/rodadas/{rid}/aprovar", headers=ceo_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    snapshot_id = body["id"]
    assert body["rodada_id"] == rid
    assert body["hash_payload"]

    # rodada.aprovada_em preenchido
    r = (
        service_role_client.table("rodada")
        .select("aprovada_em, snapshot_id, aprovada_por")
        .eq("id", rid)
        .limit(1)
        .execute()
    )
    row = (r.data or [{}])[0]
    assert row.get("aprovada_em") is not None
    assert row.get("snapshot_id") == snapshot_id

    # log_auditoria do snapshot
    log = (
        service_role_client.table("log_auditoria")
        .select("acao")
        .eq("tabela", "rodada_snapshot")
        .eq("registro_id", snapshot_id)
        .eq("acao", "INSERT")
        .execute()
    )
    assert log.data, "entrada INSERT em log_auditoria (rodada_snapshot) nao encontrada"


# ---------------------------------------------------------------------------
# T7 — UPDATE rodada aprovada via pg8000 (SQL direto) bloqueado pelo trigger
# ---------------------------------------------------------------------------

def test_update_rodada_aprovada_bloqueado(
    client, ceo_headers, rodada_nao_aprovada
):
    """
    Simula bypass da API: conecta direto no Postgres como superuser e tenta
    UPDATE na rodada aprovada. O trigger trg_bloqueia_update_rodada_aprovada
    deve levantar excecao do banco independente do caminho (REST ou SQL direto).
    """
    import os
    from urllib.parse import urlparse

    import pytest
    import pg8000.dbapi

    db_url = os.environ.get("SUPABASE_DB_URL", "").strip()
    if not db_url or "<SENHA>" in db_url:
        pytest.skip("SUPABASE_DB_URL ausente ou nao preenchido no .env")

    rid = rodada_nao_aprovada
    r_apv = client.post(f"/rodadas/{rid}/aprovar", headers=ceo_headers)
    assert r_apv.status_code == 201

    parsed = urlparse(db_url)
    conn = pg8000.dbapi.connect(
        user=parsed.username,
        password=parsed.password,
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=(parsed.path or "/postgres").lstrip("/") or "postgres",
        ssl_context=True,  # Supabase exige TLS
    )
    msg = ""
    try:
        cur = conn.cursor()
        try:
            cur.execute("UPDATE rodada SET status='CANCELADA' WHERE id = %s", (rid,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            msg = str(e).lower()
        finally:
            cur.close()
    finally:
        conn.close()

    assert (
        "ja foi aprovada" in msg
        or "imutavel" in msg
        or "bloqueada" in msg
        or "operacao bloqueada" in msg
    ), f"UPDATE nao foi bloqueado ou mensagem inesperada: {msg!r}"


# ---------------------------------------------------------------------------
# T8 — autenticado le snapshot
# ---------------------------------------------------------------------------

def test_autenticado_le_snapshot_200(
    client, ceo_headers, usuario_normal_headers, rodada_nao_aprovada
):
    rid = rodada_nao_aprovada
    assert client.post(f"/rodadas/{rid}/aprovar", headers=ceo_headers).status_code == 201

    resp = client.get(f"/rodadas/{rid}/snapshot", headers=usuario_normal_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["rodada_id"] == rid
    assert "payload" in body
    assert "transacoes" in body["payload"]
    assert "registros_pp" in body["payload"]
    assert "excecoes_ativas" in body["payload"]


# ---------------------------------------------------------------------------
# T9 — UPDATE em rodada_snapshot via JWT normal e negado por RLS
# ---------------------------------------------------------------------------

def test_update_snapshot_bloqueado(
    client, ceo_headers, usuario_normal_token, rodada_nao_aprovada, service_role_client
):
    import os
    from supabase import create_client

    rid = rodada_nao_aprovada
    r_apv = client.post(f"/rodadas/{rid}/aprovar", headers=ceo_headers)
    assert r_apv.status_code == 201
    snapshot_id = r_apv.json()["id"]
    hash_original = r_apv.json()["hash_payload"]

    # Client JWT-authed como usuario normal
    authed = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])
    authed.postgrest.auth(usuario_normal_token)

    # Sem policy UPDATE: PostgREST retorna 0 linhas afetadas (nao levanta
    # exception). Validamos que o hash nao mudou.
    try:
        authed.table("rodada_snapshot").update({"hash_payload": "ADULTERADO"}).eq("id", snapshot_id).execute()
    except Exception:
        pass

    # Re-le via service_role e confere hash intacto
    r = (
        service_role_client.table("rodada_snapshot")
        .select("hash_payload")
        .eq("id", snapshot_id)
        .limit(1)
        .execute()
    )
    assert r.data and r.data[0]["hash_payload"] == hash_original, (
        "UPDATE via JWT normal conseguiu alterar o snapshot — RLS falhou"
    )


# ---------------------------------------------------------------------------
# T10 — reaprovar rodada ja aprovada
# ---------------------------------------------------------------------------

def test_reaprovar_rodada_ja_aprovada_409(
    client, ceo_headers, rodada_nao_aprovada
):
    rid = rodada_nao_aprovada
    r1 = client.post(f"/rodadas/{rid}/aprovar", headers=ceo_headers)
    assert r1.status_code == 201

    r2 = client.post(f"/rodadas/{rid}/aprovar", headers=ceo_headers)
    assert r2.status_code == 409, r2.text
    assert "error" in r2.json()


# ---------------------------------------------------------------------------
# T11 — hash SHA256 reproduzivel
# ---------------------------------------------------------------------------

def test_hash_reproduzivel(
    client, ceo_headers, rodada_nao_aprovada, service_role_client
):
    rid = rodada_nao_aprovada
    r_apv = client.post(f"/rodadas/{rid}/aprovar", headers=ceo_headers)
    assert r_apv.status_code == 201
    snapshot_id = r_apv.json()["id"]
    hash_armazenado = r_apv.json()["hash_payload"]

    # le payload do DB
    row = (
        service_role_client.table("rodada_snapshot")
        .select("payload")
        .eq("id", snapshot_id)
        .limit(1)
        .execute()
    )
    payload = row.data[0]["payload"]

    payload_json = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
    hash_recalc = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

    assert hash_recalc == hash_armazenado, (
        f"hash divergente: armazenado={hash_armazenado} recalc={hash_recalc}"
    )
