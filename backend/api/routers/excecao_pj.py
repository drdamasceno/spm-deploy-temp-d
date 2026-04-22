from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.api.deps import (
    get_current_user,
    get_supabase_authed,
    require_ceo_with_2fa,
)
from backend.api.schemas.excecao_pj import (
    ExcecaoPJCreate,
    ExcecaoPJResponse,
    ExcecaoPJUpdate,
)


router = APIRouter()


def _is_duplicate_ativa(err_msg: str) -> bool:
    msg = (err_msg or "").lower()
    return (
        "ux_excecao_pj_prestador_cnpj_ativo" in msg
        or "duplicate key" in msg
        or "23505" in msg
    )


def _load_excecao(client, excecao_id: str) -> dict:
    resp = (
        client.table("excecao_pj")
        .select("*")
        .eq("id", excecao_id)
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "excecao nao encontrada"},
        )
    return rows[0]


@router.get("", response_model=List[ExcecaoPJResponse])
def listar_excecoes(
    ativo: Optional[bool] = Query(default=None),
    prestador_id: Optional[UUID] = Query(default=None),
    current=Depends(get_current_user),
):
    """
    GET /excecoes_pj?ativo=true&prestador_id=<uuid>

    Lista excecoes PJ. Sem filtros retorna tudo. RLS exige autenticado.
    """
    client = get_supabase_authed(current["jwt"])
    q = client.table("excecao_pj").select("*")
    if ativo is not None:
        q = q.eq("ativo", ativo)
    if prestador_id is not None:
        q = q.eq("prestador_id", str(prestador_id))
    resp = q.order("created_at", desc=True).execute()
    return [ExcecaoPJResponse(**row) for row in (resp.data or [])]


@router.get("/{excecao_id}", response_model=ExcecaoPJResponse)
def detalhe_excecao(
    excecao_id: UUID,
    current=Depends(get_current_user),
):
    client = get_supabase_authed(current["jwt"])
    row = _load_excecao(client, str(excecao_id))
    return ExcecaoPJResponse(**row)


@router.post("", response_model=ExcecaoPJResponse, status_code=status.HTTP_201_CREATED)
def criar_excecao(
    payload: ExcecaoPJCreate,
    current=Depends(require_ceo_with_2fa),
):
    """
    POST /excecoes_pj

    Requer CEO (+ TOTP se FEATURE_2FA=true). aprovado_por e preenchido a partir
    do JWT — o body nao aceita este campo. Duplicata ativa (mesmo prestador+cnpj)
    falha com 409 via UNIQUE parcial ux_excecao_pj_prestador_cnpj_ativo.
    """
    client = get_supabase_authed(current["jwt"])
    insert_payload = {
        "prestador_id": str(payload.prestador_id),
        "razao_social_autorizada": payload.razao_social_autorizada,
        "cnpj": payload.cnpj,
        "data_aprovacao": payload.data_aprovacao.isoformat(),
        "justificativa": payload.justificativa,
        "aprovado_por": current["id"],
    }
    try:
        created = client.table("excecao_pj").insert(insert_payload).execute()
    except Exception as e:
        if _is_duplicate_ativa(str(e)):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "excecao ativa ja existe para este prestador e CNPJ"},
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"falha ao criar excecao: {e}"},
        )
    rows = created.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "insert retornou vazio"},
        )
    return ExcecaoPJResponse(**rows[0])


@router.patch("/{excecao_id}", response_model=ExcecaoPJResponse)
def atualizar_excecao(
    excecao_id: UUID,
    payload: ExcecaoPJUpdate,
    current=Depends(require_ceo_with_2fa),
):
    """
    PATCH /excecoes_pj/{id}

    Requer CEO (+ TOTP). prestador_id e aprovado_por sao imutaveis. ativo
    pode ser alternado para reativar soft-deleted; reativacao que cria
    duplicata ativa falha com 409.
    """
    client = get_supabase_authed(current["jwt"])
    _load_excecao(client, str(excecao_id))  # 404 se nao existe

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "nenhum campo para atualizar"},
        )
    if "data_aprovacao" in updates and updates["data_aprovacao"] is not None:
        updates["data_aprovacao"] = updates["data_aprovacao"].isoformat()

    try:
        updated = (
            client.table("excecao_pj")
            .update(updates)
            .eq("id", str(excecao_id))
            .execute()
        )
    except Exception as e:
        if _is_duplicate_ativa(str(e)):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "reativacao criaria duplicata ativa"},
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"falha ao atualizar excecao: {e}"},
        )
    rows = updated.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "update retornou vazio"},
        )
    return ExcecaoPJResponse(**rows[0])


@router.delete("/{excecao_id}", response_model=ExcecaoPJResponse)
def remover_excecao(
    excecao_id: UUID,
    current=Depends(require_ceo_with_2fa),
):
    """
    DELETE /excecoes_pj/{id}

    Soft-delete: UPDATE ativo=false. Preserva historico. Libera o par
    (prestador_id, cnpj) para nova excecao ativa. Requer CEO (+ TOTP).
    """
    client = get_supabase_authed(current["jwt"])
    existing = _load_excecao(client, str(excecao_id))
    if not existing.get("ativo"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "excecao ja inativa"},
        )
    updated = (
        client.table("excecao_pj")
        .update({"ativo": False})
        .eq("id", str(excecao_id))
        .execute()
    )
    rows = updated.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "soft-delete retornou vazio"},
        )
    return ExcecaoPJResponse(**rows[0])
