"""Parser CNAB-240 do extrato de conta corrente Unicred (banco 136).

Layout do segmento E (detalhe extrato), inferido de arquivo real
`extrato-20260505232218.cnab240` (cooperativa 544, conta 6688055):

  pos  0-2   banco                 '136'
  pos  3-6   lote                  '0001' (lotes seguintes)
  pos  7     tipo registro         '0' header arquivo, '1' header lote,
                                   '3' detalhe, '5' trailer lote
  pos  8-12  nº seq registro       '00001' (apenas tipo 3)
  pos 13     segmento              'E' = detalhe extrato
  pos 14-16  filler                espaços
  pos 17-141 ag/conta/empresa fixo (não interpretado)
  pos 142-149 data movimento       DDMMAAAA
  pos 150-167 valor                18 chars, centavos (sem decimal)
  pos 168    sinal                 'C' crédito, 'D' débito
  pos 169-175 código histórico     7 chars (ex: '2055001' = CRED PIX)
  pos 176-200 descrição curta      25 chars (ex: 'CRED RECEBIMENTO PIX     ')
  pos 201-239 descrição completa   39 chars (ex: 'CRED PIX / SOCIEDADE PARANAENSE...')

CNAB-240 segmento E **NÃO traz saldo running por linha** (diferente do PDF).
O saldo final aparece no trailer de lote (tipo 5) e é capturado em
`MetadadosExtratoUnicred.saldo_final`.

Encoding: latin-1 (cp1252) — padrão FEBRABAN para CNAB-240.

Distinção crítica do .RET retorno PIX (também CNAB-240, banco 237):
  - Aqui (extrato): segmento E, lote tipo 04 (extrato conferência).
  - Lá (retorno PIX): segmentos A+B, lote tipo 20/45 (pagamentos em lote).
  Os dois NÃO são intercambiáveis — layouts e propósitos distintos.
"""
from __future__ import annotations

import logging
from typing import List, Tuple

from backend.src.extrato_unicred import (
    MetadadosExtratoUnicred,
    NaturezaLancamento,
    TransacaoUnicredParsed,
)

logger = logging.getLogger(__name__)


def _classificar_natureza(cod_hist: str, desc_curta: str, sinal: str) -> NaturezaLancamento:
    """Mapeia (código histórico, descrição curta, sinal) para natureza_lancamento.

    Códigos observados em extratos reais Unicred 2026-04..05:
      2055001 CRED RECEBIMENTO PIX        → PIX_CREDITO
      2055003 ESTORNO PIX PAGO             → ESTORNO
      2055100 EST ARREC CONV               → ESTORNO
      1041061 DEBITO PAGAMENTO PIX         → PIX_DEBITO
      1041063 DEBITO TRANSF PIX            → PIX_DEBITO
      1041075 TRANSF TEF PIX               → PIX_TEF
      1041655 LIQ TIT - IB                 → LIQUIDACAO_TITULO
      1041723 ARREC CONVENIO               → ARRECADACAO
      1042075 INTEGR PARC CAPIT            → INTEGRALIZACAO_CAPITAL
      1046051 PJ CONTA PJ 1                → TARIFA_CONTA

    Códigos não mapeados caem em OUTRO — precisa revisão de heurística.
    """
    desc = (desc_curta or "").upper()

    # Estorno tem prioridade — pode aparecer em qualquer código histórico
    if "ESTORNO" in desc or "EST ARREC" in desc:
        return NaturezaLancamento.ESTORNO

    if cod_hist in ("2055001",):
        return NaturezaLancamento.PIX_CREDITO
    if cod_hist in ("1041063", "1041061"):
        return NaturezaLancamento.PIX_DEBITO
    if cod_hist == "1041075":
        return NaturezaLancamento.PIX_TEF
    if cod_hist == "1041655":
        return NaturezaLancamento.LIQUIDACAO_TITULO
    if cod_hist == "1041723":
        return NaturezaLancamento.ARRECADACAO
    if cod_hist == "1042075":
        return NaturezaLancamento.INTEGRALIZACAO_CAPITAL
    if cod_hist == "1046051":
        return NaturezaLancamento.TARIFA_CONTA

    # Fallback por descrição
    if "ARREC" in desc:
        return NaturezaLancamento.ARRECADACAO
    if "INTEGR" in desc or "CAPIT" in desc:
        return NaturezaLancamento.INTEGRALIZACAO_CAPITAL
    if "TARIFA" in desc or "PJ CONTA" in desc:
        return NaturezaLancamento.TARIFA_CONTA
    if "PIX" in desc:
        return NaturezaLancamento.PIX_CREDITO if sinal == "C" else NaturezaLancamento.PIX_DEBITO
    return NaturezaLancamento.OUTRO


def _extrair_titular(desc_completa: str) -> str | None:
    """Extrai titular após o primeiro '/' na descrição completa.

    Padrões observados:
      'CRED PIX / SOCIEDADE PARANAENSE DE MEDI' → 'SOCIEDADE PARANAENSE DE MEDI'
      'DEB PIX / FD GESTAO INTELIGENTE DE NEGO' → 'FD GESTAO INTELIGENTE DE NEGO'
      'PGTO PIX / NETDIGITAL TELECOMUNICACOES'  → 'NETDIGITAL TELECOMUNICACOES'
      '3709232600 / Plano de Saude Nicolle Rei' → 'Plano de Saude Nicolle Rei'
      'Convenio'                                → None (sem '/')
    """
    if "/" not in desc_completa:
        return None
    _, _, titular = desc_completa.partition("/")
    titular = titular.strip()
    return titular or None


def _eh_cnab240_unicred(raw: bytes) -> bool:
    """Heurística leve: primeira linha tem ≥240 chars e começa com '136' + '0000' (header arquivo)."""
    if len(raw) < 240:
        return False
    try:
        head = raw[:300].decode("latin-1", errors="strict")
    except UnicodeDecodeError:
        return False
    first = head.split("\n", 1)[0].rstrip("\r")
    return len(first) >= 240 and first.startswith("136") and first[3:7] == "0000" and first[7] == "0"


def parse_extrato_unicred_cnab240(raw: bytes) -> Tuple[MetadadosExtratoUnicred, List[TransacaoUnicredParsed]]:
    """Parsea arquivo CNAB-240 do extrato Unicred. Retorna (metadados, transações)."""
    text = raw.decode("latin-1")
    linhas = text.splitlines()

    meta = MetadadosExtratoUnicred()
    transacoes: List[TransacaoUnicredParsed] = []

    for linha_num, linha in enumerate(linhas, 1):
        if len(linha) < 240:
            # Tolerar linhas com trailing trim ou padding ausente
            linha = linha.ljust(240)
        if linha[0:3] != "136":
            continue  # ignora linhas que não são Unicred (improvável)

        lote = linha[3:7]
        tipo_reg = linha[7]

        # Header arquivo (lote 0000, tipo 0)
        if lote == "0000" and tipo_reg == "0":
            # Conta da empresa: extrai do bloco de identificação fixo (heurística simples)
            # Pos 17-30 = banco/CNPJ, depois ag+conta. AG é '1605' e conta '6688055' no caso real.
            # Não crítico — saldo_final vem do trailer; conta_id já chega via API param.
            continue

        # Header lote (tipo 1, segmento E indica extrato)
        # Período de início é derivado do min(data_movimento) das transações
        # após o loop — posição exata no header varia por release Unicred e
        # confiar no campo dá string corrompida (visto em arquivo real 2026-05).
        if tipo_reg == "1":
            continue

        # Detalhe (tipo 3, segmento E)
        if tipo_reg == "3":
            if linha[13] != "E":
                continue  # outros segmentos ignorados (não esperados em extrato Unicred)

            data_str = linha[142:150]
            valor_str = linha[150:168]
            sinal = linha[168]
            cod_hist = linha[169:176].strip()
            desc_curta = linha[176:201].strip()
            desc_compl = linha[201:240].rstrip()

            try:
                if not data_str.isdigit() or len(data_str) != 8:
                    logger.warning(f"linha {linha_num}: data inválida '{data_str}'")
                    continue
                data_iso = f"{data_str[4:8]}-{data_str[2:4]}-{data_str[0:2]}"
                valor_centavos = int(valor_str)
            except (ValueError, IndexError) as e:
                logger.warning(f"linha {linha_num}: falha parse ({e})")
                continue

            valor_reais = valor_centavos / 100.0
            if sinal == "D":
                valor_reais = -valor_reais
            elif sinal != "C":
                logger.warning(f"linha {linha_num}: sinal inesperado '{sinal}', tratando como crédito")

            historico = f"{desc_curta} / {desc_compl}".strip(" /")
            titular = _extrair_titular(desc_compl)
            natureza = _classificar_natureza(cod_hist, desc_curta, sinal)

            transacoes.append(TransacaoUnicredParsed(
                data_movimento=data_iso,
                id_doc=cod_hist or None,
                historico=historico,
                valor=valor_reais,
                saldo=0.0,  # CNAB segmento E não traz saldo running por linha
                natureza=natureza,
                titular_pix=titular,
                linha_numero=linha_num,
            ))
            continue

        # Trailer lote (tipo 5) — captura saldo final e período fim
        if tipo_reg == "5":
            # Layout do trailer Unicred (heurística — pode variar):
            # pos 142-149: data fim (DDMMAAAA)
            # pos 150-167: saldo final em centavos
            # pos 168    : sinal saldo (CF=Credor Final, DF=Devedor Final → 'C' ou 'D')
            try:
                data_fim_str = linha[142:150]
                if data_fim_str.isdigit():
                    meta.periodo_fim = f"{data_fim_str[4:8]}-{data_fim_str[2:4]}-{data_fim_str[0:2]}"

                saldo_str = linha[150:168]
                if saldo_str.isdigit():
                    saldo_centavos = int(saldo_str)
                    saldo_reais = saldo_centavos / 100.0
                    sinal_saldo = linha[168] if len(linha) > 168 else "C"
                    if sinal_saldo == "D":
                        saldo_reais = -saldo_reais
                    meta.saldo_final = saldo_reais
            except (ValueError, IndexError):
                pass
            continue

    meta.banco = "UNICRED"
    # periodo_inicio derivado do mínimo das transações (mais robusto que header lote)
    if transacoes and not meta.periodo_inicio:
        meta.periodo_inicio = min(t.data_movimento for t in transacoes)
    if transacoes and not meta.periodo_fim:
        meta.periodo_fim = max(t.data_movimento for t in transacoes)
    return meta, transacoes


def eh_cnab240_unicred(raw: bytes) -> bool:
    """Detecção pública para dispatcher PDF vs CNAB."""
    return _eh_cnab240_unicred(raw)
