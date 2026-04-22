from datetime import date
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


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


class ResultadoUploadOrcamento(BaseModel):
    orcamento_id: UUID
    total_linhas_inseridas: int
    linhas_por_secao: dict[str, int]
    linhas_descartadas: int
    avisos: list[str]
