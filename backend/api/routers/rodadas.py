from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import date
from io import BytesIO
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from supabase import Client

from backend.api.deps import get_current_user, get_supabase_authed, require_ceo_with_2fa
from backend.api.schemas.rodada import ExtratoPeriodo, RodadaListItem, UploadRodadaResponse
from backend.api.schemas.rodada_snapshot import AprovarRodadaRequest, RodadaSnapshotResponse
from backend.api.schemas.resultado import (
    ConciliarResponse,
    Pagination,
    RegistroPPNested,
    ResultadoResponse,
    ResumoRegistrosPP,
    ResumoTransacoes,
    TransacaoResultado,
)
from backend.api.storage import BUCKET_RODADAS, upload_to_supabase_storage
from backend.src import conciliacao_spm, extrato_bradesco, pega_plantao


router = APIRouter()


# Pattern de rodada-teste (fixture em backend/tests/conftest.py — rodada_nao_aprovada):
#   periodo_extrato_inicio = '2026-01-01'
#   periodo_extrato_fim    = '2026-01-31'
#   pp_competencias        = ['2026-01']
# Trigger trg_bloqueia_delete_rodada_aprovada impede teardown de deletar rodadas
# aprovadas durante os testes T6-T11, entao acumula-se lixo no DB. Filtramos aqui
# por padrao; passe ?incluir_teste=true para diagnostico.
_RODADA_TESTE_INICIO = "2026-01-01"
_RODADA_TESTE_FIM = "2026-01-31"
_RODADA_TESTE_COMPETENCIAS = ["2026-01"]


def _eh_rodada_teste(r: dict) -> bool:
    return (
        str(r.get("periodo_extrato_inicio") or "") == _RODADA_TESTE_INICIO
        and str(r.get("periodo_extrato_fim") or "") == _RODADA_TESTE_FIM
        and (r.get("pp_competencias") or []) == _RODADA_TESTE_COMPETENCIAS
    )


@router.get("", response_model=List[RodadaListItem])
def listar_rodadas(
    incluir_teste: bool = Query(
        False,
        description="Inclui rodadas-teste (fixture conftest) residuais no DB. Default False.",
    ),
    current=Depends(get_current_user),
):
    """
    GET /rodadas

    Lista todas as rodadas acessiveis pelo usuario autenticado, ordenadas
    por criado_em DESC. Respeita RLS (policy rodada_select exige
    auth.uid() IS NOT NULL — qualquer autenticado enxerga todas).

    Sem paginacao em v1 (volume esperado baixo). Adicionar se crescer.

    Filtro padrao: esconde rodadas-teste (fixture pytest Bloco D) que
    acumulam por causa do trigger trg_bloqueia_delete_rodada_aprovada.
    """
    client = get_supabase_authed(current["jwt"])
    resp = (
        client.table("rodada")
        .select(
            "id, periodo_extrato_inicio, periodo_extrato_fim, "
            "pp_competencias, status, criado_em, criado_por"
        )
        .order("criado_em", desc=True)
        .execute()
    )
    rows = resp.data or []
    if not incluir_teste:
        rows = [r for r in rows if not _eh_rodada_teste(r)]
    return [
        RodadaListItem(
            id=r["id"],
            periodo_extrato_inicio=str(r.get("periodo_extrato_inicio") or ""),
            periodo_extrato_fim=str(r.get("periodo_extrato_fim") or ""),
            pp_competencias=r.get("pp_competencias") or [],
            status=r.get("status") or "CRIADA",
            criado_em=str(r.get("criado_em") or ""),
            criado_por=r.get("criado_por"),
        )
        for r in rows
    ]

# Divida tecnica — v1 aceita apenas extratos da conta Bradesco Remessas.
# UUID hardcoded aqui pelo mesmo motivo do seed Passo 2 (unica conta cadastrada).
# Fase 2 expoe parametro conta_id no payload de upload.
CONTA_BRADESCO_REMESSAS_ID = "69d80fb1-b166-4c17-b666-ae60d50fab59"

COMPETENCIA_REGEX = re.compile(r"^\d{4}-\d{2}$")


def _mm_yyyy_to_yyyy_mm(mes: str) -> str:
    """Converte 'MM/YYYY' do parser PP para 'YYYY-MM' do schema."""
    if not mes:
        return ""
    if "/" in mes:
        mm, yyyy = mes.split("/", 1)
        if yyyy.isdigit() and mm.isdigit():
            return f"{yyyy}-{mm.zfill(2)}"
    return mes


def _status_saldo(saldo: float) -> str:
    if saldo == 0:
        return "SEM_MOVIMENTO"
    if saldo < 0:
        return "SALDO_NEGATIVO"
    return "ELEGIVEL"


def _tipo_chave_pix(chave: str) -> str:
    chave = (chave or "").strip()
    if not chave:
        return "ALEATORIA"
    if "@" in chave:
        return "EMAIL"
    if any(c in chave for c in "()-+") and any(c.isdigit() for c in chave):
        return "TELEFONE"
    return "ALEATORIA"


def _ensure_prestador(client: Client, pp_record: dict) -> str:
    """
    Retorna o id do prestador correspondente ao registro PP.
    Cria se nao existir (match por lower(nome) exato).

    Divida tecnica — auto-create deixa prestador com cpf_cnpj_validado=false
    quando o parser nao traz CPF/CNPJ real. Hugo valida via UI no Passo 5.
    """
    nome = (pp_record.get("nome_prestador") or "").strip()
    if not nome:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "registro de PP sem nome_prestador"},
        )

    existing = (
        client.table("prestador")
        .select("id")
        .ilike("nome", nome)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]["id"]

    tipo_doc_raw = (pp_record.get("tipo_doc") or "").upper().strip()
    tipo_doc = tipo_doc_raw if tipo_doc_raw in ("CPF", "CNPJ") else "CPF"
    documento = (pp_record.get("documento") or "").strip()
    chave_pix = (pp_record.get("chave_pix") or "").strip()

    if documento and tipo_doc_raw in ("CPF", "CNPJ"):
        cpf_cnpj = documento
        cpf_cnpj_validado = True
    else:
        tipo_chave = _tipo_chave_pix(chave_pix)
        cpf_cnpj = f"PENDENTE:PIX_{tipo_chave}:{chave_pix or nome}"
        cpf_cnpj_validado = False

    payload = {
        "nome": nome,
        "ficticio": False,
        "tipo_doc": tipo_doc,
        "cpf_cnpj": cpf_cnpj,
        "cpf_cnpj_validado": cpf_cnpj_validado,
        "razao_social_pj": (pp_record.get("razao_social_pj") or None) or None,
        "chave_pix": chave_pix or None,
        "registro_profissional": (pp_record.get("crm") or None) or None,
        "uf": (pp_record.get("uf") or None) or None,
    }
    inserted = client.table("prestador").insert(payload).execute()
    if not inserted.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"falha ao criar prestador {nome!r}"},
        )
    return inserted.data[0]["id"]


def _normaliza_cidade(s: str) -> str:
    """Remove acentos + upper pra matching. Preserva grafia no display."""
    import unicodedata
    nfkd = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in nfkd if not unicodedata.combining(c)).upper()


def _parse_local_pp(local: str) -> tuple[str, str, str | None]:
    """
    Extrai (uf, cidade, local_sub) de 'UF - CIDADE - LOCAL - SUB - ...'.

    - Normaliza separador `–` (traço longo) → `-`.
    - uf: upper, 2 chars.
    - cidade: upper (preserva acentos).
    - local_sub: tudo após "UF - CIDADE - ", ou None se não houver.

    Raises ValueError se string vazia ou sem cidade.
    """
    import re
    local = (local or "").strip()
    if not local:
        raise ValueError("Local vazio")
    normalized = re.sub(r'–', '-', local)
    parts = [p.strip() for p in normalized.split(' - ')]
    if len(parts) < 2:
        raise ValueError(f"Local não tem UF e cidade separados por ' - ': {local!r}")
    uf = parts[0].upper()
    cidade = parts[1].upper()
    local_sub = ' - '.join(parts[2:]) if len(parts) > 2 else None
    return uf, cidade, local_sub


def _contrato_display(contrato: dict | None, local_sub: str | None) -> str:
    """Reconstrói 'UF - CIDADE - LOCAL' para exibição/relatórios a partir
    do contrato e do local_pp do registro_pp."""
    if not contrato:
        return ""
    uf = contrato.get("uf") or ""
    cidade = contrato.get("cidade") or ""
    base = f"{uf} - {cidade}" if uf and cidade else (contrato.get("nome") or "")
    if local_sub:
        return f"{base} - {local_sub}"
    return base


def _ensure_contrato(client: Client, local_pp: str | None) -> tuple[str, str | None]:
    """
    Garante que existe contrato para o (uf, cidade) derivados de `local_pp`.
    Retorna (contrato_id, local_sub).

    local_sub é o sub-local dentro da cidade (UBS RURAL, CAPS, etc.),
    guardado depois em registro_pp.local_pp.
    """
    if not local_pp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "registro de PP sem Local (coluna Local)"},
        )

    try:
        uf, cidade, local_sub = _parse_local_pp(local_pp)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f"Local inválido: {e}"},
        )

    cidade_norm = _normaliza_cidade(cidade)

    existing = (
        client.table("contrato")
        .select("id")
        .eq("uf", uf)
        .eq("cidade_norm", cidade_norm)
        .limit(1)
        .execute()
    )
    if existing.data:
        return existing.data[0]["id"], local_sub

    payload = {
        "uf": uf,
        "cidade": cidade,
        "cidade_norm": cidade_norm,
        "nome": f"{uf} - {cidade}",
        "tipo": "PUBLICO",
        "status": "ATIVO",
    }
    inserted = client.table("contrato").insert(payload).execute()
    if not inserted.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"falha ao criar contrato ({uf}, {cidade})"},
        )
    return inserted.data[0]["id"], local_sub


def _rollback_rodada(client: Client, rodada_id: str) -> None:
    """
    Best-effort cleanup quando upload falha no meio.

    Ordem obrigatoria por conta de FKs:
      transacao_bancaria (ON DELETE SET NULL — poderia ficar mas preferimos limpar)
      registro_pp (ON DELETE RESTRICT em rodada_id — precisa ir antes)
      rodada

    NAO deleta prestadores/contratos criados durante a rodada: ficam
    como dividas tecnicas rastreaveis via log_auditoria. Hugo revisa
    via UI Passo 5.
    """
    try:
        client.table("transacao_bancaria").delete().eq("rodada_id", rodada_id).execute()
    except Exception:
        pass
    try:
        client.table("registro_pp").delete().eq("rodada_id", rodada_id).execute()
    except Exception:
        pass
    try:
        client.table("rodada").delete().eq("id", rodada_id).execute()
    except Exception:
        pass


@router.post("/upload", response_model=UploadRodadaResponse)
async def upload_rodada(
    periodo_extrato_inicio: date = Form(...),
    periodo_extrato_fim: date = Form(...),
    pp_arquivos: List[UploadFile] = File(...),
    extrato_ofx: UploadFile = File(...),
    current=Depends(get_current_user),
):
    """
    POST /rodadas/upload

    Cria uma rodada de conciliacao a partir de N arquivos PP XLSX + 1 OFX Bradesco.

    Sequencia:
      1. Valida periodo do extrato
      2. Cria rodada (status='CRIADA', pp_competencias=[])
      3. Parseia todos os PPs em memoria, detecta competencias pelo CONTEUDO
      4. Upload dos PPs ao storage: <rodada_id>/pp_<competencia>_<idx>.xlsx
      5. Upload do OFX: <rodada_id>/extrato.ofx
      6. Insere registro_pp (lookup/cria prestador e contrato)
      7. Insere transacao_bancaria com status_conciliacao='NAO_CLASSIFICADO'
         e mes_competencia placeholder (= YYYY-MM da data_extrato; Bloco C
         reatribui ao reconciliar contra PP)
      8. Atualiza rodada.pp_competencias com array detectado

    Falha em qualquer etapa apos criar rodada -> rollback logico (deleta
    transacao_bancaria + registro_pp + rodada da rodada em curso).
    """
    if periodo_extrato_fim < periodo_extrato_inicio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "periodo_extrato_fim anterior a periodo_extrato_inicio"},
        )

    client = get_supabase_authed(current["jwt"])
    user_id = current["id"]

    # 1) Cria rodada
    rodada_payload = {
        "periodo_extrato_inicio": periodo_extrato_inicio.isoformat(),
        "periodo_extrato_fim": periodo_extrato_fim.isoformat(),
        "pp_competencias": [],
        "criado_por": user_id,
        "status": "CRIADA",
    }
    created = client.table("rodada").insert(rodada_payload).execute()
    if not created.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "falha ao criar rodada"},
        )
    rodada_id = created.data[0]["id"]

    try:
        # 2) Parseia PPs em memoria; coleta competencias
        pp_parsed: List[dict] = []
        competencias_set: set[str] = set()
        total_registros = 0

        for idx, arquivo in enumerate(pp_arquivos, start=1):
            conteudo = await arquivo.read()
            if not conteudo:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": f"arquivo PP {arquivo.filename!r} vazio"},
                )
            try:
                records = pega_plantao.parse_relatorio(BytesIO(conteudo))
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": f"falha ao parsear PP {arquivo.filename!r}: {e}"},
                )

            competencias_arq = {
                _mm_yyyy_to_yyyy_mm(r.get("mes_competencia", ""))
                for r in records
                if r.get("mes_competencia")
            }
            competencias_arq = {c for c in competencias_arq if COMPETENCIA_REGEX.match(c)}
            if not competencias_arq:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": f"arquivo PP {arquivo.filename!r} sem competencia detectavel"},
                )

            competencia_dominante = sorted(competencias_arq)[0]
            competencias_set.update(competencias_arq)
            pp_parsed.append({
                "idx": idx,
                "bytes": conteudo,
                "content_type": arquivo.content_type or "application/octet-stream",
                "records": records,
                "competencia": competencia_dominante,
            })
            total_registros += len(records)

        # 3) Parseia OFX em memoria
        conteudo_ofx = await extrato_ofx.read()
        if not conteudo_ofx:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "extrato OFX vazio"},
            )
        try:
            transacoes = extrato_bradesco.parse_extrato(BytesIO(conteudo_ofx))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": f"falha ao parsear OFX: {e}"},
            )

        # 4) Upload dos PPs ao storage (nome final, sem rename)
        for item in pp_parsed:
            path = f"{rodada_id}/pp_{item['competencia']}_{item['idx']:02d}.xlsx"
            upload_to_supabase_storage(
                client, BUCKET_RODADAS, path, item["bytes"], item["content_type"],
            )

        # 5) Upload do OFX
        ofx_path = f"{rodada_id}/extrato.ofx"
        upload_to_supabase_storage(
            client, BUCKET_RODADAS, ofx_path, conteudo_ofx,
            extrato_ofx.content_type or "application/octet-stream",
        )

        # 6) Insere registro_pp (lookup/cria prestador e contrato)
        registro_rows: list[dict] = []
        for item in pp_parsed:
            for rec in item["records"]:
                prestador_id = _ensure_prestador(client, rec)
                contrato_id, local_sub = _ensure_contrato(client, rec.get("contrato", ""))

                mes = _mm_yyyy_to_yyyy_mm(rec.get("mes_competencia", ""))
                if not COMPETENCIA_REGEX.match(mes):
                    mes = item["competencia"]  # fallback para competencia dominante do arquivo

                saldo = float(rec.get("saldo") or 0.0)
                registro_rows.append({
                    "prestador_id": prestador_id,
                    "contrato_id": contrato_id,
                    "local_pp": local_sub,
                    "mes_competencia": mes,
                    "saldo_pp": saldo,
                    "status_saldo": _status_saldo(saldo),
                    "rodada_id": rodada_id,
                })

        if registro_rows:
            # Constraint UNIQUE (prestador_id, contrato_id, mes_competencia) foi dropada
            # na migration 0010 — mesmo prestador pode ter N registros_pp num contrato-cidade
            # via sub-locais distintos (local_pp). Insert simples; re-upload requer
            # limpar rodada anterior via _rollback_rodada.
            client.table("registro_pp").insert(registro_rows).execute()

        # 7) Insere transacao_bancaria
        # Alinhado com persistencia_parsers.persistir_extrato_bradesco:
        # - origem_banco é NOT NULL (constraint de schema)
        # - fitid usado pra dedup preventivo
        # - natureza_lancamento vem do tipo classificado pelo parser
        def _natureza(tipo: str) -> str:
            if tipo == "PIX_ENTRADA":
                return "PIX_CREDITO"
            if tipo == "PIX_SAIDA":
                return "PIX_DEBITO"
            if tipo == "TARIFA_BANCARIA":
                return "TARIFA_CONTA"
            return "OUTRO"

        tx_rows = []
        for t in transacoes:
            valor = float(t.get("valor") or 0.0)
            data_extrato = t.get("data") or ""
            mes_placeholder = data_extrato[:7] if len(data_extrato) >= 7 else periodo_extrato_inicio.strftime("%Y-%m")
            tx_rows.append({
                "conta_id": CONTA_BRADESCO_REMESSAS_ID,
                "valor": valor,
                "data_extrato": data_extrato,
                "mes_competencia": mes_placeholder,
                "tipo": "CREDITO" if valor >= 0 else "DEBITO",
                "status_conciliacao": "NAO_CLASSIFICADO",
                "descricao": (t.get("memo") or "")[:500] or None,
                "titular_pix": t.get("titular_pix") or None,
                "origem_banco": "BRADESCO",
                "natureza_lancamento": _natureza(t.get("tipo") or ""),
                "fitid": (t.get("fitid") or "").strip() or None,
                "rodada_id": rodada_id,
            })
        if tx_rows:
            # Dedup preventivo: filtra fitids que já existem na mesma conta
            fitids = [r["fitid"] for r in tx_rows if r.get("fitid")]
            if fitids:
                existentes = (
                    client.table("transacao_bancaria")
                    .select("fitid")
                    .eq("conta_id", CONTA_BRADESCO_REMESSAS_ID)
                    .in_("fitid", fitids)
                    .execute()
                    .data
                ) or []
                ja_existem = {e["fitid"] for e in existentes}
                tx_rows = [r for r in tx_rows if not r.get("fitid") or r["fitid"] not in ja_existem]
            if tx_rows:
                client.table("transacao_bancaria").insert(tx_rows).execute()

        # 8) Atualiza pp_competencias
        client.table("rodada").update(
            {"pp_competencias": sorted(competencias_set)}
        ).eq("id", rodada_id).execute()

        return UploadRodadaResponse(
            rodada_id=rodada_id,
            pp_competencias=sorted(competencias_set),
            extrato_periodo=ExtratoPeriodo(
                inicio=periodo_extrato_inicio.isoformat(),
                fim=periodo_extrato_fim.isoformat(),
            ),
            total_registros_pp=total_registros,
            total_transacoes=len(transacoes),
        )
    except HTTPException:
        _rollback_rodada(client, rodada_id)
        raise
    except Exception as e:
        _rollback_rodada(client, rodada_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"falha no upload da rodada: {e}"},
        )


# ============================================================================
# Bloco C — conciliacao
# ============================================================================

def _motor_to_db_status(motor_status: str) -> str:
    """Mapeia status retornado pelo motor para o ENUM do schema."""
    # Motor historicamente usa 'CONCILIADO_CATEGORIA'; schema exige 'CONCILIADO_POR_CATEGORIA'
    if motor_status == "CONCILIADO_CATEGORIA":
        return "CONCILIADO_POR_CATEGORIA"
    return motor_status


# Categorias do motor que nao existem no ENUM categoria_conciliacao do schema.
# Sao descartadas ao persistir (viram categoria=NULL):
#   - RECEBIMENTO_CONTRATANTE: nao e uma das 7 [ANCORADA]s; "recebimento" e
#     o que fecha ADIANTAMENTO, nao e categoria por si (analise fica pro Passo 4)
#   - VALOR_SEM_TITULAR: label interno do motor para match por valor sem titular;
#     registrado como MANUAL_PENDENTE (sem categoria) conforme CHECK do schema
CATEGORIAS_DB_VALIDAS = {
    "ADIANTAMENTO_AVISTA",
    "COMPETENCIA_ANTERIOR",
    "CLT_FOLHA",
    "DESPESA_OPERACIONAL",
    "COORDENADORA_CLT_PJ",
    "EXCECAO_PJ_PRESTADOR",
    "TRANSFERENCIA_INTERNA",
}


def _load_rodada(client: Client, rodada_id: str) -> dict:
    resp = client.table("rodada").select("*").eq("id", rodada_id).limit(1).execute()
    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "rodada nao encontrada"},
        )
    return resp.data[0]


def _load_registros_pp_para_motor(client: Client, rodada_id: str) -> List[dict]:
    """
    Carrega registros_pp da rodada com join em prestador e contrato, no formato
    que o motor espera. Anexa `_id` (UUID do registro_pp) para mapeamento reverso.

    Motor preserva a ordem de entrada ao devolver `registros`, entao
    pp_data[i] corresponde a resultado['registros'][i].
    """
    resp = (
        client.table("registro_pp")
        .select(
            "id, mes_competencia, saldo_pp, status_saldo, local_pp,"
            "prestador(id, nome, registro_profissional, uf, tipo_doc, cpf_cnpj, razao_social_pj, chave_pix, pj_empregadora_id),"
            "contrato(id, nome, uf, cidade)"
        )
        .eq("rodada_id", rodada_id)
        .execute()
    )
    pp_data: List[dict] = []
    for r in resp.data or []:
        p = r.get("prestador") or {}
        c = r.get("contrato") or {}
        # Track B — Fase E: prestadores com pj_empregadora_id (CLTs da FD que
        # aparecem no PP, ex: Karoliny/Edinalva) saem do pool individual de
        # sugestões porque são pagos pelo PIX consolidado SPM→FD (conciliação
        # em lote via POST /conciliacoes/intragrupo). Deixá-los aqui causaria
        # duplo débito (match individual + consumo em lote do mesmo CLT).
        if p.get("pj_empregadora_id"):
            continue
        pp_data.append({
            "_id": r["id"],
            "nome_prestador": p.get("nome") or "",
            "crm": p.get("registro_profissional") or "",
            "uf": p.get("uf") or "",
            "contrato": _contrato_display(c, r.get("local_pp")),
            "mes_competencia": r.get("mes_competencia") or "",
            "saldo": float(r.get("saldo_pp") or 0.0),
            "tipo_doc": p.get("tipo_doc") or "",
            "razao_social_pj": p.get("razao_social_pj") or "",
            "chave_pix": p.get("chave_pix") or "",
            "documento": p.get("cpf_cnpj") or "",
        })
    return pp_data


def _load_transacoes_para_motor(client: Client, rodada_id: str) -> List[dict]:
    """
    Carrega transacoes da rodada e re-classifica via extrato_bradesco.classificar_transacao()
    para recuperar a classificacao OFX (PIX_SAIDA, INVEST_FACIL, etc) que o
    motor espera em 'tipo'. DB so guarda direcao (CREDITO/DEBITO), nao classificacao.
    Usa o UUID da tx como 'fitid' (chave unica interna do motor).
    """
    resp = (
        client.table("transacao_bancaria")
        .select("id, valor, data_extrato, tipo, descricao, titular_pix")
        .eq("rodada_id", rodada_id)
        .execute()
    )
    extrato_data: List[dict] = []
    for t in resp.data or []:
        trntype = "CREDIT" if t.get("tipo") == "CREDITO" else "DEBIT"
        memo = t.get("descricao") or ""
        classificacao = extrato_bradesco.classificar_transacao(memo, trntype)
        extrato_data.append({
            "fitid": t["id"],
            "data": str(t.get("data_extrato") or ""),
            "valor": float(t.get("valor") or 0.0),
            "tipo": classificacao,
            "memo": memo,
            "titular_pix": t.get("titular_pix") or "",
            "trntype": trntype,
        })
    return extrato_data


def _load_excecoes_pj_dict(client: Client) -> Dict[str, str]:
    """
    Carrega excecoes PJ ativas do DB no formato do motor: {razao_social: nome_parcial}.
    Schema real: excecao_pj.razao_social_autorizada + prestador.nome (join).
    """
    resp = (
        client.table("excecao_pj")
        .select("razao_social_autorizada, prestador(nome)")
        .eq("ativo", True)
        .execute()
    )
    result: Dict[str, str] = {}
    for e in resp.data or []:
        razao = e.get("razao_social_autorizada") or ""
        p = e.get("prestador") or {}
        nome = p.get("nome") or ""
        if razao and nome:
            # Motor casa titular do PIX contra nome parcial. Normalizar PRIMEIRO
            # (remove prefixo DR/DRA) antes de pegar o primeiro token — senao
            # nome_parcial vira "DR"/"DRA" e gera falso match em todos prestadores.
            nome_norm = conciliacao_spm._normalizar_nome(nome)
            partes = nome_norm.split()
            nome_parcial = partes[0] if partes else nome
            result[razao] = nome_parcial
    return result


def _reset_conciliacao_da_rodada(client: Client, rodada_id: str) -> None:
    """Zera status_conciliacao/categoria/registro_pp_id das tx da rodada (re-run)."""
    client.table("transacao_bancaria").update({
        "status_conciliacao": "NAO_CLASSIFICADO",
        "categoria": None,
        "registro_pp_id": None,
    }).eq("rodada_id", rodada_id).execute()


def _computar_metricas_rodada(client: Client, rodada_id: str) -> dict:
    """
    Calcula metricas de conciliacao da rodada no criterio aprovado por Hugo
    (bate com o 93,5% da rodada manual de 13/04/2026):

        percentual = debitos_enderecados / valor_total_pp_elegivel

    Definicoes:
      - debitos_enderecados = soma de |valor| de transacao_bancaria onde
        rodada_id=X AND tipo='DEBITO'
                  AND status_conciliacao != 'NAO_CLASSIFICADO'
                  AND (categoria IS NULL OR categoria != 'TRANSFERENCIA_INTERNA')
        TRANSFERENCIA_INTERNA e excluida porque representa movimento entre
        contas da propria SPM (INVEST_FACIL, transf. SOCIEDADE PARANAENSE)
        — nao e pagamento endereçado a fornecedor/prestador.
      - valor_total_pp_elegivel = soma de saldo_pp de registro_pp onde
        rodada_id=X e status_saldo='ELEGIVEL'

    Retorno: {valor_total_pp_elegivel, debitos_enderecados, percentual}.
    """
    tx_resp = (
        client.table("transacao_bancaria")
        .select("valor, tipo, status_conciliacao, categoria")
        .eq("rodada_id", rodada_id)
        .execute()
    )
    debitos_enderecados = 0.0
    for t in tx_resp.data or []:
        if (t.get("tipo") == "DEBITO"
            and t.get("status_conciliacao") != "NAO_CLASSIFICADO"
            and t.get("categoria") != "TRANSFERENCIA_INTERNA"):
            debitos_enderecados += abs(float(t.get("valor") or 0.0))

    pp_resp = (
        client.table("registro_pp")
        .select("saldo_pp, status_saldo")
        .eq("rodada_id", rodada_id)
        .execute()
    )
    valor_total_pp_elegivel = 0.0
    for r in pp_resp.data or []:
        if r.get("status_saldo") == "ELEGIVEL":
            valor_total_pp_elegivel += float(r.get("saldo_pp") or 0.0)

    percentual = (
        debitos_enderecados / valor_total_pp_elegivel * 100.0
        if valor_total_pp_elegivel > 0 else 0.0
    )
    return {
        "valor_total_pp_elegivel": round(valor_total_pp_elegivel, 2),
        "debitos_enderecados": round(debitos_enderecados, 2),
        "percentual": round(percentual, 2),
    }


def _aplicar_updates_em_batch(
    client: Client, atualizacoes: Dict[str, dict]
) -> None:
    """
    Agrupa atualizacoes por (status, categoria, registro_pp_id) e faz
    1 UPDATE por grupo com IN (<ids>). Reduz round trips ao DB.
    """
    grupos: Dict[tuple, list] = defaultdict(list)
    for tx_id, payload in atualizacoes.items():
        key = (
            payload["status_conciliacao"],
            payload.get("categoria"),
            payload.get("registro_pp_id"),
        )
        grupos[key].append(tx_id)

    for (st, cat, reg_id), ids in grupos.items():
        update_payload = {"status_conciliacao": st, "categoria": cat, "registro_pp_id": reg_id}
        client.table("transacao_bancaria").update(update_payload).in_("id", ids).execute()


@router.post("/{rodada_id}/conciliar", response_model=ConciliarResponse)
def conciliar_rodada(
    rodada_id: UUID,
    current=Depends(get_current_user),
):
    """
    POST /rodadas/{rodada_id}/conciliar

    Executa o motor de conciliacao sobre os registros_pp + transacoes_bancaria
    da rodada e persiste o resultado em transacao_bancaria.

    Comportamento:
      - rodada VALIDADA: 409 (imutavel exceto CEO)
      - CRIADA/CONCILIADA/PROCESSANDO/CANCELADA: reprocessa do zero
        (reset -> motor -> UPDATE resultado -> status='CONCILIADA')
    """
    client = get_supabase_authed(current["jwt"])
    rid = str(rodada_id)
    rodada = _load_rodada(client, rid)

    if rodada.get("status") == "VALIDADA":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "rodada em status VALIDADA - imutavel (exceto CEO)"},
        )

    # 1) Reset do estado de conciliacao das tx da rodada
    _reset_conciliacao_da_rodada(client, rid)

    # 2) Carrega dados no formato do motor
    pp_data = _load_registros_pp_para_motor(client, rid)
    extrato_data = _load_transacoes_para_motor(client, rid)
    excecoes_pj = _load_excecoes_pj_dict(client)

    # 3) Invoca motor (imports como biblioteca)
    try:
        resultado = conciliacao_spm.conciliar(pp_data, extrato_data, excecoes_pj=excecoes_pj)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"falha no motor de conciliacao: {e}"},
        )

    # 4) Mapeia saida do motor -> updates em transacao_bancaria
    #    Motor preserva ordem: resultado['registros'][i] corresponde a pp_data[i]
    atualizacoes: Dict[str, dict] = {}   # tx_id -> {status_conciliacao, categoria, registro_pp_id}

    registros_motor = resultado.get("registros", [])
    for i, r in enumerate(registros_motor):
        pp_original = pp_data[i] if i < len(pp_data) else None
        reg_pp_id = pp_original["_id"] if pp_original else None

        status_motor = r.get("status", "")
        status_db = _motor_to_db_status(status_motor)

        # Apenas status que persistem em transacao_bancaria:
        if status_db in ("MATCH_AUTOMATICO", "FRACIONADO", "CONCILIADO_POR_CATEGORIA"):
            # pix_matched: PIX associados ao match (cada um tem fitid=UUID da tx)
            pix_matched = r.get("pix_matched") or []
            categoria_motor = r.get("categoria") or ""
            categoria_final = (
                categoria_motor if (status_db == "CONCILIADO_POR_CATEGORIA"
                                    and categoria_motor in CATEGORIAS_DB_VALIDAS)
                else None
            )
            for pix in pix_matched:
                tx_id = pix.get("fitid")
                if tx_id:
                    atualizacoes[tx_id] = {
                        "status_conciliacao": status_db,
                        "categoria": categoria_final,
                        "registro_pp_id": reg_pp_id,
                    }
        elif status_db == "MANUAL_PENDENTE":
            # PIX com valor batendo mas titular divergente, ou titular ok mas valor diverge
            pix_matched = r.get("pix_matched") or []
            for pix in pix_matched:
                tx_id = pix.get("fitid")
                if tx_id:
                    atualizacoes[tx_id] = {
                        "status_conciliacao": "MANUAL_PENDENTE",
                        "categoria": None,
                        "registro_pp_id": reg_pp_id,
                    }
        # SEM_MOVIMENTO, SALDO_NEGATIVO, NAO_CLASSIFICADO: sem tx afetada (ou
        # tx ja foi absorvida por outro registro_pp; fica NAO_CLASSIFICADO do reset)

    # 5) Transacoes extras (categoria automatica, listas CLT/COORD/DESPESA_OP, excecao_pj DB)
    transacoes_extras = resultado.get("transacoes_extras") or []
    for t in transacoes_extras:
        tx_id = t.get("fitid")
        cat = t.get("categoria")
        if not tx_id:
            continue
        # Descartar categorias nao persistenciaveis (RECEBIMENTO_CONTRATANTE etc)
        if cat in CATEGORIAS_DB_VALIDAS:
            atualizacoes[tx_id] = {
                "status_conciliacao": "CONCILIADO_POR_CATEGORIA",
                "categoria": cat,
                "registro_pp_id": None,
            }
        # Se cat nao e valida no DB, descartamos — tx fica NAO_CLASSIFICADO (do reset)

    # 6) Aplica UPDATEs em batch (agrupados por payload)
    if atualizacoes:
        _aplicar_updates_em_batch(client, atualizacoes)

    # 7) Atualiza rodada.status
    client.table("rodada").update({"status": "CONCILIADA"}).eq("id", rid).execute()

    # 8) Monta response
    resumo_motor = resultado.get("resumo", {})
    resumo_tx = ResumoTransacoes(
        match_automatico=int(resumo_motor.get("match_automatico") or 0),
        fracionado=int(resumo_motor.get("fracionado") or 0),
        conciliado_categoria=int(resumo_motor.get("conciliado_categoria") or 0) + len(transacoes_extras),
        manual_pendente=int(resumo_motor.get("manual_pendente") or 0),
        nao_classificado=int(resumo_motor.get("nao_classificado") or 0),
    )
    total_registros = int(resumo_motor.get("total_registros_pp") or 0)
    sem_mov = int(resumo_motor.get("sem_movimento") or 0)
    saldo_neg = int(resumo_motor.get("saldo_negativo") or 0)
    resumo_pp = ResumoRegistrosPP(
        total_elegivel=total_registros - sem_mov - saldo_neg,
        sem_movimento=sem_mov,
        saldo_negativo=saldo_neg,
    )

    metricas = _computar_metricas_rodada(client, rid)
    return ConciliarResponse(
        rodada_id=rodada_id,
        resumo_transacoes=resumo_tx,
        resumo_registros_pp=resumo_pp,
        valor_total_pp=metricas["valor_total_pp_elegivel"],
        valor_total_conciliado=metricas["debitos_enderecados"],
        percentual_conciliado=metricas["percentual"],
    )


# ============================================================================
# GET /rodadas/{rodada_id}/resultado — paginado
# ============================================================================

@router.get("/{rodada_id}/resultado", response_model=ResultadoResponse)
def get_resultado_rodada(
    rodada_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    current=Depends(get_current_user),
):
    """
    GET /rodadas/{rodada_id}/resultado?page=1&per_page=50

    Retorna resumo agregado da rodada + pagina de transacoes com o join
    de registro_pp/prestador/contrato quando houver match.
    """
    client = get_supabase_authed(current["jwt"])
    rid = str(rodada_id)
    _ = _load_rodada(client, rid)   # 404 se nao existe

    # Total (count='exact')
    count_resp = (
        client.table("transacao_bancaria")
        .select("id", count="exact")
        .eq("rodada_id", rid)
        .execute()
    )
    total = count_resp.count or 0

    # Pagina
    offset = (page - 1) * per_page
    list_resp = (
        client.table("transacao_bancaria")
        .select(
            "id, valor, data_extrato, titular_pix, descricao,"
            "status_conciliacao, categoria, registro_pp_id,"
            "registro_pp("
            "  id, mes_competencia, saldo_pp, status_saldo,"
            "  prestador(nome),"
            "  contrato(nome)"
            ")"
        )
        .eq("rodada_id", rid)
        .order("data_extrato")
        .order("valor")
        .range(offset, offset + per_page - 1)
        .execute()
    )

    transacoes: List[TransacaoResultado] = []
    for t in list_resp.data or []:
        rp_nested = None
        rp_raw = t.get("registro_pp")
        if rp_raw:
            rp_nested = RegistroPPNested(
                id=rp_raw["id"],
                prestador_nome=(rp_raw.get("prestador") or {}).get("nome"),
                contrato_nome=(rp_raw.get("contrato") or {}).get("nome"),
                mes_competencia=rp_raw.get("mes_competencia") or "",
                saldo_pp=float(rp_raw.get("saldo_pp") or 0.0),
                status_saldo=rp_raw.get("status_saldo") or "",
            )
        transacoes.append(TransacaoResultado(
            id=t["id"],
            valor=float(t.get("valor") or 0.0),
            data_extrato=str(t.get("data_extrato") or ""),
            titular_pix=t.get("titular_pix"),
            descricao=t.get("descricao"),
            status_conciliacao=t.get("status_conciliacao") or "NAO_CLASSIFICADO",
            categoria=t.get("categoria"),
            registro_pp_id=t.get("registro_pp_id"),
            registro_pp=rp_nested,
        ))

    # Resumo agregado (por tx da rodada — recount da DB, nao do motor,
    # para refletir o estado persistido mesmo se conciliar nunca rodou)
    status_counts: Dict[str, int] = defaultdict(int)
    status_resp = (
        client.table("transacao_bancaria")
        .select("status_conciliacao")
        .eq("rodada_id", rid)
        .execute()
    )
    for row in status_resp.data or []:
        status_counts[row.get("status_conciliacao") or "NAO_CLASSIFICADO"] += 1

    resumo_tx = ResumoTransacoes(
        match_automatico=status_counts.get("MATCH_AUTOMATICO", 0),
        fracionado=status_counts.get("FRACIONADO", 0),
        conciliado_categoria=status_counts.get("CONCILIADO_POR_CATEGORIA", 0),
        manual_pendente=status_counts.get("MANUAL_PENDENTE", 0),
        nao_classificado=status_counts.get("NAO_CLASSIFICADO", 0),
    )

    # Resumo de registros PP (da rodada)
    pp_counts: Dict[str, int] = defaultdict(int)
    pp_resp = (
        client.table("registro_pp")
        .select("status_saldo, saldo_pp")
        .eq("rodada_id", rid)
        .execute()
    )
    valor_total_pp = 0.0
    for row in pp_resp.data or []:
        pp_counts[row.get("status_saldo") or ""] += 1
        if (row.get("status_saldo") or "") == "ELEGIVEL":
            valor_total_pp += float(row.get("saldo_pp") or 0.0)
    resumo_pp = ResumoRegistrosPP(
        total_elegivel=pp_counts.get("ELEGIVEL", 0),
        sem_movimento=pp_counts.get("SEM_MOVIMENTO", 0),
        saldo_negativo=pp_counts.get("SALDO_NEGATIVO", 0),
    )

    # Metrica unificada (criterio aprovado por Hugo — bate com 93,5% manual)
    metricas = _computar_metricas_rodada(client, rid)

    return ResultadoResponse(
        rodada_id=rodada_id,
        resumo_transacoes=resumo_tx,
        resumo_registros_pp=resumo_pp,
        valor_total_pp=metricas["valor_total_pp_elegivel"],
        valor_total_conciliado=metricas["debitos_enderecados"],
        percentual_conciliado=metricas["percentual"],
        transacoes=transacoes,
        pagination=Pagination(page=page, per_page=per_page, total=total),
    )


# ============================================================================
# Bloco D — aprovacao de rodada + snapshot imutavel
# ============================================================================

def _montar_payload_snapshot(client: Client, rodada_id_str: str) -> dict:
    """
    Carrega todas as transacoes, registros_pp e excecoes ativas para congelar
    no payload do snapshot. Ordem determinista (ordenada por id) para garantir
    hash SHA256 reproduzivel em T11.
    """
    tx_resp = (
        client.table("transacao_bancaria")
        .select("*")
        .eq("rodada_id", rodada_id_str)
        .order("id")
        .execute()
    )
    pp_resp = (
        client.table("registro_pp")
        .select("*")
        .eq("rodada_id", rodada_id_str)
        .order("id")
        .execute()
    )
    exc_resp = (
        client.table("excecao_pj")
        .select("*")
        .eq("ativo", True)
        .order("id")
        .execute()
    )
    return {
        "transacoes": tx_resp.data or [],
        "registros_pp": pp_resp.data or [],
        "excecoes_ativas": exc_resp.data or [],
        "metadados": {
            "snapshot_schema_version": "1",
        },
    }


@router.post(
    "/{rodada_id}/aprovar",
    response_model=RodadaSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
def aprovar_rodada(
    rodada_id: UUID,
    current=Depends(require_ceo_with_2fa),
):
    """
    POST /rodadas/{id}/aprovar

    Congela a rodada: cria snapshot com payload completo + hash SHA256 e marca
    rodada aprovada (snapshot_id/aprovada_em/aprovada_por coerentes pelo CHECK
    ck_rodada_aprovacao_coerente). Rodada aprovada fica imutavel via trigger
    trg_bloqueia_update_rodada_aprovada.

    Requer CEO (+ TOTP quando FEATURE_2FA=true).

    Atomicidade: INSERT snapshot + UPDATE rodada NAO sao transacao unica via
    supabase-py. Se UPDATE falhar, o snapshot inserido fica orfao e bloqueia
    re-aprovacao (UNIQUE ux_rodada_snapshot_rodada). Remediacao: limpeza
    manual via service_role. Endurecimento futuro: RPC fn_aprovar_rodada()
    em transacao unica (backlog Victor).
    """
    client = get_supabase_authed(current["jwt"])
    rid = str(rodada_id)
    rodada = _load_rodada(client, rid)

    if rodada.get("aprovada_em"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "rodada ja aprovada"},
        )

    metricas = _computar_metricas_rodada(client, rid)
    payload = _montar_payload_snapshot(client, rid)
    payload_json = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
    hash_payload = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

    snapshot_payload = {
        "rodada_id": rid,
        "aprovada_por": current["id"],
        "total_pp_elegivel": metricas["valor_total_pp_elegivel"],
        "total_conciliado": metricas["debitos_enderecados"],
        "percentual_conciliado": metricas["percentual"],
        "qtd_transacoes": len(payload.get("transacoes", [])),
        "qtd_registros_pp": len(payload.get("registros_pp", [])),
        "payload": payload,
        "hash_payload": hash_payload,
    }
    try:
        created = client.table("rodada_snapshot").insert(snapshot_payload).execute()
    except Exception as e:
        msg = str(e).lower()
        if "ux_rodada_snapshot_rodada" in msg or "duplicate key" in msg or "23505" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "rodada ja aprovada (snapshot existente)"},
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": f"falha ao criar snapshot: {e}"},
        )
    rows = created.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "insert snapshot retornou vazio"},
        )
    snapshot_row = rows[0]

    try:
        client.table("rodada").update({
            "snapshot_id": snapshot_row["id"],
            "aprovada_em": snapshot_row["aprovada_em"],
            "aprovada_por": current["id"],
        }).eq("id", rid).execute()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": (
                    f"snapshot criado mas falha ao marcar rodada: {e}. "
                    f"Snapshot orfao id={snapshot_row['id']} — limpeza manual necessaria."
                )
            },
        )

    return RodadaSnapshotResponse(**snapshot_row)


@router.get("/{rodada_id}/snapshot", response_model=RodadaSnapshotResponse)
def obter_snapshot(
    rodada_id: UUID,
    current=Depends(get_current_user),
):
    """
    GET /rodadas/{id}/snapshot

    Retorna o snapshot imutavel. 404 se rodada nao aprovada (sem snapshot).
    Leitura liberada para qualquer autenticado (policy rodada_snapshot_select).
    """
    client = get_supabase_authed(current["jwt"])
    resp = (
        client.table("rodada_snapshot")
        .select("*")
        .eq("rodada_id", str(rodada_id))
        .limit(1)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "snapshot nao encontrado (rodada nao aprovada)"},
        )
    return RodadaSnapshotResponse(**rows[0])
