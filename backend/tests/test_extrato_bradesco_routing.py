"""Testes da função de roteamento por conta (BANKID + ACCTID)."""
from pathlib import Path
from backend.src.extrato_bradesco import extract_bank_account

FIXTURES = Path(__file__).parent / "fixtures"
OFX_EXISTENTE = FIXTURES / "EXTRATO_POR_PERIODO_120426_221307.ofx"


def test_extract_bank_account_bradesco():
    # Assumindo que o OFX de teste já existe do trabalho anterior
    if not OFX_EXISTENTE.exists():
        import pytest
        pytest.skip("OFX fixture ausente")
    with open(OFX_EXISTENTE, "rb") as f:
        data = f.read()
    bankid, acctid = extract_bank_account(data)
    assert bankid == "0237"        # Bradesco
    assert acctid == "22982"       # Conta do extrato de exemplo


def test_extract_bank_account_raises_on_invalid():
    import pytest
    with pytest.raises(ValueError, match="BANKID"):
        extract_bank_account(b"not an ofx")
