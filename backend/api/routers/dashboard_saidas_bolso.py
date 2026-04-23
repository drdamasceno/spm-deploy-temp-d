"""Router /dashboard/saidas-por-bolso — agrega saídas por bolso no mês.

Para cada transação bancária DEBITO no período:
- Se tem transacao_linha filhas, soma por bolso usando os valores das linhas
- Senão, considera tudo SPM_OPERACIONAL (fallback)

Ou seja: enquanto Hugo não fez split, transações ficam em SPM_OPERACIONAL.
Depois que Hugo divide, o valor é distribuído pelos bolsos corretos.
"""
import calendar
from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from backend.api.deps import get_current_user, get_supabase_authed


router = APIRouter(tags=["dashboard"])


class SaidasPorBolsoResponse(BaseModel):
    competencia: str
    total: float
    spm_operacional: float
    fd_via_spm: float
    hugo_pessoal: float
    investimento_hugo: float
    transacoes_count: int
    com_split_count: int


@router.get("/dashboard/saidas-por-bolso", response_model=SaidasPorBolsoResponse)
def saidas_por_bolso(
    competencia: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    current=Depends(get_current_user),
):
    client = get_supabase_authed(current["jwt"])
    y, m = [int(x) for x in competencia.split("-")]
    d_ini = date(y, m, 1).isoformat()
    d_fim = date(y, m, calendar.monthrange(y, m)[1]).isoformat()

    # Busca transações DEBITO do mês
    txs = (
        client.table("transacao_bancaria")
        .select("id,valor")
        .eq("tipo", "DEBITO")
        .gte("data_extrato", d_ini)
        .lte("data_extrato", d_fim)
        .execute()
        .data
        or []
    )
    tx_ids = [t["id"] for t in txs]
    if not tx_ids:
        return SaidasPorBolsoResponse(
            competencia=competencia,
            total=0.0,
            spm_operacional=0.0,
            fd_via_spm=0.0,
            hugo_pessoal=0.0,
            investimento_hugo=0.0,
            transacoes_count=0,
            com_split_count=0,
        )

    # Todas as transacao_linha das tx acima, agrupadas por tx_id
    splits = (
        client.table("transacao_linha")
        .select("transacao_bancaria_id,valor,bolso")
        .in_("transacao_bancaria_id", tx_ids)
        .execute()
        .data
        or []
    )
    splits_por_tx: dict[str, list[dict]] = {}
    for s in splits:
        splits_por_tx.setdefault(s["transacao_bancaria_id"], []).append(s)

    totais = {
        "SPM_OPERACIONAL": 0.0,
        "FD_VIA_SPM": 0.0,
        "HUGO_PESSOAL": 0.0,
        "INVESTIMENTO_HUGO": 0.0,
    }
    com_split = 0
    for tx in txs:
        tx_id = tx["id"]
        valor_abs = abs(float(tx["valor"]))
        if tx_id in splits_por_tx:
            com_split += 1
            for linha in splits_por_tx[tx_id]:
                b = linha["bolso"]
                if b in totais:
                    totais[b] += abs(float(linha["valor"]))
        else:
            totais["SPM_OPERACIONAL"] += valor_abs

    total = sum(totais.values())

    return SaidasPorBolsoResponse(
        competencia=competencia,
        total=round(total, 2),
        spm_operacional=round(totais["SPM_OPERACIONAL"], 2),
        fd_via_spm=round(totais["FD_VIA_SPM"], 2),
        hugo_pessoal=round(totais["HUGO_PESSOAL"], 2),
        investimento_hugo=round(totais["INVESTIMENTO_HUGO"], 2),
        transacoes_count=len(txs),
        com_split_count=com_split,
    )
