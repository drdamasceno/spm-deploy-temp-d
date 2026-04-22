"""Testes do parser de Local → (uf, cidade, local_sub)."""
import pytest
from backend.api.routers.rodadas import _parse_local_pp, _normaliza_cidade


def test_parse_simples():
    r = _parse_local_pp("SP - IGUAPE - UBS RURAL - ESF - SPM")
    assert r == ("SP", "IGUAPE", "UBS RURAL - ESF - SPM")


def test_parse_traco_longo():
    r = _parse_local_pp("SP – SERTÃOZINHO – UBS JAMAICA")
    assert r == ("SP", "SERTÃOZINHO", "UBS JAMAICA")


def test_parse_apenas_uf_cidade():
    r = _parse_local_pp("PR - LONDRINA")
    assert r == ("PR", "LONDRINA", None)


def test_parse_mixed_separators():
    r = _parse_local_pp("MG - UNAI – HOSPITAL MUNC. - PEDIATRIA")
    assert r == ("MG", "UNAI", "HOSPITAL MUNC. - PEDIATRIA")


def test_parse_empty():
    with pytest.raises(ValueError, match="Local vazio"):
        _parse_local_pp("")


def test_parse_sem_cidade():
    with pytest.raises(ValueError, match="não tem UF e cidade"):
        _parse_local_pp("SP")


def test_normaliza_acento_match():
    assert _normaliza_cidade("SERTÃOZINHO") == "SERTAOZINHO"
    assert _normaliza_cidade("SÃO JOÃO") == "SAO JOAO"
    assert _normaliza_cidade("IGUAPE") == "IGUAPE"
