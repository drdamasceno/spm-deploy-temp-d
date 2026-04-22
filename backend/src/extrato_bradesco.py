"""
Parser de extrato Bradesco conta corrente OFX.

Formato: SGML OFX 1.02, encoding latin-1/cp1252
Banco: BANKID 0237 (Bradesco)

Cada transação em <STMTTRN>...</STMTTRN>:
  <TRNTYPE>: CREDIT ou DEBIT
  <DTPOSTED>: YYYYMMDDHHMMSS
  <TRNAMT>: valor com vírgula (ex: -1234,56)
  <FITID>: ID único
  <MEMO>: descrição (contém nome titular PIX)

# Extrair: data, descrição, valor, tipo, titular_pix
"""

from __future__ import annotations

import re
import logging
from io import BytesIO
from pathlib import Path
from typing import List, Dict, Any, Union

logger = logging.getLogger(__name__)

# Classificações automáticas por padrão de MEMO
_CLASSIFICACOES = [
    (r'invest\s+facil|rentab\.?invest\s+facil|resgate\s+invest\s+facil', 'INVEST_FACIL'),
    (r'tarifa\s+bancaria|tarifa\s+cob|tarifa\s+de', 'TARIFA_BANCARIA'),
    (r'ted[-\s]transf|transf\.?\s+elet|ted\s+entrada|ted\s+saida', 'TED'),
    (r'transferencia\s+pix|pix\s+rem|pix\s+rec|pix\s+pagamento|pix\s+enviado|pix\s+recebido', 'PIX'),
    (r'pagamento|pgto', 'PAGAMENTO'),
    (r'doc\b', 'DOC'),
    (r'saque|retirada', 'SAQUE'),
    (r'deposito|dep[oó]sito', 'DEPOSITO'),
    (r'juros|multa|encargo', 'ENCARGO'),
]


def _limpar_titular(nome: str) -> str:
    """
    Limpeza padrão do titular extraído:
      - Remove data no final (DD/MM ou D/M)
      - Strip espaços
      - Uppercase
    """
    if not nome:
        return ""
    s = nome.strip()
    # Remove data no final: "  01/04", " 1/4", etc.
    s = re.sub(r'\s+\d{1,2}/\d{1,2}\s*$', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s.upper()


def extrair_titular_pix(memo: str) -> str:
    """
    Extrai o nome do titular PIX do campo MEMO.

    Padrões reconhecidos (Bradesco):
      "TRANSFERENCIA PIX DES: NOME   DD/MM"   (destinatário — saída)
      "TRANSFERENCIA PIX REM: NOME   DD/MM"   (remetente — entrada)
      "PIX DES: NOME"
      "PIX REM: NOME"
      "PIX PAG(AMENTO): NOME"
      "PIX REC(EBIDO): NOME"
      "PIX ENVIADO/RECEBIDO/PAGAMENTO NOME"

    Returns:
        Nome do titular em UPPERCASE, sem data, ou string vazia.
    """
    memo = (memo or "").strip()

    # Padrão principal: "[TRANSFERENCIA ]PIX <DES|REM|PAG[AMENTO]|REC[EBIDO]>: NOME ..."
    m = re.search(
        r'(?:TRANSFERENCIA\s+)?PIX\s+(?:DES|REM|PAG(?:AMENTO)?|REC(?:EBIDO)?):\s+(.+?)(?:\s{2,}|\s+\d{1,2}/\d{1,2}|$)',
        memo, re.IGNORECASE
    )
    if m:
        return _limpar_titular(m.group(1))

    # Padrão sem dois-pontos: "PIX ENVIADO/RECEBIDO/PAGAMENTO NOME"
    m = re.search(
        r'PIX\s+(?:ENVIADO|RECEBIDO|PAGAMENTO)\s+(.+?)(?:\s{2,}|\s+\d{1,2}/\d{1,2}|$)',
        memo, re.IGNORECASE
    )
    if m:
        return _limpar_titular(m.group(1))

    return ""


def classificar_transacao(memo: str, trntype: str) -> str:
    """
    Classifica a transação com base no MEMO e tipo (CREDIT/DEBIT).

    Returns:
        Uma das classificações: INVEST_FACIL, TARIFA_BANCARIA, TED_ENTRADA,
        PIX_ENTRADA, PIX_SAIDA, PAGAMENTO, DOC, SAQUE, DEPOSITO, ENCARGO, OUTROS
    """
    memo_upper = (memo or "").upper()
    trntype = (trntype or "").upper()

    # INVEST FACIL (sempre categorizado separado — não é receita/despesa operacional)
    if re.search(r'INVEST\s*FACIL|RENTAB\.?\s*INVEST|RESGATE\s+INVEST', memo_upper):
        return 'INVEST_FACIL'

    # Tarifas
    if re.search(r'TARIFA|COBRANCA\s+DE|ENCARGO\s+', memo_upper):
        return 'TARIFA_BANCARIA'

    # TED
    if re.search(r'TED[-\s]TRANSF|TRANSF\.?\s*ELET|\bTED\b', memo_upper):
        return 'TED_ENTRADA' if trntype == 'CREDIT' else 'TED_SAIDA'

    # PIX
    if re.search(r'\bPIX\b|TRANSFERENCIA\s+PIX', memo_upper):
        return 'PIX_ENTRADA' if trntype == 'CREDIT' else 'PIX_SAIDA'

    # Outros padrões
    for pattern, tipo in _CLASSIFICACOES[4:]:
        if re.search(pattern, memo_upper, re.IGNORECASE):
            return tipo

    return 'OUTROS'


def _parse_data(dtposted: str) -> str:
    """
    Converte DTPOSTED (YYYYMMDDHHMMSS ou YYYYMMDD) para "YYYY-MM-DD".
    """
    s = (dtposted or "").strip()[:8]
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return s


def _parse_valor(trnamt: str) -> float:
    """
    Converte TRNAMT (ex: "-1234,56" ou "-1234.56") para float.
    Mantém sinal: negativo = saída.
    """
    s = (trnamt or "0").strip().replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _extract_tag(block: str, tag: str) -> str:
    """Extrai o valor de uma tag SGML simples: <TAG>value."""
    m = re.search(f'<{tag}>([^<\r\n]+)', block, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def parse_extrato(source: Union[str, Path, bytes, BytesIO]) -> List[Dict[str, Any]]:
    """
    Parseia extrato Bradesco OFX conta corrente.

    Aceita path (str/Path), bytes ou BytesIO — upload via HTTP usa bytes/BytesIO.

    Returns:
        Lista de dicts com campos:
        fitid, data, valor, tipo, memo, titular_pix, trntype
    """
    if isinstance(source, (str, Path)):
        filepath = Path(source)
        if not filepath.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {filepath}")
        logger.info(f"Abrindo OFX: {filepath}")
        raw = filepath.read_bytes()
    elif isinstance(source, bytes):
        logger.info("Abrindo OFX: <bytes>")
        raw = source
    elif isinstance(source, BytesIO):
        logger.info("Abrindo OFX: <BytesIO>")
        raw = source.read()
    else:
        raise TypeError(f"parse_extrato: tipo de source nao suportado: {type(source).__name__}")
    text = None
    for enc in ('latin-1', 'cp1252', 'utf-8', 'iso-8859-1'):
        try:
            text = raw.decode(enc)
            logger.debug(f"OFX encoding: {enc}")
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = raw.decode('latin-1', errors='replace')

    # Extrair todos os blocos <STMTTRN>
    blocos = re.findall(r'<STMTTRN>(.*?)</STMTTRN>', text, re.DOTALL | re.IGNORECASE)
    logger.info(f"OFX: {len(blocos)} transações encontradas")

    results = []
    for bloco in blocos:
        trntype = _extract_tag(bloco, 'TRNTYPE')
        dtposted = _extract_tag(bloco, 'DTPOSTED')
        trnamt = _extract_tag(bloco, 'TRNAMT')
        fitid = _extract_tag(bloco, 'FITID')
        memo = _extract_tag(bloco, 'MEMO')

        data = _parse_data(dtposted)
        valor = _parse_valor(trnamt)
        tipo = classificar_transacao(memo, trntype)
        titular_pix = extrair_titular_pix(memo) if 'PIX' in tipo else ''

        record = {
            "fitid": fitid,
            "data": data,
            "valor": valor,
            "tipo": tipo,
            "memo": memo,
            "titular_pix": titular_pix,
            "trntype": trntype,
        }
        results.append(record)
        logger.debug(f"  {data} | {valor:>12.2f} | {tipo:<20} | {memo[:40]}")

    logger.info(f"Parse OFX concluído: {len(results)} transações")
    return results


_RE_BANKID = re.compile(rb"<BANKID>\s*(\d+)", re.I)
_RE_ACCTID = re.compile(rb"<ACCTID>\s*(\d+)", re.I)
_RE_BALAMT = re.compile(r"<LEDGERBAL>\s*<BALAMT>\s*([-\d.,]+)", re.I)
_RE_DTASOF = re.compile(r"<LEDGERBAL>.*?<DTASOF>\s*(\d{8,14})", re.I | re.DOTALL)


def extract_saldo(source: Union[str, Path, bytes, BytesIO]) -> Dict[str, Any] | None:
    """
    Extrai saldo final e data de referência do bloco <LEDGERBAL> do OFX.
    Retorna None se não encontrar.

    Returns: {"saldo": float, "data_referencia": "YYYY-MM-DD"}
    """
    if isinstance(source, (str, Path)):
        raw = Path(source).read_bytes()
    elif isinstance(source, bytes):
        raw = source
    elif isinstance(source, BytesIO):
        raw = source.read()
    else:
        raise TypeError(f"extract_saldo: tipo nao suportado: {type(source).__name__}")

    text = None
    for enc in ('latin-1', 'cp1252', 'utf-8', 'iso-8859-1'):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = raw.decode('latin-1', errors='replace')

    m_bal = _RE_BALAMT.search(text)
    if not m_bal:
        return None
    saldo_str = m_bal.group(1).strip().replace('.', '').replace(',', '.')
    try:
        saldo = float(saldo_str)
    except ValueError:
        return None

    m_dt = _RE_DTASOF.search(text)
    data_ref = None
    if m_dt:
        raw_dt = m_dt.group(1)
        if len(raw_dt) >= 8:
            data_ref = f"{raw_dt[0:4]}-{raw_dt[4:6]}-{raw_dt[6:8]}"

    return {"saldo": saldo, "data_referencia": data_ref}


def extract_bank_account(ofx_bytes: bytes) -> tuple[str, str]:
    """
    Extrai BANKID (banco) e ACCTID (conta) do header do OFX.
    Usa para roteamento: qual conta_bancaria do DB esse extrato pertence.

    Raises:
        ValueError: se BANKID ou ACCTID não forem encontrados.
    """
    m_bank = _RE_BANKID.search(ofx_bytes)
    if not m_bank:
        raise ValueError("BANKID não encontrado no OFX")
    m_acct = _RE_ACCTID.search(ofx_bytes)
    if not m_acct:
        raise ValueError("ACCTID não encontrado no OFX")
    return m_bank.group(1).decode(), m_acct.group(1).decode()
