from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.deps import get_current_user, get_supabase_authed
from backend.api.schemas.regra import RegraClassificacaoOut, RegraClassificacaoPatch


router = APIRouter(prefix="/regras", tags=["regra_classificacao"])


@router.get("", response_model=List[RegraClassificacaoOut])
def listar(
    ativa: bool | None = None,
    current=Depends(get_current_user),
):
    """Lista regras de classificação. Filtro opcional por `ativa`."""
    client = get_supabase_authed(current["jwt"])
    q = client.table("regra_classificacao").select("*").order("criada_em", desc=True)
    if ativa is not None:
        q = q.eq("ativa", ativa)
    return q.execute().data


@router.patch("/{regra_id}", response_model=RegraClassificacaoOut)
def editar(
    regra_id: UUID,
    payload: RegraClassificacaoPatch,
    current=Depends(get_current_user),
):
    """Edita campos mutáveis de uma regra (ativa, confianca_base). Outros campos são imutáveis."""
    updates = payload.model_dump(exclude_unset=True, mode="json")
    if not updates:
        raise HTTPException(400, detail={"error": "Nada a atualizar"})
    client = get_supabase_authed(current["jwt"])
    r = client.table("regra_classificacao").update(updates).eq("id", str(regra_id)).execute()
    if not r.data:
        raise HTTPException(404, detail={"error": "Regra não encontrada"})
    return r.data[0]


@router.delete("/{regra_id}", status_code=status.HTTP_204_NO_CONTENT)
def desativar(regra_id: UUID, current=Depends(get_current_user)):
    """
    Soft delete: seta `ativa=false`. Não remove do DB para preservar histórico.
    Use DELETE hard via DB direto apenas se CEO (policy RLS).
    """
    client = get_supabase_authed(current["jwt"])
    r = client.table("regra_classificacao").update({"ativa": False}).eq("id", str(regra_id)).execute()
    if not r.data:
        raise HTTPException(404, detail={"error": "Regra não encontrada"})
    return None
