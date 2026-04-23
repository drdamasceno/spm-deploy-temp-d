"""Router /dashboard — KPIs + previsto x realizado + alertas.

Spec v2 §5.5 — agregações por (competencia, empresa). Para empresa=TODAS,
agrega SPM + FD. KPIs são best-effort no MVP (saldo_inicial=0; débito técnico
documentado no spec §3.1 Fase 2).
"""
from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends, Query

from backend.api.deps import get_current_user, get_supabase_authed
from backend.api.schemas.dashboard import DashboardResponse, KPIs, BarraPxR, Alerta


router = APIRouter(tags=["dashboard"])


def _primeiro_dia(competencia: str) -> str:
    return f"{competencia}-01"


def _ultimo_dia(competencia: str) -> str:
    import calendar
    y, m = competencia.split("-")
    last = calendar.monthrange(int(y), int(m))[1]
    return f"{y}-{m}-{last:02d}"


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    competencia: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    empresa: str = Query("TODAS", pattern=r"^(SPM|FD|TODAS)$"),
    current=Depends(get_current_user),
):
    """
    Agregações do dashboard. Respeita filtro de empresa (via orcamento.empresa_id).
    Para "TODAS", agrega SPM + FD.
    """
    client = get_supabase_authed(current["jwt"])
    d_ini = _primeiro_dia(competencia)
    d_fim = _ultimo_dia(competencia)

    # --- 1. Resolver empresa_ids conforme filtro ---
    if empresa == "TODAS":
        emp_rows = (
            client.table("empresa")
            .select("id,codigo")
            .in_("codigo", ["SPM", "FD"])
            .execute()
            .data
        )
    else:
        emp_rows = (
            client.table("empresa")
            .select("id,codigo")
            .eq("codigo", empresa)
            .execute()
            .data
        )
    empresa_ids = [e["id"] for e in emp_rows]

    # --- 2. Orcamento(s) da competencia para esses empresa_ids ---
    orc_ids: list[str] = []
    if empresa_ids:
        orc_rows = (
            client.table("orcamento")
            .select("id")
            .eq("competencia", competencia)
            .in_("empresa_id", empresa_ids)
            .execute()
            .data
        )
        orc_ids = [o["id"] for o in orc_rows]

    # --- 3. orcamento_linha (previsto) agrupado por natureza ---
    previsto_por_natureza: dict[str, float] = {}
    previsto_total = 0.0
    if orc_ids:
        linhas_prev = (
            client.table("orcamento_linha")
            .select("natureza,valor_previsto")
            .in_("orcamento_id", orc_ids)
            .execute()
            .data
        )
        for l in linhas_prev:
            v = float(l["valor_previsto"])
            previsto_por_natureza[l["natureza"]] = (
                previsto_por_natureza.get(l["natureza"], 0.0) + v
            )
            previsto_total += v

    # --- 4. Saídas do mês: transacao_bancaria DEBITO no intervalo ---
    # TRANSFERENCIA_INTERNA (SPM Bradesco↔Unicred + INVEST FACIL) é excluída:
    # saldo consolidado da empresa não muda, não é despesa real.
    # PAGAMENTO_INTRAGRUPO (SPM→FD) CONTA como saída: despesa operacional
    # com NFE; SPM contrata empresa do grupo pra fornecer serviço.
    txs = (
        client.table("transacao_bancaria")
        .select("valor,data_extrato,registro_pp_id,categoria")
        .eq("tipo", "DEBITO")
        .gte("data_extrato", d_ini)
        .lte("data_extrato", d_fim)
        .execute()
        .data
    )
    saidas_total = sum(
        abs(float(t["valor"])) for t in txs
        if t.get("categoria") != "TRANSFERENCIA_INTERNA"
    )

    # --- 5. Realizado por categoria via conciliacao_orcamento ↔ orcamento_linha (natureza) ---
    realizado_por_natureza: dict[str, float] = {}
    if orc_ids:
        linhas = (
            client.table("orcamento_linha")
            .select("id,natureza")
            .in_("orcamento_id", orc_ids)
            .execute()
            .data
        )
        linhas_map = {l["id"]: l["natureza"] for l in linhas}
        if linhas_map:
            concs = (
                client.table("conciliacao_orcamento")
                .select("orcamento_linha_id,valor_aplicado")
                .in_("orcamento_linha_id", list(linhas_map.keys()))
                .execute()
                .data
            )
            for c in concs:
                nat = linhas_map.get(c["orcamento_linha_id"])
                if nat:
                    realizado_por_natureza[nat] = (
                        realizado_por_natureza.get(nat, 0.0) + float(c["valor_aplicado"])
                    )

    # Adiciona linha "DESPESA_PROFISSIONAIS realizado" via PP
    # (transacoes com registro_pp_id — match automatico do motor de rodada)
    pp_realizado = sum(abs(float(t["valor"])) for t in txs if t.get("registro_pp_id"))
    if pp_realizado > 0:
        realizado_por_natureza["DESPESA_PROFISSIONAIS"] = (
            realizado_por_natureza.get("DESPESA_PROFISSIONAIS", 0.0) + pp_realizado
        )

    # --- 6. Previsto × Realizado (barras) ---
    todas_naturezas = set(previsto_por_natureza.keys()) | set(realizado_por_natureza.keys())
    barras: List[BarraPxR] = []
    for nat in sorted(todas_naturezas):
        prev = previsto_por_natureza.get(nat, 0.0)
        real = realizado_por_natureza.get(nat, 0.0)
        pct = (real / prev * 100.0) if prev > 0 else 0.0
        barras.append(BarraPxR(
            categoria=nat,
            previsto=round(prev, 2),
            realizado=round(real, 2),
            pct=round(pct, 2),
        ))

    # --- 7. KPIs (Track B: fix saldo_inicial hardcoded + saldo_atual = liquidez real) ---
    creditos_rows = (
        client.table("transacao_bancaria")
        .select("valor")
        .eq("tipo", "CREDITO")
        .gte("data_extrato", d_ini)
        .lte("data_extrato", d_fim)
        .execute()
        .data
    )
    entradas_do_mes = sum(float(t["valor"]) for t in creditos_rows)
    saidas_mes = saidas_total

    from backend.api.routers.saldos import get_liquidez_total
    saldo_atual = get_liquidez_total(client)

    kpis = KPIs(
        entradas_do_mes=round(entradas_do_mes, 2),
        saidas_mes=round(saidas_mes, 2),
        previsto_a_pagar=round(previsto_total, 2),
        saldo_atual=round(saldo_atual, 2),
    )

    # --- 8. Alertas ---
    alertas: List[Alerta] = []
    hoje = date.today().isoformat()
    cinco_dias_atras = (date.today() - timedelta(days=5)).isoformat()

    # 8a. Transações não conciliadas há > 5 dias
    nao_conc = (
        client.table("transacao_bancaria")
        .select("id")
        .eq("status_conciliacao", "NAO_CLASSIFICADO")
        .lte("data_extrato", cinco_dias_atras)
        .limit(1000)
        .execute()
        .data
    )
    if nao_conc:
        alertas.append(Alerta(
            tipo="NAO_CONCILIADO",
            mensagem=f"{len(nao_conc)} transações não conciliadas há mais de 5 dias",
            ref_id=None,
            ref_tipo=None,
        ))

    # 8b. Orcamento vencido sem pagamento (data_previsao < hoje e sem conciliacao)
    if orc_ids:
        linhas_venc = (
            client.table("orcamento_linha")
            .select("id,titular_razao_social,valor_previsto,data_previsao")
            .in_("orcamento_id", orc_ids)
            .not_.is_("data_previsao", "null")
            .lte("data_previsao", hoje)
            .execute()
            .data
        )
        if linhas_venc:
            ids_venc = [l["id"] for l in linhas_venc]
            pagas_rows = (
                client.table("conciliacao_orcamento")
                .select("orcamento_linha_id")
                .in_("orcamento_linha_id", ids_venc)
                .execute()
                .data
            )
            pagas = {c["orcamento_linha_id"] for c in pagas_rows}
            pendentes_vencidas = [l for l in linhas_venc if l["id"] not in pagas]
            if pendentes_vencidas:
                alertas.append(Alerta(
                    tipo="VENCIDO",
                    mensagem=f"{len(pendentes_vencidas)} linhas de orçamento vencidas sem pagamento",
                    ref_id=None,
                    ref_tipo=None,
                ))

    # 8c. Pago a maior (se sum conciliado > valor_previsto + tolerância)
    if orc_ids:
        all_linhas = (
            client.table("orcamento_linha")
            .select("id,valor_previsto")
            .in_("orcamento_id", orc_ids)
            .execute()
            .data
        )
        concs_por_linha: dict[str, float] = {}
        if all_linhas:
            ids = [l["id"] for l in all_linhas]
            for c in (
                client.table("conciliacao_orcamento")
                .select("orcamento_linha_id,valor_aplicado")
                .in_("orcamento_linha_id", ids)
                .execute()
                .data
            ):
                concs_por_linha[c["orcamento_linha_id"]] = (
                    concs_por_linha.get(c["orcamento_linha_id"], 0.0) + float(c["valor_aplicado"])
                )
        pago_a_maior = [
            l for l in all_linhas
            if concs_por_linha.get(l["id"], 0.0) > float(l["valor_previsto"]) + 0.01
        ]
        if pago_a_maior:
            alertas.append(Alerta(
                tipo="PAGO_A_MAIOR",
                mensagem=f"{len(pago_a_maior)} linhas pagas a maior",
                ref_id=None,
                ref_tipo=None,
            ))

    return DashboardResponse(
        competencia=competencia,
        empresa_filtro=empresa,
        kpis=kpis,
        saidas_por_natureza={k: round(v, 2) for k, v in realizado_por_natureza.items()},
        previsto_x_realizado=barras,
        alertas=alertas,
    )
