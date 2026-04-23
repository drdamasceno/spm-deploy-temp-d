"""Router /dashboard/receita-financeira — Track B Plano 02 Task 1.

Rendimento do mês / acumulado ano / rentabilidade vs CDI.
"""
from datetime import date
import calendar

from fastapi import APIRouter, Depends, Query

from backend.api.deps import get_current_user, get_supabase_authed
from backend.api.routers.saldos import get_liquidez_total
from backend.api.schemas.dashboard_v2 import ReceitaFinanceiraResponse


router = APIRouter(tags=["dashboard"])


# CDI mensal de referência (MVP — hardcode). Próxima iteração: tabela de config.
CDI_MES_PCT_DEFAULT = 0.83


@router.get("/dashboard/receita-financeira", response_model=ReceitaFinanceiraResponse)
def receita_financeira(
    competencia: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    current=Depends(get_current_user),
):
    """Rendimento financeiro no mês + acumulado ano + rentabilidade vs CDI."""
    client = get_supabase_authed(current["jwt"])
    y, m = [int(x) for x in competencia.split("-")]
    d_ini = date(y, m, 1)
    last_day = calendar.monthrange(y, m)[1]
    d_fim = date(y, m, last_day)
    d_ini_ano = date(y, 1, 1)
    hoje = date.today()
    d_fim_ano = hoje if hoje.year == y else date(y, 12, 31)

    # --- Rendimento do mês (transações RECEITA_FINANCEIRA no mês) ---
    tx_mes = (
        client.table("transacao_bancaria")
        .select("valor")
        .eq("tipo", "CREDITO")
        .eq("natureza_lancamento", "RECEITA_FINANCEIRA")
        .gte("data_extrato", d_ini.isoformat())
        .lte("data_extrato", d_fim.isoformat())
        .execute()
        .data
        or []
    )
    rendimento_mes = sum(float(t.get("valor") or 0) for t in tx_mes)

    # + rendimento das aplicações MANUAL (simplificação MVP: sem filtro temporal exato)
    apls = (
        client.table("aplicacao_financeira")
        .select("rendimento_ultima_atualizacao,rendimento_ultima_atualizacao_fonte")
        .eq("rendimento_ultima_atualizacao_fonte", "MANUAL")
        .execute()
        .data
        or []
    )
    rendimento_mes += sum(float(a.get("rendimento_ultima_atualizacao") or 0) for a in apls)

    # --- Acumulado ano (mesma query, intervalo ampliado) ---
    tx_ano = (
        client.table("transacao_bancaria")
        .select("valor")
        .eq("tipo", "CREDITO")
        .eq("natureza_lancamento", "RECEITA_FINANCEIRA")
        .gte("data_extrato", d_ini_ano.isoformat())
        .lte("data_extrato", d_fim_ano.isoformat())
        .execute()
        .data
        or []
    )
    acumulado_ano = sum(float(t.get("valor") or 0) for t in tx_ano)
    acumulado_ano += sum(float(a.get("rendimento_ultima_atualizacao") or 0) for a in apls)

    # --- Saldo médio do mês (média de saldo_caixa_diario.liquidez_total) ---
    snaps = (
        client.table("saldo_caixa_diario")
        .select("liquidez_total")
        .gte("data", d_ini.isoformat())
        .lte("data", d_fim.isoformat())
        .execute()
        .data
        or []
    )
    if snaps:
        valores = [float(s.get("liquidez_total") or 0) for s in snaps]
        saldo_medio = sum(valores) / len(valores) if valores else 0.0
    else:
        saldo_medio = get_liquidez_total(client)

    # --- Rentabilidade % e % CDI ---
    rentabilidade_pct = (rendimento_mes / saldo_medio * 100.0) if saldo_medio > 0 else 0.0
    cdi_mes_pct = CDI_MES_PCT_DEFAULT
    percent_cdi = (rentabilidade_pct / cdi_mes_pct * 100.0) if cdi_mes_pct > 0 else 0.0

    return ReceitaFinanceiraResponse(
        rendimento_mes=round(rendimento_mes, 2),
        acumulado_ano=round(acumulado_ano, 2),
        rentabilidade_pct=round(rentabilidade_pct, 2),
        cdi_mes_pct=round(cdi_mes_pct, 2),
        percent_cdi=round(percent_cdi, 2),
    )
