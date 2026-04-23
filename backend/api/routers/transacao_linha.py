"""Router /transacoes/{id}/split — split de uma transação em N alocações.

Invariante: sum(linhas.valor) = transacao_bancaria.valor (±0.01).
"""
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.deps import get_current_user, get_supabase_authed
from backend.api.schemas.transacao_linha import (
    SplitRequest,
    SplitResponse,
    TransacaoLinhaOut,
)


router = APIRouter(tags=["transacao_linha"])
TOLERANCIA = Decimal("0.01")


@router.get("/transacoes/{tx_id}")
def get_transacao(tx_id: UUID, current=Depends(get_current_user)):
    """Retorna dados básicos de uma transação bancária. Usado pela tela de split."""
    client = get_supabase_authed(current["jwt"])
    rows = (
        client.table("transacao_bancaria")
        .select("id,valor,titular_pix,descricao,data_extrato")
        .eq("id", str(tx_id))
        .limit(1)
        .execute()
        .data
    )
    if not rows:
        raise HTTPException(404, detail={"error": "Transação não encontrada"})
    return rows[0]


@router.get("/transacoes/{tx_id}/split", response_model=SplitResponse)
def get_split(tx_id: UUID, current=Depends(get_current_user)):
    client = get_supabase_authed(current["jwt"])
    tx = client.table("transacao_bancaria").select("id,valor").eq("id", str(tx_id)).limit(1).execute().data
    if not tx:
        raise HTTPException(404, detail={"error": "Transação não encontrada"})
    linhas = (
        client.table("transacao_linha")
        .select("*")
        .eq("transacao_bancaria_id", str(tx_id))
        .order("criado_em")
        .execute()
        .data
        or []
    )
    soma = sum(float(l["valor"]) for l in linhas)
    return SplitResponse(
        transacao_bancaria_id=tx_id,
        valor_transacao=float(tx[0]["valor"]),
        valor_soma_linhas=round(soma, 2),
        linhas=[TransacaoLinhaOut(**l) for l in linhas],
    )


@router.post("/transacoes/{tx_id}/split", response_model=SplitResponse, status_code=status.HTTP_200_OK)
def save_split(tx_id: UUID, payload: SplitRequest, current=Depends(get_current_user)):
    """Substitui todo o split da transação. Linhas existentes são deletadas."""
    if not payload.linhas:
        raise HTTPException(400, detail={"error": "Pelo menos uma linha é obrigatória"})
    client = get_supabase_authed(current["jwt"])
    tx = client.table("transacao_bancaria").select("id,valor").eq("id", str(tx_id)).limit(1).execute().data
    if not tx:
        raise HTTPException(404, detail={"error": "Transação não encontrada"})
    valor_tx = Decimal(str(tx[0]["valor"]))
    soma = sum(Decimal(str(l.valor)) for l in payload.linhas)
    if abs(soma - valor_tx) > TOLERANCIA:
        raise HTTPException(
            400,
            detail={
                "error": "Soma das linhas diverge do valor da transação",
                "valor_transacao": float(valor_tx),
                "valor_soma_linhas": float(soma),
            },
        )
    client.table("transacao_linha").delete().eq("transacao_bancaria_id", str(tx_id)).execute()
    rows = [
        {
            "transacao_bancaria_id": str(tx_id),
            "valor": float(l.valor),
            "bolso": l.bolso.value,
            "orcamento_linha_id": str(l.orcamento_linha_id) if l.orcamento_linha_id else None,
            "empresa_pagadora_id": str(l.empresa_pagadora_id) if l.empresa_pagadora_id else None,
            "descricao": l.descricao,
            "criado_por": current.get("id"),
        }
        for l in payload.linhas
    ]
    inserted = client.table("transacao_linha").insert(rows).execute().data or []
    return SplitResponse(
        transacao_bancaria_id=tx_id,
        valor_transacao=float(valor_tx),
        valor_soma_linhas=float(soma),
        linhas=[TransacaoLinhaOut(**l) for l in inserted],
    )


@router.delete("/transacoes/{tx_id}/split", status_code=status.HTTP_204_NO_CONTENT)
def delete_split(tx_id: UUID, current=Depends(get_current_user)):
    client = get_supabase_authed(current["jwt"])
    client.table("transacao_linha").delete().eq("transacao_bancaria_id", str(tx_id)).execute()
    return None


@router.get("/transacoes/{tx_id}/split/sugerir", response_model=SplitResponse)
def sugerir_split_do_ultimo(tx_id: UUID, current=Depends(get_current_user)):
    """Busca o último split do mesmo titular_pix e proporcionaliza ao valor atual."""
    client = get_supabase_authed(current["jwt"])
    tx = (
        client.table("transacao_bancaria")
        .select("id,valor,titular_pix")
        .eq("id", str(tx_id))
        .limit(1)
        .execute()
        .data
    )
    if not tx:
        raise HTTPException(404, detail={"error": "Transação não encontrada"})
    titular = (tx[0].get("titular_pix") or "").strip().upper()
    if not titular:
        return SplitResponse(
            transacao_bancaria_id=tx_id,
            valor_transacao=float(tx[0]["valor"]),
            valor_soma_linhas=0.0,
            linhas=[],
        )
    anteriores = (
        client.table("transacao_bancaria")
        .select("id,valor,data_extrato")
        .ilike("titular_pix", titular)
        .neq("id", str(tx_id))
        .order("data_extrato", desc=True)
        .limit(20)
        .execute()
        .data
        or []
    )
    for ant in anteriores:
        linhas = (
            client.table("transacao_linha")
            .select("*")
            .eq("transacao_bancaria_id", ant["id"])
            .execute()
            .data
            or []
        )
        if linhas:
            valor_atual = Decimal(str(tx[0]["valor"]))
            valor_ant = Decimal(str(ant["valor"]))
            if valor_ant == 0:
                continue
            ratio = valor_atual / valor_ant
            proporcionais = [
                {
                    **l,
                    "id": str(l["id"]),
                    "transacao_bancaria_id": str(tx_id),
                    "valor": float(round(Decimal(str(l["valor"])) * ratio, 2)),
                }
                for l in linhas
            ]
            return SplitResponse(
                transacao_bancaria_id=tx_id,
                valor_transacao=float(valor_atual),
                valor_soma_linhas=sum(p["valor"] for p in proporcionais),
                linhas=[TransacaoLinhaOut(**p) for p in proporcionais],
            )
    return SplitResponse(
        transacao_bancaria_id=tx_id,
        valor_transacao=float(tx[0]["valor"]),
        valor_soma_linhas=0.0,
        linhas=[],
    )
