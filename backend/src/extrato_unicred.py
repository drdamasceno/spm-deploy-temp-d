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

    # Padrão de linha LAYOUT ANTIGO: DATA ID HISTÓRICO ... VALOR SALDO
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

    # Padrão LAYOUT NOVO INLINE — "DATA texto - R$ VALOR R$ SALDO"
    # Usado em transações com histórico curto (ex: "PJ CONTA PJ 1 (Doc: 600010)").
    _RE_LINHA_NOVA_INLINE = re.compile(
        r"^(\d{2}/\d{2}/\d{4})\s+"              # data
        r"(.+?)\s+"                               # histórico (non-greedy)
        r"(-?\s*R\$\s*[\d\.]+,\d{2})\s+"          # valor com prefixo R$
        r"R\$\s*([\d\.]+,\d{2})\s*$"              # saldo com prefixo R$
    )

    # Padrão LAYOUT NOVO SPLIT — "DATA - R$ VALOR R$ SALDO" (sem texto entre)
    # Quando casa, histórico é coletado nas linhas vizinhas (anterior + posterior).
    _RE_LINHA_NOVA_SPLIT = re.compile(
        r"^(\d{2}/\d{2}/\d{4})\s+"
        r"(-?\s*R\$\s*[\d\.]+,\d{2})\s+"
        r"R\$\s*([\d\.]+,\d{2})\s*$"
    )

    # Saldo final/atual no layout novo: "Saldo atual R$ 943,01"
    _RE_SALDO_ATUAL_NOVO = re.compile(r"Saldo\s+atual\s+R?\$?\s*([\d\.,]+)", re.I)
    # Cliente sem prefixo (linha do header novo): "SOCIEDADE PARANAENSE DE MEDICINA - **."
    _RE_CLIENTE_NOVO = re.compile(r"^(SOCIEDADE\s+PARANAENSE[^\n]+)", re.M)

    def extrair_metadados(self, arquivo: Union[str, Path, bytes]) -> MetadadosExtratoUnicred:
        texto = self._extrair_texto_completo(arquivo)
        meta = MetadadosExtratoUnicred()

        m = self._RE_CONTA.search(texto)
        meta.conta = m.group(1) if m else None

        m = self._RE_CLIENTE.search(texto)
        if m:
            meta.cliente_razao_social = m.group(1).strip()
        else:
            # Layout novo: cliente sem prefixo "CLIENTE:"
            m2 = self._RE_CLIENTE_NOVO.search(texto)
            if m2:
                meta.cliente_razao_social = m2.group(1).strip()

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
        else:
            # Layout novo: "Saldo atual R$ 943,01"
            m2 = self._RE_SALDO_ATUAL_NOVO.search(texto)
            if m2:
                try:
                    meta.saldo_final = self._parse_valor(m2.group(1))
                except (ValueError, AttributeError):
                    pass

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

            # 1. LAYOUT ANTIGO: tenta linha única "DATA ID HIST VALOR SALDO"
            m = self._RE_LINHA.match(linha)
            if not m and i + 1 < len(linhas_raw):
                combinada = f"{linha} {linhas_raw[i + 1].strip()}"
                m = self._RE_LINHA.match(combinada)
                if m:
                    i += 1  # consome a próxima linha também

            if m:
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
                continue

            # 2. LAYOUT NOVO INLINE: "DATA texto - R$ VALOR R$ SALDO"
            #    Mas só conta se histórico for substantivo (não apenas sinal solto).
            #    Linhas como "DATA - R$ 80,00 R$ 76.390,88" caem pra SPLIT abaixo
            #    pra preservar o sinal negativo no valor.
            m2 = self._RE_LINHA_NOVA_INLINE.match(linha)
            if m2:
                hist_check = m2.group(2).strip()
                if hist_check in ("-", "—", "") or len(hist_check) < 2:
                    m2 = None
            if m2:
                data_raw, historico, valor_raw, saldo_raw = m2.groups()
                tx = TransacaoUnicredParsed(
                    data_movimento=self._parse_data(data_raw),
                    id_doc=None,
                    historico=historico.strip(),
                    valor=self._parse_valor(valor_raw),
                    saldo=self._parse_valor(saldo_raw),
                    linha_numero=i + 1,
                )
                tx.natureza = self._classificar_natureza(None, historico)
                tx.titular_pix = self._extrair_titular(historico)
                transacoes.append(tx)
                i += 1
                continue

            # 3. LAYOUT NOVO SPLIT: "DATA - R$ VALOR R$ SALDO" (sem texto entre)
            #    Histórico vem fragmentado nas linhas adjacentes — coletar.
            m3 = self._RE_LINHA_NOVA_SPLIT.match(linha)
            if m3:
                data_raw, valor_raw, saldo_raw = m3.groups()
                historico = self._coletar_historico_adjacente(linhas_raw, i)
                tx = TransacaoUnicredParsed(
                    data_movimento=self._parse_data(data_raw),
                    id_doc=None,
                    historico=historico,
                    valor=self._parse_valor(valor_raw),
                    saldo=self._parse_valor(saldo_raw),
                    linha_numero=i + 1,
                )
                tx.natureza = self._classificar_natureza(None, historico)
                tx.titular_pix = self._extrair_titular(historico)
                transacoes.append(tx)
                i += 1
                continue

            logger.warning("Linha Unicred não parseada: %s", linha[:120])
            i += 1

        return transacoes

    # Cabeçalhos que indicam INÍCIO de uma nova transação. Se a linha
    # posterior à DATA começa com um desses, pertence à PRÓXIMA transação,
    # não à atual — então paramos a coleta de histórico aqui.
    _CABECALHOS_NOVA_TX = (
        "CREDITO RECEBIMENTO", "DEBITO TRANSF", "DEBITO TRANSFERENCIA",
        "DEBITO PAGAMENTO", "LIQUIDACAO DE TITULO", "ARRECADACAO DE",
        "INTEGRALIZACAO PARCIAL", "TRANSFERENCIA TEF", "ESTORNO",
        "PJ CONTA PJ",
    )

    def _coletar_historico_adjacente(self, linhas: List[str], idx: int) -> str:
        """Para layout novo split, coleta o histórico fragmentado nas linhas
        anteriores e posteriores à linha de DATA+VALOR+SALDO.

        Pattern típico observado no PDF:
            linha N-1: 'CREDITO RECEBIMENTO DE PIX ( Doc.: CRED PIX /'
            linha N:   '07/04/2026 R$ 55.473,33 R$ 55.473,33'
            linha N+1: 'SOCIEDADE PARANAENSE DE MEDICINA LTDA )'

        Lookbehind: 1 linha (cabeçalho da tx atual). Lookahead: 1 linha,
        mas SÓ se não for cabeçalho de outra transação — pdfplumber pode
        inserir o cabeçalho da próxima entre fragmentos da atual.
        """
        partes = []
        # Linha anterior — uma só (cabeçalho da própria transação atual)
        if idx > 0:
            l_ant = linhas[idx - 1].strip()
            if l_ant and not self._RE_DATA.match(l_ant) and not self._eh_ruido(l_ant):
                partes.append(l_ant)
        # Linha posterior — uma só, e apenas se não for cabeçalho de OUTRA transação
        if idx + 1 < len(linhas):
            l_post = linhas[idx + 1].strip()
            if (
                l_post
                and not self._RE_DATA.match(l_post)
                and not self._eh_ruido(l_post)
                and not any(l_post.upper().startswith(c) for c in self._CABECALHOS_NOVA_TX)
            ):
                partes.append(l_post)
        return " ".join(partes).strip()

    @staticmethod
    def _eh_ruido(linha: str) -> bool:
        """True se a linha é footer/header de página, cabeçalho de tabela etc."""
        l = linha.strip()
        if not l:
            return True
        ruido_markers = (
            "Pág.", "Página", "CENTRAL DE RELACIONAMENTO",
            "Data Lançamentos Valor", "Saldo no final",
            "Lançamentos futuros",
        )
        return any(m in l for m in ruido_markers)

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
        # Layout novo Unicred PDF: "R$ 55.473,33" ou "- R$ 51,50" — tolera prefixo R$.
        s = s.replace(" ", "").replace("R$", "").replace(".", "").replace(",", ".")
        return float(s)


def _classificar_natureza(self, id_doc: str, historico: str) -> "NaturezaLancamento":
    hist_up = historico.upper()
    id_up = (id_doc or "").upper()
    # ESTORNO tem prioridade — pode aparecer em qualquer combinação
    if (
        "ESTORNO PIX PAGO" in hist_up
        or "CRD DEVPIX" in id_up
        or "CRED REC DEV PIX" in hist_up
        or "ESTORNO" in hist_up
        or "EST ARREC" in hist_up
        or "CREDITO RECEBIMENTO DE DEVOLUCAO" in hist_up
    ):
        return NaturezaLancamento.ESTORNO
    if (
        "CRED PIX" in id_up
        or "CRED RECEBIMENTO PIX" in hist_up
        or "CREDITO RECEBIMENTO DE PIX" in hist_up
        or "CREDITO RECEBIMENTO PIX" in hist_up
    ):
        return NaturezaLancamento.PIX_CREDITO
    if "TRANSF TEF PIX" in hist_up or "TRANSFERENCIA TEF PIX" in hist_up:
        return NaturezaLancamento.PIX_TEF
    if (
        "DEB PIX" in id_up
        or "PGTO PIX" in id_up
        or "DEBITO TRANSF PIX" in hist_up
        or "DEBITO PAGAMENTO PIX" in hist_up
        or "DEBITO TRANSFERENCIA PIX" in hist_up
    ):
        return NaturezaLancamento.PIX_DEBITO
    if "LIQ TIT" in hist_up or "LIQUIDACAO DE TITULO" in hist_up:
        return NaturezaLancamento.LIQUIDACAO_TITULO
    if "ARREC CONVENIO" in hist_up or "ARRECADACAO DE CONVENIOS" in hist_up or "CONVÊNIO" in hist_up or "CONVENIO" in hist_up:
        return NaturezaLancamento.CONVENIO
    if "INTEGR PARC CAPIT" in hist_up or "INTEGRALIZACAO PARCIAL DE CAPITAL" in hist_up:
        return NaturezaLancamento.INTEGRALIZACAO_CAPITAL
    if hist_up.startswith("PJ CONTA PJ") or "PJ CONTA PJ" in hist_up:
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
