"""Parser de Retorno PIX CNAB-240 (Bradesco e variantes).

Layout retorno de pagamento PIX em lote — confirma cada PIX que saiu de
remessa instruída pela empresa. Distinto do Extrato CNAB-240 (segmentos E)
e do Retorno de Cobrança (segmentos T/U).

Estrutura:
  Tipo 0 — Header do arquivo (1 linha)
  Tipo 1 — Header de lote (1 ou mais lotes)
  Tipo 3 — Detalhes (pares Segmento A + Segmento B por pagamento)
  Tipo 5 — Trailer de lote
  Tipo 9 — Trailer de arquivo

Segmento A (240 chars):
  Posição 1-3:    Banco (237 Bradesco)
  Pos 4-7:        Nº lote
  Pos 8:          Tipo registro = '3'
  Pos 9-13:       Sequencial registro no lote
  Pos 14:         'A'
  ...
  Após âncora 'BRL':
    +0..3:        'BRL'
    +3..18:       Quantidade moeda (15 chars, geralmente zeros)
    +18..33:      Valor instruído (15 chars, centavos)
    +33..37:      'PGIT' (forma de pagamento — 'PGIT' = PIX instantâneo Bradesco)
    +37..40:      Tipo de serviço (3 chars, '462' = transferência PIX terceiros)
    +40..53:      Nosso número Bradesco (13 chars)
    +53..61:      Data efetivação (8 chars DDMMYYYY ou zeros)
    +61..76:      Valor efetivamente pago (15 chars centavos)
  Antes da âncora 'BRL', recuando:
    -8..0:        Data agendamento DDMMYYYY
    -28..-8:      Nº documento empresa (20 chars — geralmente ID interno do PP)
    -58..-28:     Nome do favorecido (30 chars)

Segmento B (240 chars):
  Pos 1-13:       header igual ao A
  Pos 14:         'B'
  Pos 15-16:      Tipo de identificação chave PIX:
                    '01' = telefone, '02' = email, '03' = CPF/CNPJ
  Pos 17:         espaço
  Pos 17-32:      15 chars com prefixo '1' (PF, CPF 11 dig) ou '2' (PJ, CNPJ 14 dig)
  Pos 32+:        Chave PIX literal (telefone com +55, email, CPF ou CNPJ)
  Final:          Código de ocorrência (5 chars) + tipo conta + extras

Variantes por banco — Unicred não confirmado ainda (gerente Pamela). Caso o
layout Unicred seja diferente, ajustar `parse_retorno_pix` com `dialect=...`
ou criar parser dedicado em outro módulo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Union, Iterator


@dataclass
class PagamentoPIX:
    """Uma linha de pagamento PIX confirmada pelo banco."""
    seq: str                          # nº sequencial no lote (5 chars)
    nome_favorecido: str              # 30 chars máx (truncado pelo banco)
    documento_normalizado: str        # CPF (11) ou CNPJ (14), só dígitos
    tipo_pessoa: str                  # 'PF' | 'PJ' | '?'
    tipo_chave_pix: str               # '01' tel | '02' email | '03' doc
    chave_pix_literal: str            # tel/email/doc literal
    valor_instr: Decimal              # valor instruído (R$)
    valor_efet: Decimal               # valor efetivamente pago (R$)
    data_pgto: Optional[str]          # DDMMYYYY → YYYY-MM-DD
    nosso_numero: str                 # ID Bradesco (13 chars)
    id_documento_empresa: str         # 20 chars — ID interno do PP geralmente
    ocorrencia: str                   # código de status banco
    banco: str                        # '237' Bradesco

    def documento_formatado(self) -> str:
        """CPF/CNPJ com máscara."""
        d = self.documento_normalizado
        if len(d) == 11:
            return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
        if len(d) == 14:
            return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
        return d


@dataclass
class MetadadosRetornoPIX:
    banco: str
    convenio: Optional[str]
    empresa_cnpj: Optional[str]
    empresa_nome: Optional[str]
    qtd_lotes: int
    qtd_registros: int


@dataclass
class RetornoPIXParsed:
    metadados: MetadadosRetornoPIX
    pagamentos: List[PagamentoPIX] = field(default_factory=list)

    def total_efet(self) -> Decimal:
        return sum((p.valor_efet for p in self.pagamentos), Decimal(0))

    def total_instr(self) -> Decimal:
        return sum((p.valor_instr for p in self.pagamentos), Decimal(0))


def _parse_data_brl(ddmmyyyy: str) -> Optional[str]:
    """DDMMYYYY → YYYY-MM-DD; retorna None se vier zerado."""
    if not ddmmyyyy or ddmmyyyy == '00000000' or len(ddmmyyyy) < 8:
        return None
    return f"{ddmmyyyy[4:8]}-{ddmmyyyy[2:4]}-{ddmmyyyy[0:2]}"


def _normalize_doc(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def _parse_seg_a(line: str) -> Optional[dict]:
    """Extrai campos do Segmento A. Retorna None se layout não bater."""
    if len(line) < 14 or line[13] != 'A':
        return None
    brl_idx = line.find('BRL')
    if brl_idx < 0:
        return None
    try:
        nome = line[brl_idx - 58:brl_idx - 28].strip()
        id_empresa = line[brl_idx - 28:brl_idx - 8].strip()
        data_pgto_raw = line[brl_idx - 8:brl_idx]
        valor_instr = Decimal(line[brl_idx + 18:brl_idx + 33]) / Decimal(100)
        nosso_num = line[brl_idx + 40:brl_idx + 53].strip()
        valor_efet = Decimal(line[brl_idx + 61:brl_idx + 76]) / Decimal(100)
    except (ValueError, IndexError):
        return None

    # ocorrência: campo de 5 dígitos no final (após espaços), antes de marcadores
    ocorrencia = ''
    m = re.search(r"\s(\d{5})[A-Z]{2}\s", line)
    if m:
        ocorrencia = m.group(1)

    return {
        'seq': line[8:13],
        'nome': nome,
        'id_empresa': id_empresa,
        'data_pgto': _parse_data_brl(data_pgto_raw),
        'valor_instr': valor_instr,
        'valor_efet': valor_efet,
        'nosso_num': nosso_num,
        'ocorrencia': ocorrencia,
    }


def _parse_seg_b(line: str) -> Optional[dict]:
    """Extrai campos do Segmento B."""
    if len(line) < 14 or line[13] != 'B':
        return None
    tipo_doc = line[14:16]  # '01' tel | '02' email | '03' CPF/CNPJ
    doc_raw = line[17:32].strip()

    # prefixo '1' = PF (CPF, 11 dig), '2' = PJ (CNPJ, 14 dig)
    if doc_raw.startswith('2'):
        documento = doc_raw[1:].lstrip('0').rjust(14, '0')
        # CNPJ exige exatamente 14
        documento = doc_raw[-14:] if len(doc_raw) >= 14 else doc_raw
        documento = re.sub(r"\D", "", documento)
        documento = documento[-14:] if len(documento) >= 14 else documento
        tipo_pessoa = 'PJ'
    elif doc_raw.startswith('1'):
        documento = doc_raw[-11:]  # CPF 11 dig no fim
        tipo_pessoa = 'PF'
    else:
        documento = _normalize_doc(doc_raw)
        tipo_pessoa = '?'

    # chave PIX literal — primeiro token não-padding após pos 32
    rest = line[32:].rstrip()
    tokens = [t for t in rest.split() if t and t != '000000']
    chave_pix = tokens[0] if tokens else ''

    return {
        'tipo_doc': tipo_doc,
        'documento': documento,
        'tipo_pessoa': tipo_pessoa,
        'chave_pix': chave_pix,
    }


def _parse_header_arquivo(line: str) -> dict:
    """Extrai banco, convênio, CNPJ e nome empresa do header tipo 0."""
    banco = line[:3] if len(line) >= 3 else ''
    # CNPJ empresa ocupa 14 chars após posição 17 (Bradesco)
    cnpj_match = re.search(r"^.{17}(\d{14})", line)
    cnpj = cnpj_match.group(1) if cnpj_match else None
    # Convênio Bradesco: 6+1+13 = 20 dígitos após o CNPJ; capturamos os 20
    conv_match = re.search(rf"^.{{31}}\s*(\d{{20}})", line) if cnpj else None
    conv = conv_match.group(1) if conv_match else None
    # Nome empresa: 30 chars a partir de pos 72 (após convênio + filler)
    nome = line[72:102].strip() if len(line) >= 102 else None
    return {'banco': banco, 'cnpj': cnpj, 'convenio': conv, 'empresa_nome': nome}


def parse_retorno_pix(content: Union[str, bytes, Path]) -> RetornoPIXParsed:
    """Parse principal. Aceita path, bytes, ou string com o conteúdo bruto.

    Decoda em latin-1 (CP1252 é o usual em arquivos CNAB do Bradesco).
    """
    if isinstance(content, Path):
        raw = content.read_text(encoding='latin-1')
    elif isinstance(content, bytes):
        raw = content.decode('latin-1')
    elif isinstance(content, str):
        # heurística: se for caminho válido (curto e sem nl), lê do disco;
        # caso contrário, trata como conteúdo bruto.
        if len(content) < 1024 and '\n' not in content:
            try:
                p = Path(content)
                if p.exists():
                    raw = p.read_text(encoding='latin-1')
                else:
                    raw = content
            except OSError:
                raw = content
        else:
            raw = content
    else:
        raise ValueError(f"Tipo não suportado: {type(content)}")

    lines = raw.splitlines()
    if not lines:
        raise ValueError("Arquivo vazio")

    header = _parse_header_arquivo(lines[0])

    # Trailer de arquivo (tipo 9): última linha com tipo '9'
    qtd_lotes = 0
    qtd_registros = 0
    for line in reversed(lines):
        if len(line) >= 8 and line[7] == '9':
            try:
                qtd_lotes = int(line[17:23])
                qtd_registros = int(line[23:29])
            except (ValueError, IndexError):
                pass
            break

    pagamentos: List[PagamentoPIX] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if len(line) > 13 and line[13] == 'A':
            a = _parse_seg_a(line)
            b = None
            if i + 1 < len(lines) and len(lines[i + 1]) > 13 and lines[i + 1][13] == 'B':
                b = _parse_seg_b(lines[i + 1])
            if a and b:
                pagamentos.append(PagamentoPIX(
                    seq=a['seq'],
                    nome_favorecido=a['nome'],
                    documento_normalizado=b['documento'],
                    tipo_pessoa=b['tipo_pessoa'],
                    tipo_chave_pix=b['tipo_doc'],
                    chave_pix_literal=b['chave_pix'],
                    valor_instr=a['valor_instr'],
                    valor_efet=a['valor_efet'],
                    data_pgto=a['data_pgto'],
                    nosso_numero=a['nosso_num'],
                    id_documento_empresa=a['id_empresa'],
                    ocorrencia=a['ocorrencia'],
                    banco=header['banco'],
                ))
            i += 2
        else:
            i += 1

    return RetornoPIXParsed(
        metadados=MetadadosRetornoPIX(
            banco=header['banco'],
            convenio=header['convenio'],
            empresa_cnpj=header['cnpj'],
            empresa_nome=header['empresa_nome'],
            qtd_lotes=qtd_lotes,
            qtd_registros=qtd_registros,
        ),
        pagamentos=pagamentos,
    )


# Códigos de ocorrência Bradesco (parcial — confirmar lista completa com banco)
OCORRENCIAS_BRADESCO = {
    '00000': 'Sem erro',
    '00005': 'Pagamento PIX confirmado',  # observado em remessa 30/04 — TODOS confirmados
    'BD':    'Confirmação Bradesco',
    # adicionar conforme mapeamento real for evoluindo
}


def descrever_ocorrencia(codigo: str) -> str:
    """Descrição humana do código de ocorrência. Fallback p/ código raw."""
    return OCORRENCIAS_BRADESCO.get(codigo, f"Código {codigo}")
