"""Schemas Pydantic para bolso (dimensão gerencial ortogonal à natureza)."""
from enum import Enum


class BolsoTipo(str, Enum):
    SPM_OPERACIONAL = "SPM_OPERACIONAL"
    FD_VIA_SPM = "FD_VIA_SPM"
    HUGO_PESSOAL = "HUGO_PESSOAL"
    INVESTIMENTO_HUGO = "INVESTIMENTO_HUGO"


BOLSO_LABELS: dict[BolsoTipo, str] = {
    BolsoTipo.SPM_OPERACIONAL: "SPM operacional",
    BolsoTipo.FD_VIA_SPM: "Via FD",
    BolsoTipo.HUGO_PESSOAL: "Pessoal Hugo",
    BolsoTipo.INVESTIMENTO_HUGO: "Investimento Hugo",
}
