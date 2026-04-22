"""
Fixtures compartilhadas para a suite Bloco D (excecao_pj + rodada_snapshot).

Convencoes:
  - Credenciais de teste em .env via TEST_CEO_EMAIL/PASSWORD + TEST_USER_EMAIL/PASSWORD.
  - service_role key em SUPABASE_SERVICE_ROLE_KEY (bypassa RLS), usada pelas
    fixtures para criar/deletar prestador e rodada.
  - T7 usa pg8000 direto contra SUPABASE_DB_URL (teste DB-level: trigger
    bloqueando UPDATE em rodada aprovada, independente do caminho REST).
  - Cleanup e best-effort; rodadas aprovadas podem deixar lixo residual
    porque o trigger trg_bloqueia_delete_rodada_aprovada nao cede nem a
    service_role. Quando isso acontecer, teardown imprime warning e segue.
"""
from __future__ import annotations

import os
import uuid
from typing import Optional

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from supabase import Client, create_client

load_dotenv("backend/.env")
load_dotenv()  # fallback se rodar de dentro de backend/


def _env(name: str) -> Optional[str]:
    v = os.environ.get(name)
    return v.strip() if v else None


SUPABASE_URL = _env("SUPABASE_URL")
SUPABASE_ANON_KEY = _env("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = _env("SUPABASE_SERVICE_ROLE_KEY")
TEST_CEO_EMAIL = _env("TEST_CEO_EMAIL")
TEST_CEO_PASSWORD = _env("TEST_CEO_PASSWORD")
TEST_USER_EMAIL = _env("TEST_USER_EMAIL")
TEST_USER_PASSWORD = _env("TEST_USER_PASSWORD")


def _require(*names: str) -> None:
    missing = [n for n in names if not _env(n)]
    if missing:
        pytest.skip(f"variaveis de ambiente faltando: {', '.join(missing)}")


# ---------------------------------------------------------------------------
# App / HTTP client
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client() -> TestClient:
    from backend.api.main import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# Supabase clients
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def service_role_client() -> Client:
    _require("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def _sign_in(email: str, password: str) -> dict:
    _require("SUPABASE_URL", "SUPABASE_ANON_KEY")
    anon = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
    resp = anon.auth.sign_in_with_password({"email": email, "password": password})
    session = getattr(resp, "session", None)
    user = getattr(resp, "user", None)
    if session is None or user is None:
        pytest.skip(f"falha ao autenticar {email}: verifique credenciais")
    return {"token": session.access_token, "id": user.id, "email": user.email}


@pytest.fixture(scope="session")
def ceo_session() -> dict:
    _require("TEST_CEO_EMAIL", "TEST_CEO_PASSWORD")
    return _sign_in(TEST_CEO_EMAIL, TEST_CEO_PASSWORD)


@pytest.fixture(scope="session")
def usuario_normal_session() -> dict:
    _require("TEST_USER_EMAIL", "TEST_USER_PASSWORD")
    return _sign_in(TEST_USER_EMAIL, TEST_USER_PASSWORD)


@pytest.fixture(scope="session")
def ceo_token(ceo_session) -> str:
    return ceo_session["token"]


@pytest.fixture(scope="session")
def usuario_normal_token(usuario_normal_session) -> str:
    return usuario_normal_session["token"]


@pytest.fixture(scope="session")
def ceo_id(ceo_session) -> str:
    return ceo_session["id"]


@pytest.fixture(scope="session")
def usuario_normal_id(usuario_normal_session) -> str:
    return usuario_normal_session["id"]


@pytest.fixture
def ceo_headers(ceo_token) -> dict:
    return {"Authorization": f"Bearer {ceo_token}"}


@pytest.fixture
def usuario_normal_headers(usuario_normal_token) -> dict:
    return {"Authorization": f"Bearer {usuario_normal_token}"}


# ---------------------------------------------------------------------------
# Fixtures de dados
# ---------------------------------------------------------------------------

@pytest.fixture
def prestador_valido(service_role_client) -> str:
    """
    Cria um prestador de teste e devolve o id. Deleta no teardown.
    Usa sufixo UUID no nome para evitar colisao entre runs concorrentes.
    """
    tag = uuid.uuid4().hex[:8]
    payload = {
        "nome": f"PRESTADOR_TESTE_BLOCO_D_{tag}",
        "ficticio": True,
        "tipo_doc": "CPF",
        "cpf_cnpj": f"TEST:{tag}",
        "cpf_cnpj_validado": False,
    }
    created = service_role_client.table("prestador").insert(payload).execute()
    prestador_id = created.data[0]["id"]
    yield prestador_id
    try:
        # limpa excecoes pendentes antes (FK)
        service_role_client.table("excecao_pj").delete().eq("prestador_id", prestador_id).execute()
        service_role_client.table("prestador").delete().eq("id", prestador_id).execute()
    except Exception as e:
        print(f"[teardown] prestador {prestador_id}: {e}")


@pytest.fixture
def rodada_nao_aprovada(service_role_client, ceo_id) -> str:
    """
    Cria uma rodada fresh (sem transacoes nem registros_pp). Tentativa de
    teardown e best-effort: se a rodada foi aprovada durante o teste, o
    trigger trg_bloqueia_delete_rodada_aprovada bloqueia DELETE e o registro
    fica. Nesse caso loga warning.
    """
    payload = {
        "periodo_extrato_inicio": "2026-01-01",
        "periodo_extrato_fim": "2026-01-31",
        "pp_competencias": ["2026-01"],
        "status": "CRIADA",
        "criado_por": ceo_id,
    }
    created = service_role_client.table("rodada").insert(payload).execute()
    rodada_id = created.data[0]["id"]
    yield rodada_id
    # teardown
    try:
        service_role_client.table("rodada_snapshot").delete().eq("rodada_id", rodada_id).execute()
    except Exception as e:
        print(f"[teardown] snapshot da rodada {rodada_id}: {e}")
    try:
        service_role_client.table("rodada").delete().eq("id", rodada_id).execute()
    except Exception as e:
        # provavelmente trigger de rodada aprovada bloqueou
        print(f"[teardown] rodada {rodada_id} (possivel lixo residual): {e}")
