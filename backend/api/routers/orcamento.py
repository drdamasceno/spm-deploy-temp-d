from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from backend.api.deps import get_current_user, get_supabase_authed
from backend.api.schemas.orcamento import (
    OrcamentoCreate, OrcamentoOut, OrcamentoLinhaOut, ResultadoUploadOrcamento,
)
from backend.src.persistencia_parsers import persistir_orcamento_xlsx


class OrcamentoLinhaPatch(BaseModel):
    """Campos mutaveis de uma linha de orcamento (PATCH parcial)."""
    titular_razao_social: Optional[str] = None
    titular_cpf_cnpj: Optional[str] = None
    categoria_id: Optional[str] = None  # UUID string ou None para limpar
    projeto_id: Optional[str] = None
    valor_previsto: Optional[float] = None
    data_previsao: Optional[str] = None  # YYYY-MM-DD ou None
    observacao: Optional[str] = None


router = APIRouter(prefix="/orcamentos", tags=["orcamento"])


@router.get("", response_model=List[OrcamentoOut])
def listar(empresa_id: UUID | None = None, competencia: str | None = None, current=Depends(get_current_user)):
    client = get_supabase_authed(current["jwt"])
    q = client.table("orcamento").select("*")
    if empresa_id:
        q = q.eq("empresa_id", str(empresa_id))
    if competencia:
        q = q.eq("competencia", competencia)
    return q.order("competencia", desc=True).execute().data


@router.get("/{orcamento_id}/linhas", response_model=List[OrcamentoLinhaOut])
def listar_linhas(orcamento_id: UUID, natureza: str | None = None, current=Depends(get_current_user)):
    """Lista linhas do orçamento. Filtro opcional por natureza."""
    client = get_supabase_authed(current["jwt"])
    q = client.table("orcamento_linha").select("*").eq("orcamento_id", str(orcamento_id)).order("natureza,titular_razao_social")
    if natureza:
        q = q.eq("natureza", natureza)
    return q.execute().data


@router.post("", response_model=OrcamentoOut, status_code=status.HTTP_201_CREATED)
def criar(payload: OrcamentoCreate, current=Depends(get_current_user)):
    client = get_supabase_authed(current["jwt"])
    try:
        r = client.table("orcamento").insert({
            **payload.model_dump(mode="json"),
            "status": "RASCUNHO",
            "criado_por": current["id"],
        }).execute()
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(409, detail={"error": "Orcamento ja existe para essa (empresa, competencia)"})
        raise
    return r.data[0]


@router.post("/upload", response_model=ResultadoUploadOrcamento, status_code=status.HTTP_201_CREATED)
def upload(
    empresa_id: UUID = Form(...),
    competencia: str = Form(..., pattern=r"^\d{4}-\d{2}$"),
    arquivo: UploadFile = File(...),
    current=Depends(get_current_user),
):
    client = get_supabase_authed(current["jwt"])
    bytes_xlsx = arquivo.file.read()
    try:
        return persistir_orcamento_xlsx(client, bytes_xlsx, empresa_id, competencia, current["id"])
    except ValueError as e:
        raise HTTPException(409, detail={"error": str(e)})


@router.patch("/{orcamento_id}/validar", response_model=OrcamentoOut)
def validar(orcamento_id: UUID, current=Depends(get_current_user)):
    client = get_supabase_authed(current["jwt"])
    r = client.table("orcamento").update({
        "status": "VALIDADO",
        "validado_em": "now()",
    }).eq("id", str(orcamento_id)).execute()
    if not r.data:
        raise HTTPException(404)
    return r.data[0]


@router.post("/{orcamento_id}/replicar", response_model=OrcamentoOut)
def replicar(orcamento_id: UUID, nova_competencia: str, current=Depends(get_current_user)):
    client = get_supabase_authed(current["jwt"])
    # Busca orçamento origem
    origem = client.table("orcamento").select("*").eq("id", str(orcamento_id)).single().execute().data
    if not origem:
        raise HTTPException(404)
    # Cria novo
    novo = client.table("orcamento").insert({
        "empresa_id": origem["empresa_id"],
        "competencia": nova_competencia,
        "status": "RASCUNHO",
        "criado_por": current["id"],
    }).execute()
    novo_id = novo.data[0]["id"]
    # Copia linhas
    linhas = client.table("orcamento_linha").select("*").eq("orcamento_id", str(orcamento_id)).execute().data
    if linhas:
        rows = [{**l, "orcamento_id": novo_id, "id": None, "created_at": None} for l in linhas]
        for r in rows:
            r.pop("id", None)
            r.pop("created_at", None)
        client.table("orcamento_linha").insert(rows).execute()
    return novo.data[0]


@router.delete("/{orcamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar(orcamento_id: UUID, current=Depends(get_current_user)):
    client = get_supabase_authed(current["jwt"])
    client.table("orcamento").delete().eq("id", str(orcamento_id)).execute()
    return None


@router.patch("/linhas/{linha_id}", response_model=OrcamentoLinhaOut)
def editar_linha(
    linha_id: UUID,
    payload: OrcamentoLinhaPatch,
    current=Depends(get_current_user),
):
    """Edita campos mutaveis de uma orcamento_linha (patch parcial).

    Campos ausentes no payload nao sao alterados. Para limpar um campo
    opcional (ex.: categoria_id), enviar explicitamente null.
    """
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, detail={"error": "Nada a atualizar"})
    client = get_supabase_authed(current["jwt"])
    r = client.table("orcamento_linha").update(updates).eq("id", str(linha_id)).execute()
    if not r.data:
        raise HTTPException(404, detail={"error": "Linha nao encontrada"})
    return r.data[0]


@router.delete("/linhas/{linha_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_linha(linha_id: UUID, current=Depends(get_current_user)):
    """Remove uma linha do orcamento."""
    client = get_supabase_authed(current["jwt"])
    client.table("orcamento_linha").delete().eq("id", str(linha_id)).execute()
    return None
