"""Endpoints de contratos por cidade: lista agregada + carry-over + detalhe + edição."""
from __future__ import annotations

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


# ---------------------------------------------------------------------------
# Helpers — leitura cross-rodada
#
# Bug arquitetural: o mesmo (contrato, competência, prestador) pode ter
# registros_pp em múltiplas rodadas (PP re-importado em rodada nova).
# Sem filtro, queries somam entre rodadas → Saldo Original inflado.
#
# Solução em 2 partes:
#   1. Para Saldo Original / lista de prestadores: usar APENAS registros
#      da rodada com criado_em mais recente por chave.
#   2. Para Pago / Data de pagamento: usar PIX classificados a QUALQUER
#      registro_pp da mesma chave (qualquer rodada). Pagamento histórico
#      não pode sumir quando PP novo é re-importado.
# ---------------------------------------------------------------------------

def _created_at_por_rodada(client, rodada_ids: list[str]) -> dict[str, str]:
    """Busca rodada.criado_em em lote. Retorna {rodada_id: ISO_timestamp}."""
    if not rodada_ids:
        return {}
    rodadas = (
        client.table("rodada")
        .select("id,criado_em")
        .in_("id", rodada_ids)
        .execute()
        .data
        or []
    )
    return {r["id"]: r["criado_em"] for r in rodadas if r.get("id") and r.get("criado_em")}


def _filtrar_pela_rodada_mais_recente(
    rpps: list[dict],
    created_at_lookup: dict[str, str],
) -> list[dict]:
    """Mantém apenas registros_pp da rodada mais recente por (contrato_id,
    mes_competencia, prestador_id). Pura — sem DB.

    Cada rpp deve ter as chaves: id, contrato_id, mes_competencia,
    prestador_id, rodada_id. Comparação de criado_em é lexicográfica
    (ISO-8601 ordena corretamente).

    Em empate de criado_em, mantém a primeira rodada encontrada na lista
    (comportamento estável).
    """
    if not rpps:
        return []

    rodada_recente_por_chave: dict[tuple[str, str, str], str] = {}
    for r in rpps:
        cid = r.get("contrato_id")
        comp = r.get("mes_competencia")
        pid = r.get("prestador_id")
        rid = r.get("rodada_id")
        if not (cid and comp and pid and rid):
            continue
        chave = (cid, comp, pid)
        atual_rid = rodada_recente_por_chave.get(chave)
        if atual_rid is None:
            rodada_recente_por_chave[chave] = rid
            continue
        atual_t = created_at_lookup.get(atual_rid, "")
        cand_t = created_at_lookup.get(rid, "")
        if cand_t > atual_t:
            rodada_recente_por_chave[chave] = rid

    return [
        r for r in rpps
        if r.get("rodada_id")
        and r.get("contrato_id") and r.get("mes_competencia") and r.get("prestador_id")
        and r["rodada_id"] == rodada_recente_por_chave.get(
            (r["contrato_id"], r["mes_competencia"], r["prestador_id"])
        )
    ]


def _pix_por_chave(
    client,
    chaves: set[tuple[str, str, str]],
) -> dict[tuple[str, str, str], dict]:
    """Para cada chave (contrato_id, mes_competencia, prestador_id), retorna
    {pago: float (soma absoluta), data_max: Optional[str (ISO date)]}.

    Cobre PIX classificados a QUALQUER registro_pp da chave, em qualquer
    rodada. Necessario para que pagamentos historicos nao sumam quando
    PP novo é re-importado em rodada nova.
    """
    if not chaves:
        return {}

    contrato_ids = list({c[0] for c in chaves})
    competencias = list({c[1] for c in chaves})
    prestador_ids = list({c[2] for c in chaves})

    rpps = (
        client.table("registro_pp")
        .select("id,contrato_id,mes_competencia,prestador_id")
        .in_("contrato_id", contrato_ids)
        .in_("mes_competencia", competencias)
        .in_("prestador_id", prestador_ids)
        .execute()
        .data
        or []
    )
    rpp_to_chave: dict[str, tuple[str, str, str]] = {}
    for r in rpps:
        chave = (r.get("contrato_id"), r.get("mes_competencia"), r.get("prestador_id"))
        if chave in chaves:
            rpp_to_chave[r["id"]] = chave

    out: dict[tuple[str, str, str], dict] = {
        chave: {"pago": 0.0, "data_max": None} for chave in chaves
    }
    if not rpp_to_chave:
        return out

    txs = (
        client.table("transacao_bancaria")
        .select("registro_pp_id,valor,data_extrato")
        .in_("registro_pp_id", list(rpp_to_chave.keys()))
        .execute()
        .data
        or []
    )
    for t in txs:
        rid = t.get("registro_pp_id")
        if not rid:
            continue
        chave = rpp_to_chave.get(rid)
        if not chave:
            continue
        out[chave]["pago"] += abs(float(t.get("valor") or 0.0))
        d = t.get("data_extrato")
        if d:
            d_str = str(d)
            if out[chave]["data_max"] is None or d_str > out[chave]["data_max"]:
                out[chave]["data_max"] = d_str

    return out


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
    """Lista contratos-cidade da competencia. Agrupa por contrato.

    Saldo Original / lista de prestadores: somente registros da rodada
    com criado_em mais recente por (contrato, comp, prestador).
    Pago / data_pagamento: PIX classificados a registros_pp da mesma chave
    em QUALQUER rodada (helper _pix_por_chave).
    """
    if not competencia:
        return []
    if not _re.match(r"^\d{4}-\d{2}$", competencia):
        raise HTTPException(400, detail={"error": "competencia deve estar no formato YYYY-MM"})

    client = get_supabase_authed(current["jwt"])

    rpps = (
        client.table("registro_pp")
        .select("id,contrato_id,saldo_pp,prestador_id,mes_competencia,rodada_id")
        .eq("mes_competencia", competencia)
        .execute()
        .data
        or []
    )
    if not rpps:
        return []

    rodada_ids = list({r["rodada_id"] for r in rpps if r.get("rodada_id")})
    created_at_lookup = _created_at_por_rodada(client, rodada_ids)
    rpps = _filtrar_pela_rodada_mais_recente(rpps, created_at_lookup)
    if not rpps:
        return []

    contrato_ids = list({r["contrato_id"] for r in rpps if r.get("contrato_id")})
    contratos = (
        client.table("contrato").select("id,uf,cidade").in_("id", contrato_ids)
        .execute().data or []
    )
    contrato_by_id = {c["id"]: c for c in contratos}

    chaves = {
        (r["contrato_id"], r["mes_competencia"], r["prestador_id"])
        for r in rpps if r.get("contrato_id")
    }
    pix_lookup = _pix_por_chave(client, chaves)

    agreg: dict[str, dict] = {}
    for r in rpps:
        cid = r.get("contrato_id")
        if not cid or cid not in contrato_by_id:
            continue
        chave = (cid, r["mes_competencia"], r["prestador_id"])
        info = pix_lookup.get(chave, {"pago": 0.0, "data_max": None})
        a = agreg.setdefault(cid, {
            "total": 0.0, "total_pago": 0.0, "prestadores": set(),
            "data_max": None,
        })
        a["total"] += float(r["saldo_pp"])
        a["total_pago"] += info["pago"]
        a["prestadores"].add(r["prestador_id"])
        d = info["data_max"]
        if d and (a["data_max"] is None or d > a["data_max"]):
            a["data_max"] = d

    out: list[ContratoCidadeListItem] = []
    for cid, a in agreg.items():
        c = contrato_by_id[cid]
        total = round(a["total"], 2)
        pago = round(a["total_pago"], 2)
        saldo = round(total - pago, 2)
        if pago >= total and total > 0:
            st = "PAGO"
            data_pag = a["data_max"]
        elif pago > 0:
            st = "PARCIAL"
            data_pag = None
        else:
            st = "PENDENTE"
            data_pag = None
        out.append(ContratoCidadeListItem(
            id=cid, uf=c["uf"], cidade=c["cidade"], competencia=competencia,
            total=total, total_pago=pago, saldo=saldo,
            prestadores=len(a["prestadores"]), status=st,
            data_pagamento=data_pag,
        ))
    out.sort(key=lambda x: -x.saldo)
    return out


@router.get("/contratos/anteriores", response_model=list[ContratoAnteriorItem])
def listar_anteriores(
    ate: str,
    current=Depends(get_current_user),
):
    """Carry-over EM ABERTO: contratos com competencia < `ate` e saldo > 0.

    Quitados nao aparecem aqui — eles vao pra /contratos/anteriores-fechadas
    com o filtro 'apenas no mes da quitacao'.
    """
    if not _re.match(r"^\d{4}-\d{2}$", ate):
        raise HTTPException(400, detail={"error": "ate deve estar no formato YYYY-MM"})

    client = get_supabase_authed(current["jwt"])

    rpps = (
        client.table("registro_pp")
        .select("id,contrato_id,saldo_pp,prestador_id,mes_competencia,rodada_id")
        .lt("mes_competencia", ate)
        .execute()
        .data
        or []
    )
    if not rpps:
        return []

    rodada_ids = list({r["rodada_id"] for r in rpps if r.get("rodada_id")})
    created_at_lookup = _created_at_por_rodada(client, rodada_ids)
    rpps = _filtrar_pela_rodada_mais_recente(rpps, created_at_lookup)
    if not rpps:
        return []

    contrato_ids = list({r["contrato_id"] for r in rpps if r.get("contrato_id")})
    contratos = (
        client.table("contrato").select("id,uf,cidade").in_("id", contrato_ids)
        .execute().data or []
    )
    contrato_by_id = {c["id"]: c for c in contratos}

    chaves = {
        (r["contrato_id"], r["mes_competencia"], r["prestador_id"])
        for r in rpps if r.get("contrato_id")
    }
    pix_lookup = _pix_por_chave(client, chaves)

    agreg: dict[tuple[str, str], dict] = {}
    for r in rpps:
        cid = r.get("contrato_id")
        if not cid or cid not in contrato_by_id:
            continue
        comp = r["mes_competencia"]
        chave = (cid, comp, r["prestador_id"])
        info = pix_lookup.get(chave, {"pago": 0.0, "data_max": None})
        key = (cid, comp)
        a = agreg.setdefault(key, {
            "total": 0.0, "total_pago": 0.0, "prestadores": set(),
        })
        a["total"] += float(r["saldo_pp"])
        a["total_pago"] += info["pago"]
        a["prestadores"].add(r["prestador_id"])

    today = date.today()
    out: list[ContratoAnteriorItem] = []
    for (cid, comp), a in agreg.items():
        total = round(a["total"], 2)
        pago = round(a["total_pago"], 2)
        saldo = round(total - pago, 2)

        # So entra na lista 'em aberto' quem tem saldo positivo
        if saldo <= 0.01:
            continue
        if pago > 0:
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
            data_pagamento=None,
        ))
    out.sort(key=lambda x: x.competencia, reverse=True)
    return out


@router.get("/contratos/anteriores-fechadas", response_model=list[ContratoAnteriorItem])
def listar_anteriores_fechadas(
    ate: str,
    current=Depends(get_current_user),
):
    """Carry-over QUITADOS apenas no mes do filtro (data_pagamento[:7] == ate).

    Quitados em meses anteriores nao aparecem — a regra mantem a secao enxuta:
    contrato fica visivel apenas no mes em que foi efetivamente quitado.
    """
    if not _re.match(r"^\d{4}-\d{2}$", ate):
        raise HTTPException(400, detail={"error": "ate deve estar no formato YYYY-MM"})

    client = get_supabase_authed(current["jwt"])

    rpps = (
        client.table("registro_pp")
        .select("id,contrato_id,saldo_pp,prestador_id,mes_competencia,rodada_id")
        .lt("mes_competencia", ate)
        .execute()
        .data
        or []
    )
    if not rpps:
        return []

    rodada_ids = list({r["rodada_id"] for r in rpps if r.get("rodada_id")})
    created_at_lookup = _created_at_por_rodada(client, rodada_ids)
    rpps = _filtrar_pela_rodada_mais_recente(rpps, created_at_lookup)
    if not rpps:
        return []

    contrato_ids = list({r["contrato_id"] for r in rpps if r.get("contrato_id")})
    contratos = (
        client.table("contrato").select("id,uf,cidade").in_("id", contrato_ids)
        .execute().data or []
    )
    contrato_by_id = {c["id"]: c for c in contratos}

    chaves = {
        (r["contrato_id"], r["mes_competencia"], r["prestador_id"])
        for r in rpps if r.get("contrato_id")
    }
    pix_lookup = _pix_por_chave(client, chaves)

    agreg: dict[tuple[str, str], dict] = {}
    for r in rpps:
        cid = r.get("contrato_id")
        if not cid or cid not in contrato_by_id:
            continue
        comp = r["mes_competencia"]
        chave = (cid, comp, r["prestador_id"])
        info = pix_lookup.get(chave, {"pago": 0.0, "data_max": None})
        key = (cid, comp)
        a = agreg.setdefault(key, {
            "total": 0.0, "total_pago": 0.0, "prestadores": set(),
            "data_max": None,
        })
        a["total"] += float(r["saldo_pp"])
        a["total_pago"] += info["pago"]
        a["prestadores"].add(r["prestador_id"])
        d = info["data_max"]
        if d and (a["data_max"] is None or d > a["data_max"]):
            a["data_max"] = d

    today = date.today()
    out: list[ContratoAnteriorItem] = []
    for (cid, comp), a in agreg.items():
        total = round(a["total"], 2)
        pago = round(a["total_pago"], 2)
        saldo = round(total - pago, 2)
        data_max = a["data_max"]

        # Apenas quitados (saldo ~= 0)
        if saldo > 0.01:
            continue
        if total <= 0:
            continue
        # E apenas no mes da quitacao
        if data_max is None or data_max[:7] != ate:
            continue

        try:
            y, m, d_ = data_max[:10].split("-")
            data_pag = date(int(y), int(m), int(d_))
        except (ValueError, AttributeError):
            data_pag = None

        y, m = map(int, comp.split("-"))
        last_day = monthrange(y, m)[1]
        ref = date(y, m, last_day)
        idade = (today - ref).days
        c = contrato_by_id[cid]
        out.append(ContratoAnteriorItem(
            contrato_id=cid, uf=c["uf"], cidade=c["cidade"], competencia=comp,
            total_original=total, total_pago=pago, saldo_aberto=max(saldo, 0.0),
            prestadores=len(a["prestadores"]), status="QUITADO", idade_dias=max(idade, 0),
            data_pagamento=data_pag,
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
    """Detalhe contrato-cidade na competencia. Lista prestadores apenas da
    rodada mais recente; PIX cruzados por chave (qualquer rodada)."""
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
        "id,prestador_id,saldo_pp,local_pp,contrato_id,mes_competencia,rodada_id,prestador(nome)"
    ).eq("contrato_id", str(contrato_id)).eq("mes_competencia", competencia).execute().data or []

    rodada_ids = list({r["rodada_id"] for r in rpps if r.get("rodada_id")})
    created_at_lookup = _created_at_por_rodada(client, rodada_ids)
    rpps = _filtrar_pela_rodada_mais_recente(rpps, created_at_lookup)

    chaves = {
        (str(contrato_id), competencia, r["prestador_id"])
        for r in rpps if r.get("prestador_id")
    }
    pix_lookup = _pix_por_chave(client, chaves)

    linhas: list[PrestadorLinhaDetalhe] = []
    total_sum = 0.0
    pago_sum = 0.0
    prestadores_set = set()
    for r in rpps:
        chave = (str(contrato_id), competencia, r["prestador_id"])
        info = pix_lookup.get(chave, {"pago": 0.0, "data_max": None})
        total = float(r["saldo_pp"])
        pago = info["pago"]
        saldo = total - pago
        if pago >= total and total > 0:
            st = "PAGO"
        elif pago > 0:
            st = "PARCIAL"
        else:
            st = "PENDENTE"
        pd = None
        if info["data_max"]:
            try:
                y, m, d_ = info["data_max"][:10].split("-")
                pd = date(int(y), int(m), int(d_))
            except (ValueError, AttributeError):
                pd = None
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
