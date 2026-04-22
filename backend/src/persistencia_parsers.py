"""Glue entre parsers (Python puro) e Supabase (persistência)."""
from typing import Dict, List
from uuid import UUID
from supabase import Client
from postgrest.exceptions import APIError

from backend.src.orcamento_xlsx import OrcamentoParser, OrcamentoLinhaParsed, NaturezaOrcamento
from backend.src.extrato_unicred import UnicredParser
from backend.src.extrato_bradesco import extract_bank_account, parse_extrato


def persistir_orcamento_xlsx(
    client: Client,
    arquivo_bytes: bytes,
    empresa_id: UUID,
    competencia: str,
    criado_por: UUID,
) -> Dict:
    """
    Parsea XLSX e insere orcamento + orcamento_linha em transação lógica.
    Retorna dict no formato ResultadoUploadOrcamento.

    Raises:
        ValueError: se já existir orcamento para (empresa, competencia).
    """
    resultado = OrcamentoParser().parse_completo(arquivo_bytes)

    # Cria cabeçalho. Duplicata em (empresa_id, competencia) dispara 23505 no
    # Postgres, que o postgrest-py propaga como APIError. Convertemos para
    # ValueError para o router traduzir em HTTP 409.
    try:
        ins = client.table("orcamento").insert({
            "empresa_id": str(empresa_id),
            "competencia": competencia,
            "status": "RASCUNHO",
            "criado_por": str(criado_por),
        }).execute()
    except APIError as e:
        code = getattr(e, "code", None) or (e.args[0].get("code") if e.args and isinstance(e.args[0], dict) else None)
        msg = getattr(e, "message", None) or (e.args[0].get("message", str(e)) if e.args and isinstance(e.args[0], dict) else str(e))
        if code == "23505" or "duplicate key" in msg.lower() or "unique constraint" in msg.lower():
            raise ValueError("Orcamento ja existe para essa (empresa, competencia)")
        raise
    if not ins.data:
        raise ValueError("Falha ao criar orcamento (possível duplicata)")
    orcamento_id = ins.data[0]["id"]

    # Lookup de catálogos: categoria_despesa e projeto
    cats = client.table("categoria_despesa").select("id,nome").execute()
    mapa_categoria = {c["nome"].upper(): c["id"] for c in cats.data}
    projs = client.table("projeto").select("id,codigo").execute()
    mapa_projeto = {p["codigo"].upper(): p["id"] for p in projs.data}
    empresa_by_codigo = {
        e["codigo"]: e["id"]
        for e in client.table("empresa").select("id,codigo").execute().data
    }

    rows_para_inserir = []
    avisos: List[str] = []
    for linha in resultado.linhas:
        cat_id = mapa_categoria.get((linha.categoria or "").upper())
        proj_id = mapa_projeto.get((linha.projeto or "").upper())
        emp_id = empresa_by_codigo.get(linha.empresa_codigo, str(empresa_id))
        if linha.projeto and not proj_id:
            avisos.append(f"Projeto '{linha.projeto}' (linha XLSX {linha.linha_xlsx}) não cadastrado — campo ficou NULL.")
        rows_para_inserir.append({
            "orcamento_id": orcamento_id,
            "natureza": linha.natureza.value,
            "categoria_id": cat_id,
            "projeto_id": proj_id,
            "titular_cpf_cnpj": linha.titular_cpf_cnpj,
            "titular_razao_social": linha.titular_razao_social,
            "valor_previsto": linha.valor_previsto,
            "data_previsao": linha.data_previsao,
            "observacao": linha.observacao,
        })

    # Bulk insert
    if rows_para_inserir:
        client.table("orcamento_linha").insert(rows_para_inserir).execute()

    return {
        "orcamento_id": orcamento_id,
        "total_linhas_inseridas": len(rows_para_inserir),
        "linhas_por_secao": {k.value: v for k, v in resultado.linhas_por_secao.items()},
        "linhas_descartadas": resultado.linhas_descartadas,
        "avisos": avisos,
    }


def persistir_extrato_unicred(client: Client, arquivo_bytes: bytes, conta_id: UUID) -> Dict:
    """Parseia PDF Unicred e insere transacoes em transacao_bancaria.

    Returns:
        dict compativel com UploadExtratoResponse.
    """
    parser = UnicredParser()
    meta = parser.extrair_metadados(arquivo_bytes)
    transacoes = parser.parse(arquivo_bytes)
    rows = [{
        "conta_id": str(conta_id),
        "valor": t.valor,
        "data_extrato": t.data_movimento,
        "mes_competencia": t.data_movimento[:7],
        "tipo": "CREDITO" if t.valor > 0 else "DEBITO",
        "status_conciliacao": "NAO_CLASSIFICADO",
        "descricao": (t.historico or "")[:500],
        "titular_pix": t.titular_pix,
        "origem_banco": "UNICRED",
        "natureza_lancamento": t.natureza.value,
    } for t in transacoes]
    if rows:
        client.table("transacao_bancaria").insert(rows).execute()

    # Persiste snapshot de saldo da conta (alimenta Dashboard de Liquidez)
    if meta.saldo_final is not None and meta.periodo_fim:
        try:
            client.table("saldo_conta_snapshot").insert({
                "conta_bancaria_id": str(conta_id),
                "saldo_valor": float(meta.saldo_final),
                "data_referencia": meta.periodo_fim,
                "origem": "UNICRED_PDF",
            }).execute()
        except Exception:
            pass  # não-crítico — se falhar, extrato continua válido

    return {
        "conta_id": conta_id,
        "origem_banco": "UNICRED",
        "total_transacoes_inseridas": len(rows),
        "periodo_inicio": meta.periodo_inicio or "",
        "periodo_fim": meta.periodo_fim or "",
        "saldo_final": meta.saldo_final,
    }


def _natureza_bradesco(tipo: str, trntype: str) -> str:
    """Mapeia o `tipo` classificado pelo parser Bradesco para `natureza_lancamento`.

    parse_extrato retorna tipos como PIX_ENTRADA, PIX_SAIDA, TED_ENTRADA, TED_SAIDA,
    TARIFA_BANCARIA, INVEST_FACIL, PAGAMENTO, DOC, SAQUE, DEPOSITO, ENCARGO, OUTROS.
    natureza_lancamento só aceita: PIX_CREDITO, PIX_DEBITO, PIX_TEF, LIQUIDACAO_TITULO,
    CONVENIO, INTEGRALIZACAO_CAPITAL, ARRECADACAO, TARIFA_CONTA, ESTORNO, OUTRO.
    """
    if tipo == "PIX_ENTRADA":
        return "PIX_CREDITO"
    if tipo == "PIX_SAIDA":
        return "PIX_DEBITO"
    if tipo == "TARIFA_BANCARIA":
        return "TARIFA_CONTA"
    return "OUTRO"


def persistir_extrato_bradesco(client: Client, arquivo_bytes: bytes) -> Dict:
    """Rota pelo BANKID+ACCTID para resolver conta_id; parseia OFX e insere.

    Raises:
        ValueError: se a conta (banco, conta) nao estiver cadastrada.
    """
    bankid, acctid = extract_bank_account(arquivo_bytes)
    # BANKID vem como "0237" no OFX mas pode estar cadastrado como "237" no DB
    # (ou vice-versa). Tentamos a variação sem zeros à esquerda se a primeira falhar.
    resp = (
        client.table("conta_bancaria")
        .select("id,finalidade,banco,conta")
        .eq("banco", bankid)
        .eq("conta", acctid)
        .execute()
    )
    rows_conta = resp.data or []
    if not rows_conta:
        # fallback sem zeros à esquerda no bankid
        bankid_norm = bankid.lstrip("0") or bankid
        if bankid_norm != bankid:
            resp = (
                client.table("conta_bancaria")
                .select("id,finalidade,banco,conta")
                .eq("banco", bankid_norm)
                .eq("conta", acctid)
                .execute()
            )
            rows_conta = resp.data or []
    if not rows_conta:
        # fallback: Bradesco OFX omite o DV (dígito verificador) da conta.
        # Tenta match com a conta cadastrada SEM o último dígito.
        bankid_norm = bankid.lstrip("0") or bankid
        resp = (
            client.table("conta_bancaria")
            .select("id,finalidade,banco,conta")
            .in_("banco", [bankid, bankid_norm])
            .execute()
        )
        for row in resp.data or []:
            c = row.get("conta") or ""
            # Match se a conta cadastrada sem o último dígito bate com o ACCTID
            if c and c[:-1] == acctid:
                rows_conta = [row]
                break
    if not rows_conta:
        raise ValueError(f"Conta nao cadastrada: banco {bankid} conta {acctid}")
    conta_id = rows_conta[0]["id"]

    transacoes = parse_extrato(arquivo_bytes)
    rows = []
    for t in transacoes:
        valor = t["valor"]
        data = t["data"]
        if not data or len(data) != 10:
            # pula transacoes sem data valida (formato YYYY-MM-DD esperado)
            continue
        rows.append({
            "conta_id": conta_id,
            "valor": valor,
            "data_extrato": data,
            "mes_competencia": data[:7],
            "tipo": "CREDITO" if valor > 0 else "DEBITO",
            "status_conciliacao": "NAO_CLASSIFICADO",
            "descricao": (t.get("memo") or "")[:500],
            "titular_pix": t.get("titular_pix") or None,
            "origem_banco": "BRADESCO",
            "natureza_lancamento": _natureza_bradesco(t.get("tipo") or "", t.get("trntype") or ""),
        })
    if rows:
        client.table("transacao_bancaria").insert(rows).execute()
    datas = sorted(r["data_extrato"] for r in rows)

    # Extrai saldo do OFX (<LEDGERBAL>) e persiste snapshot pra Dashboard de Liquidez
    from backend.src.extrato_bradesco import extract_saldo
    saldo_info = extract_saldo(arquivo_bytes)
    saldo_final = 0.0
    if saldo_info and saldo_info.get("data_referencia"):
        saldo_final = float(saldo_info["saldo"])
        try:
            client.table("saldo_conta_snapshot").insert({
                "conta_bancaria_id": str(conta_id),
                "saldo_valor": saldo_final,
                "data_referencia": saldo_info["data_referencia"],
                "origem": "BRADESCO_OFX",
            }).execute()
        except Exception:
            pass

    return {
        "conta_id": conta_id,
        "origem_banco": "BRADESCO",
        "total_transacoes_inseridas": len(rows),
        "periodo_inicio": datas[0] if datas else "",
        "periodo_fim": datas[-1] if datas else "",
        "saldo_final": saldo_final,
    }
