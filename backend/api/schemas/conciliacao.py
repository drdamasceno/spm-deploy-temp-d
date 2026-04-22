from uuid import UUID
from pydantic import BaseModel


class SugestaoOut(BaseModel):
    transacao_id: UUID
    orcamento_linha_id: UUID
    confianca: float
    origem: str
    valor_aplicado: float


class ConciliacaoCreate(BaseModel):
    transacao_id: UUID
    orcamento_linha_id: UUID
    valor_aplicado: float
    confianca: float | None = None
    origem: str                              # "REGRA" | "SIMILARIDADE" | "VALOR" | "MANUAL"


class ConciliacaoOut(BaseModel):
    id: UUID
    transacao_id: UUID
    orcamento_linha_id: UUID
    valor_aplicado: float
    confianca: float | None
    origem: str
    aprovada_em: str
