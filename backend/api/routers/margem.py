"""Endpoints de margem e realizado.

Três visões agregadas que abastecem as abas Faturamento, Despesas Variáveis e
Contratos (drilldown de margem por profissional). Sem mudança de schema.

Helpers reusados de `contratos_competencia.py` — os mesmos que mitigam o bug
arquitetural cross-rodada (rodada `22f82135` absorveu seed via UPSERT, fix em
2026-04-28). Qualquer query nova de `registro_pp` por `mes_competencia` SEM
`_filtrar_pela_rodada_mais_recente` reintroduz o bug. Documentado em
`/Users/dr.damasceno/second-brain/projetos/sistema-financeiro-spm/2026-04-25-rodada-com-unai-e-bug-cross-rodada.md`.
"""
from typing import List, Optional
from uuid import UUID
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException

from backend.api.deps import get_current_user, get_supabase_authed
from backend.api.routers.contratos_competencia import (
    _filtrar_pela_rodada_mais_recente,
    _created_at_por_rodada,
    _chunked_select,
)
from backend.api.schemas.margem import (
    RealizadoPorLinhaItem,
    MargemPorContratoOut,
    MargemPorProfissionalOut,
    ConciliacaoDetalheOut,
)


router = APIRouter(tags=["margem"])


# ---------------------------------------------------------------------------
# 4. conciliações detalhadas de uma linha (drawer multi-conta)
# ---------------------------------------------------------------------------

@router.get(
    "/orcamentos/linhas/{linha_id}/conciliacoes",
    response_model=List[ConciliacaoDetalheOut],
)
def conciliacoes_da_linha(
    linha_id: UUID,
    current=Depends(get_current_user),
):
    """Lista todas as conciliações de uma linha de orçamento, com dados da
    transação bancária associada. Alimenta o drawer multi-conta.
    """
    client = get_supabase_authed(current["jwt"])

    concs = (
        client.table("conciliacao_orcamento")
        .select("id,transacao_id,valor_aplicado,origem,aprovada_em")
        .eq("orcamento_linha_id", str(linha_id))
        .execute()
        .data
        or []
    )
    if not concs:
        return []

    tx_ids = list({c["transacao_id"] for c in concs if c.get("transacao_id")})
    txs = _chunked_select(
        client,
        tx_ids,
        lambda c, chunk: (
            c.table("transacao_bancaria")
            .select("id,titular_pix,valor,data_extrato,descricao,origem_banco,natureza_lancamento,conta_id")
            .in_("id", chunk)
        ),
    )
    tx_por_id = {t["id"]: t for t in txs}

    out: List[ConciliacaoDetalheOut] = []
    for c in concs:
        t = tx_por_id.get(c.get("transacao_id"))
        if not t:
            continue
        out.append(ConciliacaoDetalheOut(
            conciliacao_id=UUID(c["id"]),
            transacao_id=UUID(t["id"]),
            valor_aplicado=float(c.get("valor_aplicado") or 0.0),
            titular_pix=t.get("titular_pix"),
            data_extrato=str(t.get("data_extrato") or ""),
            descricao_tx=t.get("descricao"),
            origem_banco=t.get("origem_banco") or "BRADESCO",
            conta_id=UUID(t["conta_id"]) if t.get("conta_id") else None,
            natureza_lancamento=t.get("natureza_lancamento"),
            aprovada_em=c.get("aprovada_em"),
            origem=c.get("origem"),
        ))
    out.sort(key=lambda x: x.data_extrato, reverse=True)
    return out


# ---------------------------------------------------------------------------
# 1. realizado-por-linha
# ---------------------------------------------------------------------------

@router.get(
    "/orcamentos/{orcamento_id}/realizado-por-linha",
    response_model=List[RealizadoPorLinhaItem],
)
def realizado_por_linha(
    orcamento_id: UUID,
    current=Depends(get_current_user),
):
    """Para cada linha do orçamento, soma `conciliacao_orcamento.valor_aplicado`
    e retorna data da última transação conciliada + contagem de conciliações.

    Substitui o placeholder `—` em `tabela-linhas.tsx:146`. Habilita coluna
    Pago/Saldo/Status nas 3 abas de orçamento.
    """
    client = get_supabase_authed(current["jwt"])

    # 1. ids das linhas do orçamento
    linhas = (
        client.table("orcamento_linha")
        .select("id")
        .eq("orcamento_id", str(orcamento_id))
        .execute()
        .data
        or []
    )
    if not linhas:
        return []
    linha_ids = [l["id"] for l in linhas]

    # 2. conciliações das linhas (pode haver N conciliações por linha)
    concs = _chunked_select(
        client,
        linha_ids,
        lambda c, chunk: (
            c.table("conciliacao_orcamento")
            .select("orcamento_linha_id,transacao_id,valor_aplicado")
            .in_("orcamento_linha_id", chunk)
        ),
    )
    if not concs:
        return [RealizadoPorLinhaItem(linha_id=lid, pago=0.0, data_max=None, txs_count=0) for lid in linha_ids]

    # 3. data_extrato das transações referenciadas
    tx_ids = list({c["transacao_id"] for c in concs if c.get("transacao_id")})
    txs = _chunked_select(
        client,
        tx_ids,
        lambda c, chunk: (
            c.table("transacao_bancaria")
            .select("id,data_extrato")
            .in_("id", chunk)
        ),
    )
    data_por_tx = {t["id"]: t.get("data_extrato") for t in txs}

    # 4. agregação em Python
    agg: dict[str, dict] = {
        lid: {"pago": 0.0, "data_max": None, "txs_count": 0,
              "pago_cnab": 0.0, "data_max_cnab": None, "retornos_count": 0}
        for lid in linha_ids
    }
    for c in concs:
        lid = c.get("orcamento_linha_id")
        if not lid:
            continue
        a = agg[lid]
        a["pago"] += float(c.get("valor_aplicado") or 0.0)
        a["txs_count"] += 1
        d = data_por_tx.get(c.get("transacao_id"))
        if d:
            d_str = str(d)
            if a["data_max"] is None or d_str > a["data_max"]:
                a["data_max"] = d_str

    # 5. enriquecimento via retorno_pix CNAB-240 — fonte determinística pra
    #    linhas DESPESA_PROFISSIONAIS. O caminho:
    #      orcamento_linha (DESPESA_PROFISSIONAIS, contrato_id, competencia)
    #      → registro_pp (mesmo contrato + competencia)
    #      → retorno_pix (registro_pp_id matched, status CONFIRMADO)
    linhas_pp = (
        client.table("orcamento_linha")
        .select("id,contrato_id,natureza,orcamento:orcamento_id(competencia)")
        .eq("orcamento_id", str(orcamento_id))
        .eq("natureza", "DESPESA_PROFISSIONAIS")
        .execute()
        .data
        or []
    )
    pp_lines_with_contract = [
        l for l in linhas_pp
        if l.get("contrato_id") and (l.get("orcamento") or {}).get("competencia")
    ]
    if pp_lines_with_contract:
        # para cada (contrato_id, competencia), buscar registros_pp
        chaves_pp: dict[tuple[str, str], list[str]] = {}
        for l in pp_lines_with_contract:
            cid = l["contrato_id"]
            comp = l["orcamento"]["competencia"]
            chaves_pp.setdefault((cid, comp), []).append(l["id"])

        contrato_ids_pp = list({c for c, _ in chaves_pp.keys()})
        comps_pp = list({c for _, c in chaves_pp.keys()})
        rpps_pp = (
            client.table("registro_pp")
            .select("id,contrato_id,mes_competencia")
            .in_("contrato_id", contrato_ids_pp)
            .in_("mes_competencia", comps_pp)
            .execute()
            .data
            or []
        )
        # mapa registro_pp.id → linhas de orçamento candidatas
        rpp_to_orclinhas: dict[str, list[str]] = {}
        for r in rpps_pp:
            chave = (r.get("contrato_id"), r.get("mes_competencia"))
            for orclinha_id in chaves_pp.get(chave, []):
                rpp_to_orclinhas.setdefault(r["id"], []).append(orclinha_id)

        if rpp_to_orclinhas:
            retornos = _chunked_select(
                client,
                list(rpp_to_orclinhas.keys()),
                lambda c, chunk: (
                    c.table("retorno_pix")
                    .select("registro_pp_id,valor_efetivado,data_pagamento,status")
                    .in_("registro_pp_id", chunk)
                    .eq("status", "CONFIRMADO")
                ),
            )
            for r in retornos:
                rpp_id = r.get("registro_pp_id")
                if not rpp_id:
                    continue
                valor = float(r.get("valor_efetivado") or 0.0)
                data_pgto = r.get("data_pagamento")
                for orclinha_id in rpp_to_orclinhas.get(rpp_id, []):
                    a = agg.get(orclinha_id)
                    if not a:
                        continue
                    a["pago_cnab"] += valor
                    a["retornos_count"] += 1
                    if data_pgto:
                        d_str = str(data_pgto)
                        if a["data_max_cnab"] is None or d_str > a["data_max_cnab"]:
                            a["data_max_cnab"] = d_str

    return [
        RealizadoPorLinhaItem(
            linha_id=lid,
            pago=v["pago"],
            data_max=v["data_max"],
            txs_count=v["txs_count"],
            pago_cnab=v["pago_cnab"],
            data_max_cnab=v["data_max_cnab"],
            retornos_count=v["retornos_count"],
        )
        for lid, v in agg.items()
    ]


# ---------------------------------------------------------------------------
# 2. margem/por-contrato
# ---------------------------------------------------------------------------

@router.get("/margem/por-contrato", response_model=List[MargemPorContratoOut])
def margem_por_contrato(
    competencia: str,
    empresa_id: UUID,
    current=Depends(get_current_user),
):
    """Margem por contrato para a competência: faturamento previsto/realizado,
    despesa de profissionais previsto/realizado, margem absoluta e percentual.

    Origem dos dados:
    - **Previsto** (faturamento e despesa): `orcamento_linha` filtrado por
      orçamento da empresa+competência e naturezas {FATURAMENTO, DESPESA_PROFISSIONAIS}.
    - **Realizado** (faturamento e despesa): soma de `conciliacao_orcamento.valor_aplicado`
      das linhas de cada contrato.
    """
    client = get_supabase_authed(current["jwt"])

    # 1. orçamento da (empresa, competência)
    orc = (
        client.table("orcamento")
        .select("id")
        .eq("empresa_id", str(empresa_id))
        .eq("competencia", competencia)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not orc:
        return []
    orcamento_id = orc[0]["id"]

    # 2. linhas FATURAMENTO + DESPESA_PROFISSIONAIS desse orçamento
    linhas = (
        client.table("orcamento_linha")
        .select("id,natureza,contrato_id,valor_previsto")
        .eq("orcamento_id", orcamento_id)
        .in_("natureza", ["FATURAMENTO", "DESPESA_PROFISSIONAIS"])
        .execute()
        .data
        or []
    )
    if not linhas:
        return []

    # 3. realizado por linha (reutiliza lógica do endpoint 1)
    linha_ids = [l["id"] for l in linhas]
    concs = _chunked_select(
        client,
        linha_ids,
        lambda c, chunk: (
            c.table("conciliacao_orcamento")
            .select("orcamento_linha_id,valor_aplicado")
            .in_("orcamento_linha_id", chunk)
        ),
    )
    pago_por_linha: dict[str, float] = defaultdict(float)
    for c in concs:
        lid = c.get("orcamento_linha_id")
        if lid:
            pago_por_linha[lid] += float(c.get("valor_aplicado") or 0.0)

    # 4. agregação por contrato_id (None = sem contrato)
    Acc = lambda: {"f_prev": 0.0, "f_real": 0.0, "d_prev": 0.0, "d_real": 0.0}
    por_contrato: dict[Optional[str], dict] = defaultdict(Acc)
    for l in linhas:
        cid = l.get("contrato_id")
        natureza = l["natureza"]
        prev = float(l.get("valor_previsto") or 0.0)
        real = pago_por_linha.get(l["id"], 0.0)
        bucket = por_contrato[cid]
        if natureza == "FATURAMENTO":
            bucket["f_prev"] += prev
            bucket["f_real"] += real
        else:  # DESPESA_PROFISSIONAIS
            bucket["d_prev"] += prev
            bucket["d_real"] += real

    # 5. rótulo do contrato (UF-cidade)
    contrato_ids = [cid for cid in por_contrato.keys() if cid]
    rotulos: dict[str, str] = {}
    if contrato_ids:
        contratos = (
            client.table("contrato")
            .select("id,uf,cidade")
            .in_("id", contrato_ids)
            .execute()
            .data
            or []
        )
        rotulos = {c["id"]: f"{c['uf']}-{c['cidade']}" for c in contratos}

    # 6. monta saída
    out: List[MargemPorContratoOut] = []
    for cid, b in por_contrato.items():
        m_prev = b["f_prev"] - b["d_prev"]
        m_real = b["f_real"] - b["d_real"]
        m_pct = (m_real / b["f_real"]) if b["f_real"] > 0 else None
        out.append(MargemPorContratoOut(
            contrato_id=UUID(cid) if cid else None,
            rotulo=rotulos.get(cid, "(sem contrato)") if cid else "(sem contrato)",
            faturamento_previsto=b["f_prev"],
            faturamento_realizado=b["f_real"],
            despesa_prof_previsto=b["d_prev"],
            despesa_prof_realizado=b["d_real"],
            margem_previsto=m_prev,
            margem_realizado=m_real,
            margem_pct=m_pct,
        ))
    out.sort(key=lambda x: x.rotulo)
    return out


# ---------------------------------------------------------------------------
# 3. margem/por-profissional
# ---------------------------------------------------------------------------

@router.get("/margem/por-profissional", response_model=List[MargemPorProfissionalOut])
def margem_por_profissional(
    contrato_id: UUID,
    competencia: str,
    current=Depends(get_current_user),
):
    """Rateia a receita do contrato pelos prestadores que executaram plantões
    naquela competência, proporcionalmente ao `valor_bonificado`.

    INVARIANTE — bug `22f82135`: aplicar `_filtrar_pela_rodada_mais_recente`
    em `registro_pp` por `mes_competencia` é OBRIGATÓRIO. Sem isso, plantões
    do mesmo prestador em rodadas distintas se acumulam e o rateio infla.
    Caso reprodutível: MG-UNAI 02.26 baseline `22f82135` + rodada `a4fecc9e`
    — Saldo Original deve ser ≈ R$ 1.295.787, NÃO R$ 1.978.713.
    """
    client = get_supabase_authed(current["jwt"])
    contrato_str = str(contrato_id)

    # 1. plantões da chave (contrato, competência) — pode ter de múltiplas rodadas
    rpps = (
        client.table("registro_pp")
        .select("id,contrato_id,mes_competencia,prestador_id,rodada_id,valor_bonificado")
        .eq("contrato_id", contrato_str)
        .eq("mes_competencia", competencia)
        .execute()
        .data
        or []
    )
    if not rpps:
        return []

    # 2. filtrar pela rodada mais recente (invariante cross-rodada)
    rodada_ids = list({r.get("rodada_id") for r in rpps if r.get("rodada_id")})
    created_at_lookup = _created_at_por_rodada(client, rodada_ids)
    rpps_filtrados = _filtrar_pela_rodada_mais_recente(rpps, created_at_lookup)

    # 3. soma valor_bonificado por prestador
    bonif_por_prestador: dict[str, float] = defaultdict(float)
    for r in rpps_filtrados:
        pid = r.get("prestador_id")
        if pid:
            bonif_por_prestador[pid] += float(r.get("valor_bonificado") or 0.0)
    total_bonificacao = sum(bonif_por_prestador.values())
    if total_bonificacao <= 0:
        return []

    # 4. receita do contrato — usa REALIZADO (FATURAMENTO conciliado) com fallback PREVISTO
    #    Procura linha de orcamento_linha natureza=FATURAMENTO + contrato_id + competencia.
    #    Atravessa o relacionamento orcamento_linha → orcamento → competencia.
    fatura_linhas = (
        client.table("orcamento_linha")
        .select("id,valor_previsto,orcamento:orcamento_id(competencia)")
        .eq("contrato_id", contrato_str)
        .eq("natureza", "FATURAMENTO")
        .execute()
        .data
        or []
    )
    fatura_da_comp = [
        l for l in fatura_linhas
        if (l.get("orcamento") or {}).get("competencia") == competencia
    ]
    receita_prevista = sum(float(l.get("valor_previsto") or 0.0) for l in fatura_da_comp)

    receita_realizada = 0.0
    if fatura_da_comp:
        ids = [l["id"] for l in fatura_da_comp]
        concs = _chunked_select(
            client,
            ids,
            lambda c, chunk: (
                c.table("conciliacao_orcamento")
                .select("valor_aplicado")
                .in_("orcamento_linha_id", chunk)
            ),
        )
        receita_realizada = sum(float(c.get("valor_aplicado") or 0.0) for c in concs)

    # Receita pro rateio: prefere realizada, senão prevista
    receita_para_rateio = receita_realizada if receita_realizada > 0 else receita_prevista
    if receita_para_rateio <= 0:
        # Sem receita registrada — devolve com share/receita zero, só bonificação
        receita_para_rateio = 0.0

    # 5. nomes dos prestadores
    prestador_ids = list(bonif_por_prestador.keys())
    prestadores = (
        client.table("prestador")
        .select("id,nome")
        .in_("id", prestador_ids)
        .execute()
        .data
        or []
    )
    nome_por_id = {p["id"]: p.get("nome") or "(sem nome)" for p in prestadores}

    # 6. PIX confirmado via retorno_pix (CNAB-240) por prestador
    #    Caminho: registros_pp filtrados → retorno_pix.registro_pp_id (CONFIRMADO).
    rpp_ids_filtrados = [r["id"] for r in rpps_filtrados if r.get("id")]
    rpp_to_prestador = {r["id"]: r["prestador_id"] for r in rpps_filtrados if r.get("id") and r.get("prestador_id")}
    pix_por_prestador: dict[str, dict] = {pid: {"valor": 0.0, "data": None} for pid in prestador_ids}
    if rpp_ids_filtrados:
        retornos = _chunked_select(
            client,
            rpp_ids_filtrados,
            lambda c, chunk: (
                c.table("retorno_pix")
                .select("registro_pp_id,valor_efetivado,data_pagamento,status")
                .in_("registro_pp_id", chunk)
                .eq("status", "CONFIRMADO")
            ),
        )
        for r in retornos:
            rpp_id = r.get("registro_pp_id")
            pid = rpp_to_prestador.get(rpp_id) if rpp_id else None
            if not pid or pid not in pix_por_prestador:
                continue
            pix_por_prestador[pid]["valor"] += float(r.get("valor_efetivado") or 0.0)
            d = r.get("data_pagamento")
            if d:
                d_str = str(d)
                if pix_por_prestador[pid]["data"] is None or d_str > pix_por_prestador[pid]["data"]:
                    pix_por_prestador[pid]["data"] = d_str

    # 7. monta saída ordenada por margem decrescente
    out: List[MargemPorProfissionalOut] = []
    for pid, bonif in bonif_por_prestador.items():
        share = bonif / total_bonificacao if total_bonificacao > 0 else 0.0
        receita_atrib = share * receita_para_rateio
        margem_abs = receita_atrib - bonif
        margem_pct = (margem_abs / receita_atrib) if receita_atrib > 0 else None
        pix_info = pix_por_prestador.get(pid, {"valor": 0.0, "data": None})
        out.append(MargemPorProfissionalOut(
            prestador_id=UUID(pid),
            prestador_nome=nome_por_id.get(pid, "(sem nome)"),
            bonificacao=bonif,
            share=share,
            receita_atribuida=receita_atrib,
            margem_absoluta=margem_abs,
            margem_pct=margem_pct,
            pix_confirmado=pix_info["valor"],
            data_ultimo_pix=pix_info["data"],
        ))
    out.sort(key=lambda x: x.margem_absoluta, reverse=True)
    return out
