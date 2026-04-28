"""Router /dashboard/compromissos e /dashboard/recebiveis — Track B Plano 02 Task 1."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends

from backend.api.deps import get_current_user, get_supabase_authed
from backend.api.schemas.dashboard_v2 import (
    CompromissoItem,
    CompromissosResponse,
    RecebiveisResponse,
)


router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/compromissos", response_model=CompromissosResponse)
def compromissos(current=Depends(get_current_user)):
    """Agrega compromissos a pagar: saldos de PP elegiveis + faturas previstas (30 dias).

    PP: aplica filtro por rodada mais recente (por chave contrato/comp/prestador)
    para nao somar registros duplicados quando PP foi re-importado.
    """
    from backend.api.routers.contratos_competencia import (
        _created_at_por_rodada,
        _filtrar_pela_rodada_mais_recente,
    )

    client = get_supabase_authed(current["jwt"])

    itens: list[CompromissoItem] = []
    soma_pp = 0.0
    soma_faturas = 0.0

    pp_rows = (
        client.table("registro_pp")
        .select("id,nome_prestador,saldo_pp,contrato_id,mes_competencia,prestador_id,rodada_id")
        .eq("status_saldo", "ELEGIVEL")
        .execute()
        .data
        or []
    )
    if pp_rows:
        rodada_ids = list({r["rodada_id"] for r in pp_rows if r.get("rodada_id")})
        created_at_lookup = _created_at_por_rodada(client, rodada_ids)
        pp_rows = _filtrar_pela_rodada_mais_recente(pp_rows, created_at_lookup)

    for r in pp_rows:
        valor = float(r.get("saldo_pp") or 0)
        if valor <= 0:
            continue
        soma_pp += valor
        itens.append(CompromissoItem(
            fonte="PP",
            descricao=r.get("nome_prestador") or "(sem nome)",
            valor=round(valor, 2),
            vencimento=None,
        ))

    hoje = date.today()
    limite = (hoje + timedelta(days=30)).isoformat()
    linhas = (
        client.table("orcamento_linha")
        .select("id,titular_razao_social,valor_previsto,data_previsao")
        .not_.is_("data_previsao", "null")
        .lte("data_previsao", limite)
        .execute()
        .data
        or []
    )
    if linhas:
        ids = [l["id"] for l in linhas]
        concs = (
            client.table("conciliacao_orcamento")
            .select("orcamento_linha_id,valor_aplicado")
            .in_("orcamento_linha_id", ids)
            .execute()
            .data
            or []
        )
        pago_por_linha: dict[str, float] = {}
        for c in concs:
            lid = c["orcamento_linha_id"]
            pago_por_linha[lid] = pago_por_linha.get(lid, 0.0) + float(c.get("valor_aplicado") or 0)

        for l in linhas:
            previsto = float(l.get("valor_previsto") or 0)
            pago = pago_por_linha.get(l["id"], 0.0)
            saldo = previsto - pago
            if saldo <= 0.01:
                continue
            soma_faturas += saldo
            itens.append(CompromissoItem(
                fonte="FATURA",
                descricao=l.get("titular_razao_social") or "(sem titular)",
                valor=round(saldo, 2),
                vencimento=l.get("data_previsao"),
            ))

    itens.sort(key=lambda x: x.valor, reverse=True)
    itens_top = itens[:50]

    return CompromissosResponse(
        total=round(soma_pp + soma_faturas, 2),
        por_fonte={
            "PP": round(soma_pp, 2),
            "FATURAS": round(soma_faturas, 2),
        },
        itens=itens_top,
    )


@router.get("/dashboard/recebiveis", response_model=RecebiveisResponse)
def recebiveis(current=Depends(get_current_user)):
    """Placeholder seguro.

    Aguarda orçamento de entradas (Plano 04+). Por enquanto retorna vazio
    para o frontend não quebrar.
    """
    # Mantém dependência de autenticação (respeita padrão do app)
    _ = current
    return RecebiveisResponse(
        total=0.0,
        por_aging={},
        itens=[],
    )
