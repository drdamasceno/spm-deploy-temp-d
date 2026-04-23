"""Endpoints de contratos por cidade: lista agregada + carry-over + detalhe + edição."""
from typing import Optional
from uuid import UUID
from datetime import date
from calendar import monthrange
import re as _re

from fastapi import APIRouter, Depends, HTTPException

from backend.api.deps import get_current_user, get_supabase_authed
from backend.api.schemas.contrato_competencia import (
    ContratoCidadeListItem,
    ContratoAnteriorItem,
    ContratoDetalheOut,
    ContratoDadosExtras,
    PrestadorLinhaDetalhe,
)


router = APIRouter(tags=["contratos_competencia"])


@router.get("/contratos/cadastrados")
def listar_contratos_cadastrados(current=Depends(get_current_user)):
    """Lista todos os contratos da tabela `contrato` (sem filtro por competência).

    Usado para popular o select de 'Contrato vinculado' no editor de linha
    de orçamento. Retorna {id, uf, cidade, nome, status} ordenado por UF+cidade.
    """
    client = get_supabase_authed(current["jwt"])
    rows = (
        client.table("contrato")
        .select("id,uf,cidade,nome,nome_oficial,status")
        .order("uf")
        .order("cidade")
        .execute()
        .data
        or []
    )
    return rows


@router.get("/contratos", response_model=list[ContratoCidadeListItem])
def listar_contratos(
    competencia: Optional[str] = None,
    current=Depends(get_current_user),
):
    """Lista contratos-cidade da competência. Agrupa saldo e status."""
    if not competencia:
        return []
    if not _re.match(r"^\d{4}-\d{2}$", competencia):
        raise HTTPException(400, detail={"error": "competencia deve estar no formato YYYY-MM"})

    client = get_supabase_authed(current["jwt"])

    rpps = (
        client.table("registro_pp")
        .select("id,contrato_id,saldo_pp,prestador_id")
        .eq("mes_competencia", competencia)
        .execute()
        .data
    )
    if not rpps:
        return []

    contrato_ids = list({r["contrato_id"] for r in rpps if r.get("contrato_id")})
    if not contrato_ids:
        return []
    contratos = (
        client.table("contrato")
        .select("id,uf,cidade")
        .in_("id", contrato_ids)
        .execute()
        .data
    )
    contrato_by_id = {c["id"]: c for c in contratos}

    rpp_ids = [r["id"] for r in rpps]
    txs = (
        client.table("transacao_bancaria")
        .select("registro_pp_id,valor")
        .in_("registro_pp_id", rpp_ids)
        .execute()
        .data
    )
    pago_por_rpp: dict[str, float] = {}
    for t in txs:
        rpp_id = t.get("registro_pp_id")
        if rpp_id:
            pago_por_rpp[rpp_id] = pago_por_rpp.get(rpp_id, 0.0) + abs(float(t["valor"]))

    agreg: dict[str, dict] = {}
    for r in rpps:
        cid = r.get("contrato_id")
        if not cid or cid not in contrato_by_id:
            continue
        a = agreg.setdefault(cid, {
            "total": 0.0, "total_pago": 0.0, "prestadores": set(),
        })
        a["total"] += float(r["saldo_pp"])
        a["total_pago"] += pago_por_rpp.get(r["id"], 0.0)
        a["prestadores"].add(r["prestador_id"])

    out: list[ContratoCidadeListItem] = []
    for cid, a in agreg.items():
        c = contrato_by_id[cid]
        total = round(a["total"], 2)
        pago = round(a["total_pago"], 2)
        saldo = round(total - pago, 2)
        if pago >= total and total > 0:
            st = "PAGO"
        elif pago > 0:
            st = "PARCIAL"
        else:
            st = "PENDENTE"
        out.append(ContratoCidadeListItem(
            id=cid, uf=c["uf"], cidade=c["cidade"], competencia=competencia,
            total=total, total_pago=pago, saldo=saldo,
            prestadores=len(a["prestadores"]), status=st,
        ))
    out.sort(key=lambda x: -x.saldo)
    return out


@router.get("/contratos/anteriores", response_model=list[ContratoAnteriorItem])
def listar_anteriores(
    ate: str,
    current=Depends(get_current_user),
):
    """Retorna contratos com saldo em aberto em competências < `ate`."""
    if not _re.match(r"^\d{4}-\d{2}$", ate):
        raise HTTPException(400, detail={"error": "ate deve estar no formato YYYY-MM"})

    client = get_supabase_authed(current["jwt"])

    rpps = (
        client.table("registro_pp")
        .select("id,contrato_id,saldo_pp,prestador_id,mes_competencia")
        .lt("mes_competencia", ate)
        .execute()
        .data
    )
    if not rpps:
        return []

    contrato_ids = list({r["contrato_id"] for r in rpps if r.get("contrato_id")})
    contratos = (
        client.table("contrato").select("id,uf,cidade").in_("id", contrato_ids).execute().data
        if contrato_ids else []
    )
    contrato_by_id = {c["id"]: c for c in contratos}

    rpp_ids = [r["id"] for r in rpps]
    txs = (
        client.table("transacao_bancaria")
        .select("registro_pp_id,valor").in_("registro_pp_id", rpp_ids).execute().data
        if rpp_ids else []
    )
    pago_por_rpp: dict[str, float] = {}
    for t in txs:
        rid = t.get("registro_pp_id")
        if rid:
            pago_por_rpp[rid] = pago_por_rpp.get(rid, 0.0) + abs(float(t["valor"]))

    agreg: dict[tuple, dict] = {}
    for r in rpps:
        cid = r.get("contrato_id")
        if not cid or cid not in contrato_by_id:
            continue
        key = (cid, r["mes_competencia"])
        a = agreg.setdefault(key, {
            "total": 0.0, "total_pago": 0.0, "prestadores": set(),
        })
        a["total"] += float(r["saldo_pp"])
        a["total_pago"] += pago_por_rpp.get(r["id"], 0.0)
        a["prestadores"].add(r["prestador_id"])

    today = date.today()
    out: list[ContratoAnteriorItem] = []
    for (cid, comp), a in agreg.items():
        total = round(a["total"], 2)
        pago = round(a["total_pago"], 2)
        saldo = round(total - pago, 2)
        if saldo <= 0.01:
            continue
        if pago >= total and total > 0:
            st = "PAGO"
        elif pago > 0:
            st = "PARCIAL"
        else:
            st = "PENDENTE"
        y, m = map(int, comp.split("-"))
        last_day = monthrange(y, m)[1]
        ref = date(y, m, last_day)
        idade = (today - ref).days
        c = contrato_by_id[cid]
        out.append(ContratoAnteriorItem(
            contrato_id=cid, uf=c["uf"], cidade=c["cidade"], competencia=comp,
            total_original=total, total_pago=pago, saldo_aberto=saldo,
            prestadores=len(a["prestadores"]), status=st, idade_dias=max(idade, 0),
        ))
    out.sort(key=lambda x: x.competencia, reverse=True)
    return out


@router.patch("/contratos/{contrato_id}", response_model=ContratoDadosExtras)
def editar_dados_contrato(
    contrato_id: UUID,
    payload: ContratoDadosExtras,
    current=Depends(get_current_user),
):
    """Atualiza campos extras do contrato."""
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, detail={"error": "Nada a atualizar"})
    client = get_supabase_authed(current["jwt"])
    r = client.table("contrato").update(updates).eq("id", str(contrato_id)).execute()
    if not r.data:
        raise HTTPException(404, detail={"error": "Contrato não encontrado"})
    d = r.data[0]
    return ContratoDadosExtras(
        nome_oficial=d.get("nome_oficial"),
        cnpj=d.get("cnpj"),
        tipo=d.get("tipo"),
        valor_faturamento_mensal=d.get("valor_faturamento_mensal"),
        retencao_tributaria_pct=d.get("retencao_tributaria_pct"),
        observacoes=d.get("observacoes"),
    )


@router.get(
    "/contratos/{contrato_id}/competencia/{competencia}",
    response_model=ContratoDetalheOut,
)
def detalhe(contrato_id: UUID, competencia: str, current=Depends(get_current_user)):
    """Detalhe do contrato-cidade na competência: KPIs + lista por (prestador × local)."""
    if not _re.match(r"^\d{4}-\d{2}$", competencia):
        raise HTTPException(400, detail={"error": "competencia deve estar no formato YYYY-MM"})

    client = get_supabase_authed(current["jwt"])

    c = client.table("contrato").select(
        "id,uf,cidade,nome_oficial,cnpj,tipo,valor_faturamento_mensal,retencao_tributaria_pct,observacoes"
    ).eq("id", str(contrato_id)).limit(1).execute().data
    if not c:
        raise HTTPException(404, detail={"error": "Contrato não encontrado"})
    c = c[0]

    rpps = client.table("registro_pp").select(
        "id,prestador_id,saldo_pp,local_pp,prestador(nome)"
    ).eq("contrato_id", str(contrato_id)).eq("mes_competencia", competencia).execute().data

    rpp_ids = [r["id"] for r in rpps]
    txs = (
        client.table("transacao_bancaria")
        .select("registro_pp_id,valor,data_extrato").in_("registro_pp_id", rpp_ids).execute().data
        if rpp_ids else []
    )
    pago_por_rpp: dict[str, float] = {}
    data_max_por_rpp: dict[str, str] = {}
    for t in txs:
        rid = t.get("registro_pp_id")
        if rid:
            pago_por_rpp[rid] = pago_por_rpp.get(rid, 0.0) + abs(float(t["valor"]))
            d = str(t["data_extrato"])
            if rid not in data_max_por_rpp or d > data_max_por_rpp[rid]:
                data_max_por_rpp[rid] = d

    linhas: list[PrestadorLinhaDetalhe] = []
    total_sum = 0.0
    pago_sum = 0.0
    prestadores_set = set()
    for r in rpps:
        total = float(r["saldo_pp"])
        pago = pago_por_rpp.get(r["id"], 0.0)
        saldo = total - pago
        if pago >= total and total > 0:
            st = "PAGO"
        elif pago > 0:
            st = "PARCIAL"
        else:
            st = "PENDENTE"
        pd = data_max_por_rpp.get(r["id"])
        prest = r.get("prestador")
        if isinstance(prest, dict):
            nome = prest.get("nome", "—")
        elif isinstance(prest, list) and prest:
            nome = prest[0].get("nome", "—")
        else:
            nome = "—"
        linhas.append(PrestadorLinhaDetalhe(
            prestador_id=r["prestador_id"],
            prestador_nome=nome,
            local=r.get("local_pp"),
            competencia=competencia,
            total=round(total, 2),
            total_pago=round(pago, 2),
            saldo=round(saldo, 2),
            status=st,
            data_pagamento=pd,
        ))
        total_sum += total
        pago_sum += pago
        prestadores_set.add(r["prestador_id"])

    return ContratoDetalheOut(
        contrato_id=c["id"], uf=c["uf"], cidade=c["cidade"], competencia=competencia,
        total=round(total_sum, 2), total_pago=round(pago_sum, 2),
        saldo=round(total_sum - pago_sum, 2),
        prestadores_count=len(prestadores_set),
        registros_count=len(rpps),
        linhas=linhas,
        dados_extras=ContratoDadosExtras(
            nome_oficial=c.get("nome_oficial"),
            cnpj=c.get("cnpj"),
            tipo=c.get("tipo"),
            valor_faturamento_mensal=c.get("valor_faturamento_mensal"),
            retencao_tributaria_pct=c.get("retencao_tributaria_pct"),
            observacoes=c.get("observacoes"),
        ),
    )
