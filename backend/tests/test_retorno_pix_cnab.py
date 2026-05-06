"""Testes do parser CNAB-240 retorno PIX (Bradesco).

Usa amostra real anonimizada da remessa de 30/04/2026 (R$ 512.767,40, 58 PIX,
conta SPM 0566060000000229822). Validar contra o trailer do arquivo é a melhor
defesa contra bug de slicing posicional.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from textwrap import dedent

import pytest

from backend.src.retorno_pix_cnab import (
    parse_retorno_pix,
    PagamentoPIX,
    descrever_ocorrencia,
)


SAMPLE_RET = Path(__file__).parent / "fixtures" / "retorno_pix_sample.RET"


def _retorno_minimo_real():
    """Conteúdo CNAB-240 de retorno PIX com 1 par A+B, baseado em layout real."""
    # Linha de 240 chars exatos. Pago = R$ 6.360,00 → 636000 centavos.
    # Layout: ...NOME(30c)...ID_EMPRESA(20c)DATA(8c)BRL+ZEROS(15)+VALOR(15)+PGIT462+NOSSO(13)+DATAEF(8)+EFET(15)+...
    nome = "CLINICA MEDICA TESTE LTDA     "  # 30 chars
    id_empresa = "26043011471143598019"  # 20 chars
    data = "30042026"  # DDMMYYYY
    valor_zeros = "0" * 15
    valor_instr = "000000000636000"  # R$ 6.360,00 em centavos (15 chars)
    pgit = "PGIT"
    tipo_serv = "462"
    nosso = "0000000008648"  # 13 chars
    data_efet = "00000000"  # 8 chars (zerado quando PIX é instantâneo)
    valor_efet = "000000000636000"  # 15 chars
    # prefix do segmento A
    seg_a_prefix = "237" + "0001" + "3" + "00001" + "A" + "00000900000000 000000000000  "
    seg_a_meio = nome + id_empresa + data + "BRL" + valor_zeros + valor_instr + pgit + tipo_serv + nosso + data_efet + valor_efet
    seg_a = seg_a_prefix + seg_a_meio
    # ocorrência no fim
    seg_a = seg_a + " " * (230 - len(seg_a)) + "00005CC   0BD   "
    seg_a = seg_a[:240].ljust(240)

    # Segmento B: chave PIX por CNPJ (tipo '03', prefixo '2' + 14 dig)
    seg_b_prefix = "237" + "0001" + "3" + "00002" + "B" + "03 "
    cnpj = "62318207000166"  # 14 dígitos
    seg_b_doc = "2" + cnpj  # 15 chars (prefixo '2' = PJ + 14 dig CNPJ)
    seg_b_padding = " " * 80
    seg_b_chave = cnpj + " " * 100 + "000000"
    seg_b = seg_b_prefix + seg_b_doc + seg_b_padding + seg_b_chave
    seg_b = seg_b[:240].ljust(240)

    # Header arquivo (mínimo)
    header = "237" + "0" * 4 + "0" + " " * 9 + "237" + "09232600010456 6837" + " " * 50 + "SOCIEDADE PARANAENSE DE MEDICI" + "BANCO BRADESCO SA"
    header = header[:240].ljust(240)
    header_lote = "237" + "0001" + "1" + " " * 230
    header_lote = header_lote[:240].ljust(240)
    trailer_lote = "237" + "0001" + "5" + "         " + "000002" + " " * 200
    trailer_lote = trailer_lote[:240].ljust(240)
    trailer_arq = "237" + "9999" + "9" + "         " + "000001" + "000005" + " " * 200
    trailer_arq = trailer_arq[:240].ljust(240)

    return "\n".join([header, header_lote, seg_a, seg_b, trailer_lote, trailer_arq])


def test_parse_retorno_minimo():
    """Parse sintético: 1 PIX de R$ 6.360 confirmado (ocorrência 00005)."""
    raw = _retorno_minimo_real()
    out = parse_retorno_pix(raw)
    assert len(out.pagamentos) == 1
    p = out.pagamentos[0]
    assert p.nome_favorecido.startswith("CLINICA MEDICA TESTE LTDA")
    assert p.documento_normalizado == "62318207000166"
    assert p.tipo_pessoa == "PJ"
    assert p.tipo_chave_pix == "03"
    assert p.chave_pix_literal == "62318207000166"
    assert p.valor_instr == Decimal("6360.00")
    assert p.valor_efet == Decimal("6360.00")
    assert p.data_pgto == "2026-04-30"
    assert p.ocorrencia == "00005"
    assert p.banco == "237"


def test_total_efetivo_bate_soma_individual():
    """total_efet() agrega corretamente."""
    raw = _retorno_minimo_real()
    out = parse_retorno_pix(raw)
    assert out.total_efet() == Decimal("6360.00")
    assert out.total_instr() == Decimal("6360.00")


def test_descreve_ocorrencia():
    assert "confirmado" in descrever_ocorrencia("00005").lower()
    assert "Código XYZ" == descrever_ocorrencia("XYZ")


@pytest.mark.skipif(not SAMPLE_RET.exists(), reason="fixture do retorno real não está no repo")
def test_amostra_real_30042026():
    """Sanity contra o arquivo real da remessa 30/04 (R$ 512.767,40 em 58 PIX)."""
    out = parse_retorno_pix(SAMPLE_RET)
    assert len(out.pagamentos) == 58
    assert out.total_efet() == Decimal("512767.40")
    assert all(p.banco == "237" for p in out.pagamentos)
    # todas com ocorrência 00005 (confirmado)
    assert all(p.ocorrencia == "00005" for p in out.pagamentos)
