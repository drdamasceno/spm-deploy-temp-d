from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from backend.api.deps import (
    get_current_user,
    get_supabase_anon,
    get_supabase_authed,
)
from backend.api.schemas.auth import (
    LoginRequest,
    LoginResponse,
    MeResponse,
    RefreshRequest,
    RefreshResponse,
    UserInfo,
)

router = APIRouter()


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    client = get_supabase_anon()
    try:
        resp = client.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "credenciais invalidas"},
        )

    session = getattr(resp, "session", None)
    user = getattr(resp, "user", None)
    if session is None or user is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "credenciais invalidas"},
        )

    return LoginResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        user=UserInfo(id=user.id, email=user.email),
    )


@router.post("/refresh", response_model=RefreshResponse)
def refresh(payload: RefreshRequest):
    client = get_supabase_anon()
    try:
        resp = client.auth.refresh_session(payload.refresh_token)
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "refresh token invalido"},
        )

    session = getattr(resp, "session", None)
    if session is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "refresh token invalido"},
        )

    return RefreshResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
    )


@router.get("/me", response_model=MeResponse)
def me(current=Depends(get_current_user)):
    client = get_supabase_authed(current["jwt"])
    try:
        result = (
            client.table("usuario")
            .select("id, email, nome, perfil")
            .eq("id", current["id"])
            .limit(1)
            .execute()
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "erro ao consultar usuario"},
        )

    rows = result.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "usuario nao encontrado"},
        )

    row = rows[0]
    return MeResponse(
        id=row["id"],
        email=row["email"],
        nome=row.get("nome"),
        role=row.get("perfil"),
    )
