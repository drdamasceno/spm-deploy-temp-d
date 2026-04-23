"""Router /dashboard/evolucao-caixa — Track B Plano 02 Task 1.

Abertura do mês + hoje + variação + sparkline diária.

Usa saldo_caixa_diario quando disponível (populado pelo worker da Fase F).
Fallback enquanto o worker não existe: abertura=hoje=liquidez_total atual,
sparkline=[liquidez_total]. Ainda útil: usuário vê valor atual confiável.
"""
from datetime import date
import calendar

from fastapi import APIRouter, Depends, Query

from backend.api.deps import get_current_user, get_supabase_authed
from backend.api.routers.saldos import get_liquidez_total
from backend.api.schemas.dashboard_v2 import EvolucaoCaixaResponse


router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/evolucao-caixa", response_model=EvolucaoCaixaResponse)
def evolucao_caixa(
    competencia: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    current=Depends(get_current_user),
):
    """Abertura do mês + hoje + variação + sparkline diária."""
    client = get_supabase_authed(current["jwt"])
    y, m = [int(x) for x in competencia.split("-")]
    d_ini = date(y, m, 1)
    last_day = calendar.monthrange(y, m)[1]
    d_fim = date(y, m, last_day)
    hoje = date.today()
    d_hoje = hoje if d_ini <= hoje <= d_fim else d_fim

    snaps = (
        client.table("saldo_caixa_diario")
        .select("data,liquidez_total")
        .gte("data", d_ini.isoformat())
        .lte("data", d_hoje.isoformat())
        .order("data")
        .execute()
        .data
        or []
    )

    if snaps:
        por_data = {s["data"]: float(s["liquidez_total"]) for s in snaps}
        liquidez_atual = float(snaps[-1]["liquidez_total"])
        abertura_valor = float(snaps[0]["liquidez_total"])
        abertura_data_str = snaps[0]["data"]
        hoje_data_str = snaps[-1]["data"]
        sparkline = [por_data[k] for k in sorted(por_data.keys())]
    else:
        liquidez_atual = get_liquidez_total(client)
        abertura_valor = liquidez_atual
        abertura_data_str = d_ini.isoformat()
        hoje_data_str = d_hoje.isoformat()
        sparkline = [liquidez_atual]

    variacao_valor = liquidez_atual - abertura_valor
    variacao_pct = (variacao_valor / abertura_valor * 100.0) if abertura_valor else 0.0

    return EvolucaoCaixaResponse(
        abertura_data=abertura_data_str,
        abertura_valor=round(abertura_valor, 2),
        hoje_data=hoje_data_str,
        hoje_valor=round(liquidez_atual, 2),
        variacao_valor=round(variacao_valor, 2),
        variacao_pct=round(variacao_pct, 2),
        sparkline=[round(v, 2) for v in sparkline],
    )
