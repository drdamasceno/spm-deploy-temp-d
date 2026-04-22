from functools import lru_cache
from typing import Optional

import pyotp
from fastapi import Depends, Header, HTTPException, status
from pydantic_settings import BaseSettings, SettingsConfigDict
from supabase import Client, create_client


class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: Optional[str] = None
    feature_2fa: bool = False

    model_config = SettingsConfigDict(
        env_file="backend/.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_supabase_anon() -> Client:
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_anon_key)


def get_supabase_authed(jwt: str) -> Client:
    """
    Client Supabase autenticado com JWT do usuario — respeita RLS em todas
    as camadas (PostgREST, Storage, Functions). supabase-py v2.x mantem
    sub-clients separados para cada servico; precisa propagar o JWT para
    todos, nao apenas PostgREST.
    """
    s = get_settings()
    client = create_client(s.supabase_url, s.supabase_anon_key)
    client.postgrest.auth(jwt)
    # Storage usa SyncClient proprio com header Authorization que default para anon.
    # Sem este set, qualquer operacao em storage.objects com policy 'auth.uid() IS NOT NULL'
    # avalia como NULL e rejeita com "new row violates row-level security policy".
    client.storage._client.headers["Authorization"] = f"Bearer {jwt}"
    return client


def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "nao autenticado"},
        )
    jwt = authorization.split(" ", 1)[1].strip()
    if not jwt:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "nao autenticado"},
        )
    try:
        client = get_supabase_anon()
        resp = client.auth.get_user(jwt)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "nao autenticado"},
        )
    user = getattr(resp, "user", None)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "nao autenticado"},
        )
    return {"id": user.id, "email": user.email, "jwt": jwt}


def require_ceo(current: dict = Depends(get_current_user)) -> dict:
    """
    Exige que o usuario autenticado seja CEO. Delega ao banco via RPC fn_is_ceo()
    — mesma fonte de verdade que as policies RLS usam. Se a regra mudar no banco,
    o backend reflete sem redeploy.
    """
    client = get_supabase_authed(current["jwt"])
    try:
        resp = client.rpc("fn_is_ceo").execute()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "verificacao de perfil falhou"},
        )
    raw = resp.data
    if isinstance(raw, list):
        raw = raw[0] if raw else None
    if raw is not True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "operacao requer perfil CEO"},
        )
    return current


def require_ceo_with_2fa(
    current: dict = Depends(require_ceo),
    x_totp_code: Optional[str] = Header(default=None, alias="X-TOTP-Code"),
) -> dict:
    """
    Exige CEO + TOTP quando FEATURE_2FA=True. Flag off -> no-op (passthrough).

    Schema ja prevê 2FA: usuario.fa_habilitado + usuario.totp_secret.
    Quando a flag for ativada globalmente, cada CEO precisa ter fa_habilitado=true
    e totp_secret preenchido — senao bloqueia com 403.
    """
    s = get_settings()
    if not s.feature_2fa:
        return current

    client = get_supabase_authed(current["jwt"])
    try:
        resp = (
            client.table("usuario")
            .select("totp_secret, fa_habilitado")
            .eq("id", current["id"])
            .limit(1)
            .execute()
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "falha ao consultar configuracao 2FA"},
        )
    rows = resp.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "usuario nao encontrado"},
        )
    row = rows[0]
    if not row.get("fa_habilitado"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "2FA obrigatorio mas nao habilitado para este usuario"},
        )
    secret = row.get("totp_secret")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "2FA habilitado mas totp_secret ausente"},
        )
    if not x_totp_code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "codigo TOTP ausente (header X-TOTP-Code)"},
        )
    try:
        ok = pyotp.TOTP(secret).verify(x_totp_code, valid_window=1)
    except Exception:
        ok = False
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "codigo TOTP invalido"},
        )
    return current
