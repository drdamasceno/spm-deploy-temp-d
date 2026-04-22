"""
Parser de extrato Unicred PDF ("para simples conferência").

Formato de cabeçalho:
  COOPERATIVA 544 - COOPERATIVA DE CREDITO UNICRED
  CONTA: 6688055
  CLIENTE: SOCIEDADE PARANAENSE DE MEDICINA LTDA
  EXTRATO DE CONTA CORRENTE PARA SIMPLES CONFERÊNCIA EM DD/MM/YYYY HH:MM
  PERÍODO DE DD/MM/YYYY A DD/MM/YYYY
  SALDO ANTERIOR: 0,00

Formato de linha de transação (layout fixo):
  DATA_MOV  ID_DOC  HISTÓRICO  LANÇAMENTO(R$)  SALDO(R$)

pdfplumber extrai o texto linha a linha. Quebras de linha naturais podem
separar o valor do HISTÓRICO — usar lookahead para reconstruir.
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Union

import pdfplumber

logger = logging.getLogger(__name__)


class NaturezaLancamento(str, Enum):
    PIX_CREDITO = "PIX_CREDITO"
    PIX_DEBITO = "PIX_DEBITO"
    PIX_TEF = "PIX_TEF"
    LIQUIDACAO_TITULO = "LIQUIDACAO_TITULO"
    CONVENIO = "CONVENIO"
    INTEGRALIZACAO_CAPITAL = "INTEGRALIZACAO_CAPITAL"
    ARRECADACAO = "ARRECADACAO"
    TARIFA_CONTA = "TARIFA_CONTA"
    ESTORNO = "ESTORNO"
    OUTRO = "OUTRO"


@dataclass
class MetadadosExtratoUnicred:
    banco: str = "UNICRED"
    conta: Optional[str] = None
    cliente_razao_social: Optional[str] = None
    periodo_inicio: Optional[str] = None  # YYYY-MM-DD
    periodo_fim: Optional[str] = None
    saldo_anterior: float = 0.0
    saldo_final: float = 0.0


@dataclass
class TransacaoUnicredParsed:
    data_movimento: str          # YYYY-MM-DD
    id_doc: Optional[str]
    historico: str
    valor: float                 # negativo = débito, positivo = crédito
    saldo: float
    natureza: NaturezaLancamento = NaturezaLancamento.OUTRO
    titular_pix: Optional[str] = None
    linha_numero: int = 0


class UnicredParser:
    """Parser de PDF Unicred com lookahead para quebras de linha."""

    _RE_DATA = re.compile(r"^(\d{2}/\d{2}/\d{4})\s+")
    _RE_SALDO_ANTERIOR = re.compile(r"SALDO\s+ANTERIOR:\s*([\d\.,]+)", re.I)
    _RE_PERIODO = re.compile(r"PER[IÍ]ODO\s+DE\s+(\d{2}/\d{2}/\d{4})\s+A\s+(\d{2}/\d{2}/\d{4})", re.I)
    _RE_CONTA = re.compile(r"CONTA:\s*(\d+)", re.I)
    _RE_CLIENTE = re.compile(r"CLIENTE:\s*([^\n]+)", re.I)
    _RE_SALDO_FINAL = re.compile(r"Saldo\s+em\s+\d{2}/\d{2}/\d{4}\s+([\d\.,]+)", re.I)

    # Padrão de linha: DATA ID HISTÓRICO ... VALOR SALDO
    # VALOR pode ter sinal negativo; SALDO sempre positivo/zero
    # Obs: quando a linha quebra entre sinal e valor ("... -\n 2.250,00 SALDO"),
    # o lookahead junta com espaço no meio -> permitimos "- " entre sinal e dígitos.
    _RE_LINHA = re.compile(
        r"^(\d{2}/\d{2}/\d{4})\s+"              # data
        r"(\S+)\s+"                               # id_doc
        r"(.+?)\s+"                               # histórico (non-greedy)
        r"(-?\s*[\d\.]+,\d{2})\s+"                # valor (sinal pode estar solto)
        r"([\d\.]+,\d{2})\s*$"                    # saldo
    )

    def extrair_metadados(self, arquivo: Union[str, Path, bytes]) -> MetadadosExtratoUnicred:
        texto = self._extrair_texto_completo(arquivo)
        meta = MetadadosExtratoUnicred()

        m = self._RE_CONTA.search(texto)
        meta.conta = m.group(1) if m else None

        m = self._RE_CLIENTE.search(texto)
        if m:
            meta.cliente_razao_social = m.group(1).strip()

        m = self._RE_PERIODO.search(texto)
        if m:
            meta.periodo_inicio = self._parse_data(m.group(1))
            meta.periodo_fim = self._parse_data(m.group(2))

        m = self._RE_SALDO_ANTERIOR.search(texto)
        if m:
            meta.saldo_anterior = self._parse_valor(m.group(1))

        m = self._RE_SALDO_FINAL.search(texto)
        if m:
            meta.saldo_final = self._parse_valor(m.group(1))

        return meta

    def parse(self, arquivo: Union[str, Path, bytes]) -> List[TransacaoUnicredParsed]:
        texto = self._extrair_texto_completo(arquivo)
        linhas_raw = texto.split("\n")
        transacoes: List[TransacaoUnicredParsed] = []

        i = 0
        while i < len(linhas_raw):
            linha = linhas_raw[i].strip()
            if not linha or not self._RE_DATA.match(linha):
                i += 1
                continue

            # Tenta match completo na linha única
            m = self._RE_LINHA.match(linha)
            linha_combinada = linha
            # Lookahead: junta próxima linha se necessário (valor quebra de linha)
            if not m and i + 1 < len(linhas_raw):
                combinada = f"{linha} {linhas_raw[i + 1].strip()}"
                m = self._RE_LINHA.match(combinada)
                if m:
                    linha_combinada = combinada
                    i += 1  # consome a próxima linha também

            if not m:
                logger.warning("Linha Unicred não parseada: %s", linha[:120])
                i += 1
                continue

            data_raw, id_doc, historico, valor_raw, saldo_raw = m.groups()
            tx = TransacaoUnicredParsed(
                data_movimento=self._parse_data(data_raw),
                id_doc=id_doc,
                historico=historico.strip(),
                valor=self._parse_valor(valor_raw),
                saldo=self._parse_valor(saldo_raw),
                linha_numero=i + 1,
            )
            tx.natureza = self._classificar_natureza(id_doc, historico)
            tx.titular_pix = self._extrair_titular(historico)
            transacoes.append(tx)
            i += 1

        return transacoes

    # ------------------- helpers -------------------

    def _extrair_texto_completo(self, arquivo) -> str:
        paginas = []
        if isinstance(arquivo, (str, Path)):
            with pdfplumber.open(arquivo) as pdf:
                for p in pdf.pages:
                    paginas.append(p.extract_text() or "")
        else:
            from io import BytesIO
            with pdfplumber.open(BytesIO(arquivo)) as pdf:
                for p in pdf.pages:
                    paginas.append(p.extract_text() or "")
        return "\n".join(paginas)

    @staticmethod
    def _parse_data(s: str) -> str:
        d, m, y = s.split("/")
        return f"{y}-{m}-{d}"

    @staticmethod
    def _parse_valor(s: str) -> float:
        # "55.473,33" -> 55473.33 ; "-2.000,00" -> -2000.00 ; "- 2.250,00" -> -2250.00
        s = s.replace(" ", "").replace(".", "").replace(",", ".")
        return float(s)


def _classificar_natureza(self, id_doc: str, historico: str) -> "NaturezaLancamento":
    hist_up = historico.upper()
    id_up = (id_doc or "").upper()
    if "ESTORNO PIX PAGO" in hist_up or "CRD DEVPIX" in id_up or "CRED REC DEV PIX" in hist_up:
        return NaturezaLancamento.ESTORNO
    if "CRED PIX" in id_up or "CRED RECEBIMENTO PIX" in hist_up:
        return NaturezaLancamento.PIX_CREDITO
    if "TRANSF TEF PIX" in hist_up:
        return NaturezaLancamento.PIX_TEF
    if "DEB PIX" in id_up or "PGTO PIX" in id_up or "DEBITO TRANSF PIX" in hist_up or "DEBITO PAGAMENTO PIX" in hist_up:
        return NaturezaLancamento.PIX_DEBITO
    if "LIQ TIT" in hist_up:
        return NaturezaLancamento.LIQUIDACAO_TITULO
    if "ARREC CONVENIO" in hist_up or "CONVÊNIO" in hist_up:
        return NaturezaLancamento.CONVENIO
    if "INTEGR PARC CAPIT" in hist_up:
        return NaturezaLancamento.INTEGRALIZACAO_CAPITAL
    if hist_up.startswith("PJ CONTA PJ"):
        return NaturezaLancamento.TARIFA_CONTA
    return NaturezaLancamento.OUTRO


def _extrair_titular(self, historico: str) -> Optional[str]:
    # Titular vem entre parênteses no final: "... PIX(NOME DO TITULAR)"
    # Limpa marcadores `(cid:N)` que o pdfplumber deixa no texto — representam
    # caracteres especiais (tabs, símbolos), NÃO são nomes de titular.
    cleaned = re.sub(r"\(cid:\d+\)", "", historico)
    m = re.search(r"\(([^)]+)\)", cleaned)
    if not m:
        return None
    nome = m.group(1).strip()
    # Rejeita se sobrou só "CID:N" ou padrões lixo curtos/numéricos
    if re.fullmatch(r"CID:\d+", nome, re.I):
        return None
    if len(nome) < 3:
        return None
    return nome


UnicredParser._classificar_natureza = _classificar_natureza
UnicredParser._extrair_titular = _extrair_titular
