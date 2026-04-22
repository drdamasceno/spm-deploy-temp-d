"""Endpoints de /saldos e /aplicacoes — Track D: dashboard de liquidez."""
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from backend.api.deps import get_current_user, get_supabase_authed
from backend.api.schemas.saldos import (
    AplicacaoCreate,
    AplicacaoOut,
    AplicacaoPatch,
    ContaLiquidezItem,
    DashboardSaldos,
    SaldoManualInput,
)


router = APIRouter(tags=["saldos"])


@router.get("/saldos/dashboard", response_model=DashboardSaldos)
def dashboard(current=Depends(get_current_user)):
    """Retorna contas correntes (último snapshot por conta) + aplicações ativas + totais."""
    client = get_supabase_authed(current["jwt"])

    # Contas bancárias ativas
    contas = client.table("conta_bancaria").select("id,banco,agencia,conta,finalidade").eq("ativo", True).execute().data or []

    # Último snapshot por conta
    contas_liquidez: list[ContaLiquidezItem] = []
    total_contas = 0.0
    today = date.today()
    for c in contas:
        snap = (
            client.table("saldo_conta_snapshot")
            .select("saldo_valor,data_referencia,origem")
            .eq("conta_bancaria_id", c["id"])
            .order("data_referencia", desc=True)
            .order("criado_em", desc=True)
            .limit(1)
            .execute()
            .data
        )
        if snap:
            s = snap[0]
            saldo = float(s["saldo_valor"])
            data_ref = date.fromisoformat(s["data_referencia"]) if s.get("data_referencia") else None
            dias = (today - data_ref).days if data_ref else None
            origem = s.get("origem")
        else:
            saldo = 0.0
            data_ref = None
            dias = None
            origem = None
        contas_liquidez.append(ContaLiquidezItem(
            conta_id=c["id"], banco=c["banco"], agencia=c["agencia"], conta=c["conta"],
            finalidade=c["finalidade"], saldo_valor=round(saldo, 2),
            data_referencia=data_ref, origem=origem, dias_desatualizado=dias,
        ))
        total_contas += saldo

    # Aplicações ativas
    aps_raw = (
        client.table("aplicacao_financeira")
        .select("*")
        .eq("ativo", True)
        .order("valor_atual", desc=True)
        .execute()
        .data or []
    )
    aplicacoes: list[AplicacaoOut] = [AplicacaoOut(
        id=a["id"], nome=a["nome"], tipo=a["tipo"],
        valor_atual=float(a["valor_atual"]),
        data_atualizacao=a["data_atualizacao"],
        modo=a["modo"],
        instituicao=a.get("instituicao"),
        rentabilidade=a.get("rentabilidade"),
        data_vencimento=a.get("data_vencimento"),
        liquidez=a.get("liquidez"),
        observacoes=a.get("observacoes"),
        ativo=a.get("ativo", True),
    ) for a in aps_raw]

    total_aplic_auto = sum(a.valor_atual for a in aplicacoes if a.modo == "AUTOMATICA")
    total_aplic_manual = sum(a.valor_atual for a in aplicacoes if a.modo == "MANUAL")
    liquidez_total = total_contas + total_aplic_auto + total_aplic_manual

    return DashboardSaldos(
        contas=contas_liquidez,
        aplicacoes=aplicacoes,
        liquidez_total=round(liquidez_total, 2),
        disponivel_agora=round(total_contas + total_aplic_auto, 2),
        reserva_travada=round(total_aplic_manual, 2),
    )


@router.post("/saldos/conta-manual", status_code=201)
def saldo_manual(payload: SaldoManualInput, current=Depends(get_current_user)):
    """Registra um snapshot manual de saldo de conta corrente."""
    client = get_supabase_authed(current["jwt"])
    r = client.table("saldo_conta_snapshot").insert({
        "conta_bancaria_id": str(payload.conta_bancaria_id),
        "saldo_valor": payload.saldo_valor,
        "data_referencia": payload.data_referencia.isoformat(),
        "origem": "MANUAL",
        "observacao": payload.observacao,
        "criado_por": current["id"],
    }).execute()
    if not r.data:
        raise HTTPException(500, detail={"error": "Falha ao registrar snapshot"})
    return {"id": r.data[0]["id"]}


@router.get("/aplicacoes", response_model=list[AplicacaoOut])
def listar_aplicacoes(
    incluir_inativas: bool = False,
    current=Depends(get_current_user),
):
    client = get_supabase_authed(current["jwt"])
    q = client.table("aplicacao_financeira").select("*")
    if not incluir_inativas:
        q = q.eq("ativo", True)
    rows = q.order("valor_atual", desc=True).execute().data or []
    return [AplicacaoOut(
        id=a["id"], nome=a["nome"], tipo=a["tipo"],
        valor_atual=float(a["valor_atual"]),
        data_atualizacao=a["data_atualizacao"],
        modo=a["modo"],
        instituicao=a.get("instituicao"),
        rentabilidade=a.get("rentabilidade"),
        data_vencimento=a.get("data_vencimento"),
        liquidez=a.get("liquidez"),
        observacoes=a.get("observacoes"),
        ativo=a.get("ativo", True),
    ) for a in rows]


@router.post("/aplicacoes", response_model=AplicacaoOut, status_code=201)
def criar_aplicacao(payload: AplicacaoCreate, current=Depends(get_current_user)):
    client = get_supabase_authed(current["jwt"])
    data = payload.model_dump(mode="json", exclude_unset=True)
    data["data_atualizacao"] = data.get("data_atualizacao") or date.today().isoformat()
    data["criado_por"] = current["id"]
    r = client.table("aplicacao_financeira").insert(data).execute()
    if not r.data:
        raise HTTPException(500, detail={"error": "Falha ao criar aplicação"})
    a = r.data[0]
    return AplicacaoOut(
        id=a["id"], nome=a["nome"], tipo=a["tipo"],
        valor_atual=float(a["valor_atual"]),
        data_atualizacao=a["data_atualizacao"],
        modo=a["modo"],
        instituicao=a.get("instituicao"),
        rentabilidade=a.get("rentabilidade"),
        data_vencimento=a.get("data_vencimento"),
        liquidez=a.get("liquidez"),
        observacoes=a.get("observacoes"),
        ativo=a.get("ativo", True),
    )


@router.patch("/aplicacoes/{aplicacao_id}", response_model=AplicacaoOut)
def editar_aplicacao(aplicacao_id: UUID, payload: AplicacaoPatch, current=Depends(get_current_user)):
    updates = payload.model_dump(mode="json", exclude_unset=True)
    if not updates:
        raise HTTPException(400, detail={"error": "Nada a atualizar"})
    updates["updated_em"] = "now()"
    client = get_supabase_authed(current["jwt"])
    r = client.table("aplicacao_financeira").update(updates).eq("id", str(aplicacao_id)).execute()
    if not r.data:
        raise HTTPException(404, detail={"error": "Aplicação não encontrada"})
    a = r.data[0]
    return AplicacaoOut(
        id=a["id"], nome=a["nome"], tipo=a["tipo"],
        valor_atual=float(a["valor_atual"]),
        data_atualizacao=a["data_atualizacao"],
        modo=a["modo"],
        instituicao=a.get("instituicao"),
        rentabilidade=a.get("rentabilidade"),
        data_vencimento=a.get("data_vencimento"),
        liquidez=a.get("liquidez"),
        observacoes=a.get("observacoes"),
        ativo=a.get("ativo", True),
    )


@router.delete("/aplicacoes/{aplicacao_id}", status_code=204)
def deletar_aplicacao(aplicacao_id: UUID, current=Depends(get_current_user)):
    """Soft-delete (ativo=false)."""
    client = get_supabase_authed(current["jwt"])
    client.table("aplicacao_financeira").update({"ativo": False}).eq("id", str(aplicacao_id)).execute()
    return None
