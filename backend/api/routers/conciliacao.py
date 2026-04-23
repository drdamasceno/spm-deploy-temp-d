"""Router /conciliacoes — sugestoes em cascata + aplicar + desfazer.

Endpoints:
  GET  /conciliacoes/sugestoes?orcamento_id=...&conta_id=...
  POST /conciliacoes
  DELETE /conciliacoes/{id}

Comportamento:
  - Sugestoes usam sugerir_cascata (3 camadas: REGRA -> SIMILARIDADE -> VALOR)
  - Aplicar conciliacao: insere linha, marca transacao como MATCH_AUTOMATICO,
    e se origem != REGRA, cria/atualiza regra_classificacao para o titular.
  - Deletar: remove conciliacao + volta transacao para NAO_CLASSIFICADO
    se nao sobrar outra conciliacao dela.

Divida tecnica — _carregar_contexto filtra as conciliacoes ja existentes
por orcamento_id via lookup das linhas do orcamento (evita trazer tudo do
DB; o plano original tinha select sem filtro, que nao escala).
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status

from backend.api.deps import get_current_user, get_supabase_authed
from backend.api.schemas.conciliacao import ConciliacaoCreate, SugestaoOut
from backend.src.classificador_conciliacao import (
    LinhaOrcamento,
    Regra,
    Transacao,
    eh_pagamento_intragrupo,
    eh_transferencia_interna,
    normalizar_titular,
    sugerir_cascata,
)


router = APIRouter(prefix="/conciliacoes", tags=["conciliacao"])


def _carregar_contexto(client, orcamento_id: UUID, conta_id: UUID | None):
    """Carrega linhas abertas do orcamento, transacoes NAO_CLASSIFICADO da conta, regras ativas.

    Linhas 'abertas' = valor_previsto - sum(conciliacao_orcamento.valor_aplicado) > 0.

    Importante: as somas de conciliacoes sao filtradas pelos IDs das linhas do
    orcamento atual (in_('orcamento_linha_id', [...])) para nao carregar
    conciliacoes de outros orcamentos do DB.
    """
    linhas = (
        client.table("orcamento_linha")
        .select("*")
        .eq("orcamento_id", str(orcamento_id))
        .execute()
        .data
    )
    linha_ids = [l["id"] for l in linhas]
    sums: dict[str, float] = {}
    if linha_ids:
        conc = (
            client.table("conciliacao_orcamento")
            .select("orcamento_linha_id,valor_aplicado")
            .in_("orcamento_linha_id", linha_ids)
            .execute()
            .data
        )
        for c in conc:
            key = c["orcamento_linha_id"]
            sums[key] = sums.get(key, 0.0) + float(c["valor_aplicado"])

    abertas: List[LinhaOrcamento] = []
    for l in linhas:
        aplicado = sums.get(l["id"], 0.0)
        saldo = float(l["valor_previsto"]) - aplicado
        if saldo > 0.005:
            abertas.append(LinhaOrcamento(
                id=l["id"],
                titular_razao_social=l["titular_razao_social"],
                valor_previsto=float(l["valor_previsto"]),
                saldo_pendente=saldo,
            ))

    q = (
        client.table("transacao_bancaria")
        .select("*")
        .eq("status_conciliacao", "NAO_CLASSIFICADO")
    )
    if conta_id:
        q = q.eq("conta_id", str(conta_id))
    txs_raw = q.execute().data

    # Heurística preventiva — 2 categorias distintas:
    #  1. TRANSFERENCIA_INTERNA — entre contas da própria SPM (Bradesco↔Unicred).
    #     Saldo consolidado não muda; filtrada do Dashboard.
    #  2. PAGAMENTO_INTRAGRUPO — SPM contrata empresa do grupo (ex: FD GESTAO)
    #     pra fornecer serviço. Despesa real com NFE; conta como saída no
    #     Dashboard. Fica fora do pool pra evitar match falso com prestador PP.
    # Ambas saem do pool de sugestões.
    ids_internas: list[str] = []
    ids_intragrupo: list[str] = []
    for t_raw in txs_raw:
        t_obj = Transacao(
            id=t_raw["id"],
            titular_pix=t_raw.get("titular_pix"),
            valor=float(t_raw["valor"]),
            data_movimento=str(t_raw["data_extrato"]),
            origem_banco=t_raw.get("origem_banco") or "BRADESCO",
        )
        if eh_transferencia_interna(t_obj):
            ids_internas.append(t_raw["id"])
        elif eh_pagamento_intragrupo(t_obj):
            ids_intragrupo.append(t_raw["id"])
    if ids_internas:
        (
            client.table("transacao_bancaria")
            .update({
                "status_conciliacao": "CONCILIADO_POR_CATEGORIA",
                "categoria": "TRANSFERENCIA_INTERNA",
            })
            .in_("id", ids_internas)
            .execute()
        )
    if ids_intragrupo:
        (
            client.table("transacao_bancaria")
            .update({
                "status_conciliacao": "CONCILIADO_POR_CATEGORIA",
                "categoria": "PAGAMENTO_INTRAGRUPO",
            })
            .in_("id", ids_intragrupo)
            .execute()
        )
    removidos = set(ids_internas) | set(ids_intragrupo)
    txs_raw = [t for t in txs_raw if t["id"] not in removidos]

    txs = [
        Transacao(
            id=t["id"],
            titular_pix=t.get("titular_pix"),
            valor=float(t["valor"]),
            data_movimento=str(t["data_extrato"]),
            origem_banco=t.get("origem_banco") or "BRADESCO",
        )
        for t in txs_raw
    ]

    regras_raw = (
        client.table("regra_classificacao").select("*").eq("ativa", True).execute().data
    )
    regras = [
        Regra(
            id=r["id"],
            titular_pix_padrao=r["titular_pix_padrao"],
            orcamento_linha_id=r.get("orcamento_linha_id"),
            confianca_base=float(r["confianca_base"]),
            ativa=r["ativa"],
        )
        for r in regras_raw
    ]

    return txs, abertas, regras


@router.get("/sugestoes", response_model=List[SugestaoOut])
def sugestoes(
    orcamento_id: UUID,
    conta_id: UUID | None = None,
    current=Depends(get_current_user),
):
    client = get_supabase_authed(current["jwt"])
    txs, abertas, regras = _carregar_contexto(client, orcamento_id, conta_id)
    out: List[SugestaoOut] = []
    for tx in txs:
        for s in sugerir_cascata(tx, abertas, regras):
            out.append(SugestaoOut(
                transacao_id=tx.id,
                orcamento_linha_id=s.orcamento_linha_id,
                confianca=s.confianca,
                origem=s.origem,
                valor_aplicado=s.valor_aplicado,
            ))
    return out


@router.post("/sugestoes/lookup")
def lookup_detalhes(
    payload: dict = Body(...),
    current=Depends(get_current_user),
):
    """Busca detalhes ricos para uma lista de transacao_ids + orcamento_linha_ids.

    Criado para viabilizar a UI de conciliacao (tela /conciliacao) que precisa
    mostrar titular, valor, data, razao social, natureza — dados que nao estao
    em SugestaoOut (que carrega apenas IDs). Evita N+1 queries no frontend.

    Body: {"transacao_ids": [...], "orcamento_linha_ids": [...]}
    """
    client = get_supabase_authed(current["jwt"])
    transacao_ids = payload.get("transacao_ids") or []
    orcamento_linha_ids = payload.get("orcamento_linha_ids") or []

    txs: list = []
    linhas: list = []
    if transacao_ids:
        txs = (
            client.table("transacao_bancaria")
            .select("id,titular_pix,valor,data_extrato,origem_banco")
            .in_("id", [str(t) for t in transacao_ids])
            .execute()
            .data
        )
    if orcamento_linha_ids:
        linhas = (
            client.table("orcamento_linha")
            .select("id,titular_razao_social,valor_previsto,natureza,observacao")
            .in_("id", [str(l) for l in orcamento_linha_ids])
            .execute()
            .data
        )
    return {"transacoes": txs, "orcamento_linhas": linhas}


@router.post("", response_model=ConciliacaoCreate, status_code=status.HTTP_201_CREATED)
def criar_conciliacao(payload: ConciliacaoCreate, current=Depends(get_current_user)):
    client = get_supabase_authed(current["jwt"])
    # 1. Insere conciliacao
    ins = client.table("conciliacao_orcamento").insert({
        "transacao_id": str(payload.transacao_id),
        "orcamento_linha_id": str(payload.orcamento_linha_id),
        "valor_aplicado": payload.valor_aplicado,
        "confianca": payload.confianca,
        "origem": payload.origem,
        "aprovada_por": current["id"],
    }).execute()
    if not ins.data:
        raise HTTPException(400, detail={"error": "Falha ao criar conciliacao"})

    # 2. Atualiza transacao_bancaria (MATCH_AUTOMATICO para todas as origens
    #    automaticas/manuais — o schema conhece MATCH_AUTOMATICO | FRACIONADO |
    #    CONCILIADO_POR_CATEGORIA | MANUAL_PENDENTE | NAO_CLASSIFICADO)
    client.table("transacao_bancaria").update({
        "status_conciliacao": "MATCH_AUTOMATICO",
    }).eq("id", str(payload.transacao_id)).execute()

    # 3. Se nao veio de regra, cria/atualiza regra_classificacao para o futuro
    if payload.origem != "REGRA":
        tx_rows = (
            client.table("transacao_bancaria")
            .select("titular_pix")
            .eq("id", str(payload.transacao_id))
            .limit(1)
            .execute()
            .data
        )
        tx = tx_rows[0] if tx_rows else None
        if tx and tx.get("titular_pix"):
            titular_norm = normalizar_titular(tx["titular_pix"])
            if titular_norm:
                # desativa regra existente com mesmo titular (se houver) e cria nova
                client.table("regra_classificacao").update({"ativa": False}).eq(
                    "titular_pix_padrao", titular_norm
                ).eq("ativa", True).execute()
                client.table("regra_classificacao").insert({
                    "titular_pix_padrao": titular_norm,
                    "orcamento_linha_id": str(payload.orcamento_linha_id),
                    "confianca_base": 0.95,
                    "ativa": True,
                    "criada_por": current["id"],
                }).execute()

    return payload


@router.get("/intragrupo/pendentes")
def listar_intragrupo_pendentes(current=Depends(get_current_user)):
    """Lista transações categoria=PAGAMENTO_INTRAGRUPO que ainda não foram
    conciliadas em lote (sem conciliacao_orcamento associada).
    """
    client = get_supabase_authed(current["jwt"])
    txs = (
        client.table("transacao_bancaria")
        .select("id,valor,titular_pix,data_extrato,descricao,status_conciliacao,categoria")
        .eq("categoria", "PAGAMENTO_INTRAGRUPO")
        .order("data_extrato", desc=True)
        .execute()
        .data
        or []
    )
    if not txs:
        return {"transacoes": []}
    ids = [t["id"] for t in txs]
    ja_conciliadas = (
        client.table("conciliacao_orcamento")
        .select("transacao_id")
        .in_("transacao_id", ids)
        .execute()
        .data
        or []
    )
    conc_ids = {c["transacao_id"] for c in ja_conciliadas}
    pendentes = [t for t in txs if t["id"] not in conc_ids]
    return {"transacoes": pendentes}


@router.post("/intragrupo/{transacao_id}")
def conciliar_intragrupo_em_lote(
    transacao_id: UUID,
    current=Depends(get_current_user),
):
    """Concilia um PIX PAGAMENTO_INTRAGRUPO (ex: SPM→FD) em lote, consumindo
    linhas de orçamento com empresa_pagadora_id da empresa destino em FIFO por
    competência.

    Regras (Track B Fase E):
    - Transação precisa ter categoria=PAGAMENTO_INTRAGRUPO
    - Resolve empresa destino via titular_pix da transação (match contra empresa.razao_social)
    - Lista orcamento_linha WHERE empresa_pagadora_id = <empresa_destino>
      ordenadas por (orcamento.competencia ASC, data_previsao ASC NULLS LAST)
      com saldo pendente > 0
    - Consome FIFO até esgotar o valor do PIX
    - Resíduo (se PIX > soma das linhas) não vira conciliação — fica reportado
      como 'nao_consumido' no retorno (Hugo decide se lança como adiantamento)
    - Déficit (se PIX < soma das linhas) deixa linhas remanescentes em aberto

    Retorna: {
      conciliadas: [{orcamento_linha_id, valor_aplicado}],
      valor_total_tx, valor_consumido, residuo_nao_consumido, linhas_restantes_em_aberto
    }
    """
    client = get_supabase_authed(current["jwt"])

    # 1. Carrega transação + valida que é PAGAMENTO_INTRAGRUPO
    tx_rows = (
        client.table("transacao_bancaria")
        .select("id,valor,titular_pix,categoria,status_conciliacao")
        .eq("id", str(transacao_id))
        .limit(1)
        .execute()
        .data
    )
    if not tx_rows:
        raise HTTPException(404, detail={"error": "Transação não encontrada"})
    tx = tx_rows[0]
    if tx.get("categoria") != "PAGAMENTO_INTRAGRUPO":
        raise HTTPException(
            400,
            detail={
                "error": "Transação não é PAGAMENTO_INTRAGRUPO",
                "categoria_atual": tx.get("categoria"),
            },
        )
    valor_tx = abs(float(tx["valor"]))

    # 2. Resolve empresa destino via razão social no titular_pix
    titular = (tx.get("titular_pix") or "").upper()
    empresas = client.table("empresa").select("id,codigo,razao_social").execute().data or []
    empresa_destino_id = None
    for e in empresas:
        if (e.get("razao_social") or "").upper() in titular or (e.get("codigo") or "").upper() in titular:
            empresa_destino_id = e["id"]
            break
    if not empresa_destino_id:
        raise HTTPException(
            400,
            detail={"error": f"Não achei empresa do grupo no titular '{titular}'"},
        )

    # 3. Lista orcamento_linha com empresa_pagadora=<empresa_destino>,
    #    ordenadas por competência do orçamento ASC e data_previsao ASC
    linhas_raw = (
        client.table("orcamento_linha")
        .select("id,valor_previsto,data_previsao,titular_razao_social,orcamento_id,orcamento!inner(competencia)")
        .eq("empresa_pagadora_id", str(empresa_destino_id))
        .execute()
        .data
        or []
    )
    # Ordena por (competencia ASC, data_previsao ASC nulls last)
    def _chave_fifo(l):
        comp = (l.get("orcamento") or {}).get("competencia") or "9999-99"
        dt = l.get("data_previsao") or "9999-12-31"
        return (comp, dt)

    linhas_raw.sort(key=_chave_fifo)

    # 4. Filtra linhas com saldo pendente > 0 (subtrai conciliações já aplicadas)
    ids_linhas = [l["id"] for l in linhas_raw]
    conc_existentes = []
    if ids_linhas:
        conc_existentes = (
            client.table("conciliacao_orcamento")
            .select("orcamento_linha_id,valor_aplicado")
            .in_("orcamento_linha_id", ids_linhas)
            .execute()
            .data
            or []
        )
    ja_aplicado: dict = {}
    for c in conc_existentes:
        ja_aplicado[c["orcamento_linha_id"]] = ja_aplicado.get(c["orcamento_linha_id"], 0.0) + float(c["valor_aplicado"])

    # 5. Consome FIFO
    saldo_restante = valor_tx
    conciliadas: list = []
    remanescentes_em_aberto = 0
    for l in linhas_raw:
        if saldo_restante <= 0.005:
            # Tx esgotou mas ainda há linhas — contabiliza para reporte
            saldo_linha = float(l["valor_previsto"]) - ja_aplicado.get(l["id"], 0.0)
            if saldo_linha > 0.005:
                remanescentes_em_aberto += 1
            continue
        saldo_linha = float(l["valor_previsto"]) - ja_aplicado.get(l["id"], 0.0)
        if saldo_linha <= 0.005:
            continue
        aplicar = min(saldo_linha, saldo_restante)
        client.table("conciliacao_orcamento").insert({
            "transacao_id": str(transacao_id),
            "orcamento_linha_id": l["id"],
            "valor_aplicado": round(aplicar, 2),
            "confianca": 1.0,
            "origem": "MANUAL",
            "aprovada_por": current["id"],
        }).execute()
        conciliadas.append({
            "orcamento_linha_id": l["id"],
            "titular_razao_social": l.get("titular_razao_social"),
            "valor_aplicado": round(aplicar, 2),
        })
        saldo_restante -= aplicar

    # 6. Atualiza status da transação
    if conciliadas:
        client.table("transacao_bancaria").update({
            "status_conciliacao": "MATCH_AUTOMATICO",
        }).eq("id", str(transacao_id)).execute()

    return {
        "transacao_id": str(transacao_id),
        "empresa_destino_id": empresa_destino_id,
        "valor_total_tx": round(valor_tx, 2),
        "valor_consumido": round(valor_tx - saldo_restante, 2),
        "residuo_nao_consumido": round(max(saldo_restante, 0.0), 2),
        "conciliadas": conciliadas,
        "linhas_remanescentes_em_aberto": remanescentes_em_aberto,
    }


@router.delete("/{conciliacao_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar(conciliacao_id: UUID, current=Depends(get_current_user)):
    """Desfaz uma conciliacao e volta a transacao para NAO_CLASSIFICADO (se for a
    unica conciliacao daquela transacao).

    Usa .limit(1).execute() em vez de .single() porque supabase-py 2.x levanta
    APIError (PGRST116) quando a linha nao existe — queremos idempotencia.
    """
    client = get_supabase_authed(current["jwt"])
    rows = (
        client.table("conciliacao_orcamento")
        .select("transacao_id")
        .eq("id", str(conciliacao_id))
        .limit(1)
        .execute()
        .data
    )
    if rows:
        c = rows[0]
        client.table("conciliacao_orcamento").delete().eq("id", str(conciliacao_id)).execute()
        outras = (
            client.table("conciliacao_orcamento")
            .select("id")
            .eq("transacao_id", c["transacao_id"])
            .execute()
            .data
        )
        if not outras:
            client.table("transacao_bancaria").update({
                "status_conciliacao": "NAO_CLASSIFICADO",
            }).eq("id", c["transacao_id"]).execute()
    return None
