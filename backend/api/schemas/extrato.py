from uuid import UUID
from pydantic import BaseModel


class UploadExtratoResponse(BaseModel):
    conta_id: UUID
    origem_banco: str                       # "UNICRED" | "BRADESCO"
    total_transacoes_inseridas: int
    periodo_inicio: str
    periodo_fim: str
    saldo_final: float
