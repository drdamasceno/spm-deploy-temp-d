"""Router /dashboard/historico — Track B Plano 02 Task 1.

Agregados mensais (últimos N meses) para visão histórica.
"""
from datetime import date
import calendar

from fastapi import APIRouter, Depends, Query

from backend.api.deps import get_current_user, get_supabase_authed
from backend.api.schemas.dashboard_v2 import HistoricoResponse, MesHistorico


router = APIRouter(tags=["dashboard"])


def _competencia_anterior(competencia: str) -> str:
    y, m = [int(x) for x in competencia.split("-")]
    m -= 1
    if m == 0:
        m = 12
        y -= 1
    return f"{y:04d}-{m:02d}"


def _primeiro_ultimo_dia(competencia: str) -> tuple[str, str]:
    y, m = [int(x) for x in competencia.split("-")]
    last = calendar.monthrange(y, m)[1]
    return f"{competencia}-01", f"{competencia}-{last:02d}"


@router.get("/dashboard/historico", response_model=HistoricoResponse)
def historico(
    meses: int = Query(6, ge=1, le=24),
    current=Depends(get_current_user),
):
    """Para cada um dos últimos N meses (incluindo o atual), retorna MesHistorico."""
    client = get_supabase_authed(current["jwt"])

    hoje = date.today()
    competencia_atual = f"{hoje.year:04d}-{hoje.month:02d}"
    competencias: list[str] = []
    c = competencia_atual
    for _ in range(meses):
        competencias.append(c)
        c = _competencia_anterior(c)
    competencias.reverse()  # ordem cronológica ascendente

    resultado: list[MesHistorico] = []
    for comp in competencias:
        d_ini, d_fim = _primeiro_ultimo_dia(comp)

        # liquidez: último snapshot do mês
        snaps = (
            client.table("saldo_caixa_diario")
            .select("data,liquidez_total")
            .gte("data", d_ini)
            .lte("data", d_fim)
            .order("data", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        liquidez = float(snaps[0]["liquidez_total"]) if snaps else 0.0

        # faturamento: soma CREDITO no mês
        credits = (
            client.table("transacao_bancaria")
            .select("valor")
            .eq("tipo", "CREDITO")
            .gte("data_extrato", d_ini)
            .lte("data_extrato", d_fim)
            .execute()
            .data
            or []
        )
        faturamento = sum(float(t.get("valor") or 0) for t in credits)

        # DEBITOS no mês, agrupado por natureza_lancamento
        debits = (
            client.table("transacao_bancaria")
            .select("valor,natureza_lancamento")
            .eq("tipo", "DEBITO")
            .gte("data_extrato", d_ini)
            .lte("data_extrato", d_fim)
            .execute()
            .data
            or []
        )
        despesa_fixa = 0.0
        despesa_variavel = 0.0
        tributo = 0.0
        for t in debits:
            valor = abs(float(t.get("valor") or 0))
            nat = t.get("natureza_lancamento")
            if nat == "DESPESA_FIXA":
                despesa_fixa += valor
            elif nat in ("VALOR_VARIAVEL", "SALARIO_VARIAVEL"):
                despesa_variavel += valor
            elif nat == "TRIBUTO":
                tributo += valor

        # compromissos_abertos: saldo_pp de registro_pp ELEGIVEL em rodadas da competência
        compromissos_abertos = 0.0
        rodadas_rows = (
            client.table("rodada")
            .select("id")
            .contains("pp_competencias", [comp])
            .execute()
            .data
            or []
        )
        rodada_ids = [r["id"] for r in rodadas_rows]
        if rodada_ids:
            regs = (
                client.table("registro_pp")
                .select("saldo_pp")
                .eq("status_saldo", "ELEGIVEL")
                .in_("rodada_id", rodada_ids)
                .execute()
                .data
                or []
            )
            compromissos_abertos = sum(float(r.get("saldo_pp") or 0) for r in regs)

        resultado.append(MesHistorico(
            competencia=comp,
            liquidez=round(liquidez, 2),
            faturamento=round(faturamento, 2),
            despesa_fixa=round(despesa_fixa, 2),
            despesa_variavel=round(despesa_variavel, 2),
            tributo=round(tributo, 2),
            compromissos_abertos=round(compromissos_abertos, 2),
            recebiveis_atraso=0.0,  # placeholder: ver /dashboard/recebiveis
        ))

    return HistoricoResponse(meses=resultado)
