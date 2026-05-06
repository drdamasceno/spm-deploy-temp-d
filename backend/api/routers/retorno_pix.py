"""Router /retornos-pix — ingestão de arquivos CNAB-240 retorno PIX e
matching determinístico contra registro_pp.

Substitui (no caminho de exibição) a heurística extrato↔PP que produzia
falsos positivos cross-prestador (ex: Henrique Storino ↔ Eduarda Vitor).

Fluxo:
  POST /retornos-pix    upload do arquivo .RET → parser → matcher → bulk insert
  GET  /retornos-pix    lista os pagamentos importados (com filtros)

O matching prioriza:
  1. DOC_EXATO   — prestador.cpf_cnpj == retorno.documento + valor exato +
                    registro_pp em aberto na competência ativa.
  2. CHAVE_PIX   — prestador.chave_pix == retorno.chave_pix_literal + valor.
  3. NOME_VALOR  — fallback fraco (apenas se documento ausente no PP).
"""
from __future__ import annotations

import hashlib
import re
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.api.deps import get_current_user, get_supabase_authed
from backend.src.retorno_pix_cnab import parse_retorno_pix, PagamentoPIX


router = APIRouter(prefix="/retornos-pix", tags=["retorno_pix"])


_OCORRENCIA_PARA_STATUS = {
    "00000": "CONFIRMADO",
    "00005": "CONFIRMADO",  # observado em todas as 58 linhas da remessa 30/04
    # Códigos de rejeição/estorno serão adicionados conforme aparecerem em prod.
}


def _normalize_doc(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def _ocorrencia_para_status(codigo: str) -> str:
    return _OCORRENCIA_PARA_STATUS.get(codigo, "OUTRO")


def _matchear(client, p: PagamentoPIX) -> tuple[Optional[str], Optional[str]]:
    """Tenta achar registro_pp em aberto para este pagamento.

    Retorna (registro_pp_id, match_confianca) ou (None, None).

    Estratégia DOC_EXATO:
      - Busca prestador por cpf_cnpj == p.documento_normalizado.
      - Lista registros_pp do prestador onde saldo_pp ≈ valor_efetivado E
        ainda não tem retorno_pix associado (saldo de retorno = 0).
      - Se exatamente 1 → match.
    """
    if not p.documento_normalizado:
        return None, None

    # 1) prestador por documento
    prestadores = (
        client.table("prestador")
        .select("id")
        .eq("cpf_cnpj", p.documento_normalizado)
        .execute()
        .data
        or []
    )
    if not prestadores:
        return None, None

    prestador_ids = [pr["id"] for pr in prestadores]

    # 2) registros_pp candidatos (saldo ≈ valor + sem retorno_pix associado já)
    rpps = (
        client.table("registro_pp")
        .select("id,saldo_pp,mes_competencia,contrato_id")
        .in_("prestador_id", prestador_ids)
        .execute()
        .data
        or []
    )

    valor = float(p.valor_efetivado)
    candidatos = [r for r in rpps if abs(float(r["saldo_pp"]) - valor) <= 0.01]
    if len(candidatos) == 1:
        return candidatos[0]["id"], "DOC_EXATO"

    # ambíguo (mais de um match) ou zero — operador resolve manualmente
    return None, None


@router.post("")
async def upload_retorno_pix(
    arquivo: UploadFile = File(...),
    conta_id: Optional[str] = None,
    current=Depends(get_current_user),
):
    """Recebe .RET CNAB-240 retorno PIX, parseia, faz matching determinístico
    contra registro_pp, e persiste em retorno_pix.

    Idempotente por (arquivo_hash, nosso_numero) — re-upload do mesmo arquivo
    não duplica linhas.
    """
    raw = await arquivo.read()
    if not raw:
        raise HTTPException(400, detail={"error": "Arquivo vazio"})

    arquivo_hash = hashlib.sha256(raw).hexdigest()

    try:
        parsed = parse_retorno_pix(raw)
    except Exception as e:
        raise HTTPException(400, detail={"error": f"Falha ao parsear: {e}"})

    if not parsed.pagamentos:
        raise HTTPException(400, detail={"error": "Nenhum pagamento PIX encontrado no arquivo"})

    client = get_supabase_authed(current["jwt"])

    # Pre-fetch existentes pra dedup (evita conflict explicito por sequência)
    existentes = (
        client.table("retorno_pix")
        .select("nosso_numero")
        .eq("arquivo_hash", arquivo_hash)
        .execute()
        .data
        or []
    )
    nossos_existentes = {e["nosso_numero"] for e in existentes if e.get("nosso_numero")}

    rows = []
    pulados_dedup = 0
    matched = 0
    for p in parsed.pagamentos:
        if p.nosso_numero in nossos_existentes:
            pulados_dedup += 1
            continue
        rpp_id, conf = _matchear(client, p)
        if rpp_id:
            matched += 1
        rows.append({
            "banco": p.banco,
            "conta_id": conta_id,
            "arquivo_origem": arquivo.filename,
            "arquivo_hash": arquivo_hash,
            "importado_por": current.get("user_id"),
            "seq_lote": p.seq,
            "nosso_numero": p.nosso_numero,
            "id_documento_empresa": p.id_documento_empresa,
            "nome_favorecido": p.nome_favorecido,
            "documento": p.documento_normalizado,
            "tipo_pessoa": p.tipo_pessoa,
            "tipo_chave_pix": p.tipo_chave_pix,
            "chave_pix_literal": p.chave_pix_literal,
            "valor_instruido": float(p.valor_instr),
            "valor_efetivado": float(p.valor_efet),
            "data_pagamento": p.data_pgto,
            "ocorrencia_codigo": p.ocorrencia,
            "status": _ocorrencia_para_status(p.ocorrencia),
            "registro_pp_id": rpp_id,
            "match_confianca": conf,
            "matched_em": "now()" if rpp_id else None,
        })

    inserted = 0
    if rows:
        # batch inserts em chunks de 100
        for i in range(0, len(rows), 100):
            chunk = rows[i:i + 100]
            r = client.table("retorno_pix").insert(chunk).execute()
            inserted += len(r.data or [])

    return {
        "arquivo": arquivo.filename,
        "arquivo_hash": arquivo_hash,
        "total_pagamentos_arquivo": len(parsed.pagamentos),
        "inseridos": inserted,
        "pulados_dedup": pulados_dedup,
        "matched_automaticamente": matched,
        "valor_total_efetivado": float(parsed.total_efet()),
        "metadados": {
            "banco": parsed.metadados.banco,
            "qtd_lotes": parsed.metadados.qtd_lotes,
            "qtd_registros": parsed.metadados.qtd_registros,
        },
    }


@router.get("")
def listar_retornos(
    documento: Optional[str] = None,
    matched: Optional[bool] = None,
    current=Depends(get_current_user),
):
    """Lista linhas de retorno_pix com filtros opcionais."""
    client = get_supabase_authed(current["jwt"])
    q = client.table("retorno_pix").select("*").order("data_pagamento", desc=True).limit(500)
    if documento:
        q = q.eq("documento", _normalize_doc(documento))
    if matched is True:
        q = q.not_.is_("registro_pp_id", "null")
    elif matched is False:
        q = q.is_("registro_pp_id", "null")
    return q.execute().data or []
