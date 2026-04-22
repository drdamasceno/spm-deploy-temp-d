from typing import List, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from supabase import Client

from backend.api.deps import get_current_user, get_supabase_authed
from backend.api.schemas.catalogos import EmpresaOut, CategoriaOut, ProjetoIn, ProjetoOut


class ContaBancariaCreate(BaseModel):
    banco: str
    agencia: str
    conta: str
    finalidade: Literal["RECEBIMENTOS", "REMESSAS", "AVISTA", "FIXAS", "TRIBUTOS"]


router = APIRouter()


@router.get("/empresas", response_model=List[EmpresaOut])
def listar_empresas(current=Depends(get_current_user)):
    client: Client = get_supabase_authed(current["jwt"])
    r = client.table("empresa").select("*").eq("ativa", True).order("codigo").execute()
    return r.data


@router.get("/categorias", response_model=List[CategoriaOut])
def listar_categorias(current=Depends(get_current_user)):
    client: Client = get_supabase_authed(current["jwt"])
    r = client.table("categoria_despesa").select("*").order("nome").execute()
    return r.data


@router.get("/projetos", response_model=List[ProjetoOut])
def listar_projetos(current=Depends(get_current_user)):
    client: Client = get_supabase_authed(current["jwt"])
    r = client.table("projeto").select("*").eq("ativo", True).order("codigo").execute()
    return r.data


@router.post("/projetos", response_model=ProjetoOut, status_code=status.HTTP_201_CREATED)
def criar_projeto(payload: ProjetoIn, current=Depends(get_current_user)):
    client: Client = get_supabase_authed(current["jwt"])
    r = client.table("projeto").insert(payload.model_dump(mode="json")).execute()
    if not r.data:
        raise HTTPException(status_code=400, detail={"error": "Falha ao criar projeto"})
    return r.data[0]


@router.delete("/projetos/{projeto_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_projeto(projeto_id: UUID, current=Depends(get_current_user)):
    client: Client = get_supabase_authed(current["jwt"])
    client.table("projeto").delete().eq("id", str(projeto_id)).execute()
    return None


@router.get("/contas_bancarias", response_model=List[dict])
def listar_contas_bancarias(
    finalidade: str | None = None,
    current=Depends(get_current_user),
):
    client: Client = get_supabase_authed(current["jwt"])
    q = (
        client.table("conta_bancaria")
        .select("id,banco,agencia,conta,finalidade,ativo")
        .eq("ativo", True)
        .order("banco")
    )
    if finalidade:
        q = q.eq("finalidade", finalidade)
    return q.execute().data


@router.post("/contas_bancarias", response_model=dict, status_code=status.HTTP_201_CREATED)
def criar_conta_bancaria(payload: ContaBancariaCreate, current=Depends(get_current_user)):
    client: Client = get_supabase_authed(current["jwt"])
    try:
        r = (
            client.table("conta_bancaria")
            .insert(
                {
                    "banco": payload.banco.strip().upper(),
                    "agencia": payload.agencia.strip(),
                    "conta": payload.conta.strip(),
                    "finalidade": payload.finalidade.upper(),
                    "ativo": True,
                }
            )
            .execute()
        )
    except Exception as e:
        msg = str(e).lower()
        if "unique" in msg or "duplicate" in msg or "23505" in msg:
            raise HTTPException(
                status_code=409,
                detail={"error": "Conta bancaria ja cadastrada (banco+agencia+conta)"},
            )
        raise
    if not r.data:
        raise HTTPException(status_code=400, detail={"error": "Falha ao criar conta bancaria"})
    return r.data[0]


@router.delete("/contas_bancarias/{conta_id}", status_code=status.HTTP_204_NO_CONTENT)
def desativar_conta_bancaria(conta_id: UUID, current=Depends(get_current_user)):
    """Soft delete: seta ativo=false."""
    client: Client = get_supabase_authed(current["jwt"])
    r = (
        client.table("conta_bancaria")
        .update({"ativo": False})
        .eq("id", str(conta_id))
        .execute()
    )
    if not r.data:
        raise HTTPException(status_code=404, detail={"error": "Conta bancaria nao encontrada"})
    return None
