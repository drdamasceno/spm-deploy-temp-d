from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


_CNPJ_DIGITS = re.compile(r"\D")


def _normalize_cnpj(value: str) -> str:
    """Remove tudo que nao e digito e exige exatamente 14."""
    digits = _CNPJ_DIGITS.sub("", value or "")
    if len(digits) != 14:
        raise ValueError("CNPJ deve ter 14 digitos apos normalizacao")
    return digits


class ExcecaoPJCreate(BaseModel):
    prestador_id: UUID
    razao_social_autorizada: str = Field(..., min_length=1)
    cnpj: str = Field(..., description="CNPJ com ou sem mascara; normalizado para 14 digitos")
    data_aprovacao: date
    justificativa: Optional[str] = None

    @field_validator("cnpj")
    @classmethod
    def _validate_cnpj(cls, v: str) -> str:
        return _normalize_cnpj(v)

    @field_validator("razao_social_autorizada")
    @classmethod
    def _strip_razao(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("razao_social_autorizada nao pode ser vazia")
        return v


class ExcecaoPJUpdate(BaseModel):
    razao_social_autorizada: Optional[str] = None
    cnpj: Optional[str] = None
    data_aprovacao: Optional[date] = None
    justificativa: Optional[str] = None
    ativo: Optional[bool] = None

    @field_validator("cnpj")
    @classmethod
    def _validate_cnpj_opt(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return _normalize_cnpj(v)

    @field_validator("razao_social_autorizada")
    @classmethod
    def _strip_razao_opt(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("razao_social_autorizada nao pode ser vazia")
        return v


class ExcecaoPJResponse(BaseModel):
    id: UUID
    prestador_id: UUID
    razao_social_autorizada: str
    cnpj: Optional[str] = None
    data_aprovacao: date
    justificativa: Optional[str] = None
    aprovado_por: UUID
    ativo: bool
    created_at: datetime
