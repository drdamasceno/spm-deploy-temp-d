from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.deps import get_current_user, get_supabase_authed
from backend.api.schemas.adiantamento import AdiantamentoOut, AdiantamentoCompensarIn


router = APIRouter(prefix="/adiantamentos", tags=["adiantamento"])


@router.get("", response_model=List[AdiantamentoOut])
def listar(
    status_filtro: str | None = None,
    prestador_id: UUID | None = None,
    current=Depends(get_current_user),
):
    """Lista adiantamentos. Filtros opcionais por status e prestador."""
    client = get_supabase_authed(current["jwt"])
    q = client.table("adiantamento").select("*").order("data_pagamento", desc=True)
    if status_filtro:
        q = q.eq("status", status_filtro)
    if prestador_id:
        q = q.eq("prestador_id", str(prestador_id))
    return q.execute().data


@router.get("/{adiantamento_id}/registros_pp_disponiveis", response_model=list[dict])
def listar_registros_disponiveis(adiantamento_id: UUID, current=Depends(get_current_user)):
    """Lista registro_pp elegíveis para compensar este adiantamento (mesmo prestador, ELEGIVEL)."""
    client = get_supabase_authed(current["jwt"])
    adi = client.table("adiantamento").select("prestador_id,data_pagamento").eq("id", str(adiantamento_id)).limit(1).execute().data
    if not adi:
        raise HTTPException(404, detail={"error": "Adiantamento não encontrado"})
    rpps = client.table("registro_pp").select("id,contrato_id,mes_competencia,saldo_pp,status_saldo,contrato(nome)").eq("prestador_id", adi[0]["prestador_id"]).eq("status_saldo", "ELEGIVEL").order("mes_competencia", desc=True).execute().data
    return rpps


@router.post("/{adiantamento_id}/compensar", response_model=AdiantamentoOut)
def compensar(
    adiantamento_id: UUID,
    payload: AdiantamentoCompensarIn,
    current=Depends(get_current_user),
):
    """
    Marca compensação manual de adiantamento contra PP futuro.
    Valida: (1) adiantamento em status ABERTO; (2) registro_pp pertence ao mesmo prestador.
    """
    client = get_supabase_authed(current["jwt"])

    # 1. Carrega adiantamento
    adi = client.table("adiantamento").select("*").eq("id", str(adiantamento_id)).limit(1).execute().data
    if not adi:
        raise HTTPException(404, detail={"error": "Adiantamento não encontrado"})
    adi = adi[0]
    if adi["status"] != "ABERTO":
        raise HTTPException(409, detail={"error": f"Adiantamento já está em status {adi['status']}"})

    # 2. Valida registro_pp do mesmo prestador
    rpp = client.table("registro_pp").select("id,prestador_id").eq("id", str(payload.registro_pp_id)).limit(1).execute().data
    if not rpp:
        raise HTTPException(404, detail={"error": "registro_pp não encontrado"})
    if rpp[0]["prestador_id"] != adi["prestador_id"]:
        raise HTTPException(400, detail={"error": "registro_pp pertence a outro prestador"})

    # 3. Update
    r = client.table("adiantamento").update({
        "status": "COMPENSADO_TOTAL",
        "compensado_em_registro_pp_id": str(payload.registro_pp_id),
        "compensado_em": "now()",
    }).eq("id", str(adiantamento_id)).execute()
    if not r.data:
        raise HTTPException(500, detail={"error": "Falha ao atualizar adiantamento"})
    return r.data[0]
