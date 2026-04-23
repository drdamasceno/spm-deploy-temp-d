from datetime import date
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

from backend.api.schemas.bolso import BolsoTipo


class OrcamentoCreate(BaseModel):
    empresa_id: UUID
    competencia: str = Field(pattern=r"^\d{4}-\d{2}$")


class OrcamentoOut(BaseModel):
    id: UUID
    empresa_id: UUID
    competencia: str
    status: str
    criado_em: str


class OrcamentoLinhaOut(BaseModel):
    id: UUID
    orcamento_id: UUID
    natureza: str
    categoria_id: Optional[UUID]
    projeto_id: Optional[UUID]
    titular_cpf_cnpj: Optional[str]
    titular_razao_social: str
    contrato_id: Optional[UUID]
    valor_previsto: float
    data_previsao: Optional[date]
    observacao: Optional[str]
    bolso: BolsoTipo = BolsoTipo.SPM_OPERACIONAL
    empresa_pagadora_id: Optional[UUID] = None


class OrcamentoLinhaPatch(BaseModel):
    """Campos mutaveis de uma linha de orcamento (PATCH parcial).

    Campos ausentes no payload nao sao alterados. Para limpar um campo
    opcional (ex.: categoria_id), enviar explicitamente null.
    """
    titular_razao_social: Optional[str] = None
    titular_cpf_cnpj: Optional[str] = None
    categoria_id: Optional[str] = None
    projeto_id: Optional[str] = None
    contrato_id: Optional[UUID] = None
    valor_previsto: Optional[float] = None
    data_previsao: Optional[str] = None
    observacao: Optional[str] = None
    bolso: Optional[BolsoTipo] = None
    empresa_pagadora_id: Optional[UUID] = None


class ResultadoUploadOrcamento(BaseModel):
    orcamento_id: UUID
    total_linhas_inseridas: int
    linhas_por_secao: dict[str, int]
    linhas_descartadas: int
    avisos: list[str]
