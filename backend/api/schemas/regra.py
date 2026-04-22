from uuid import UUID
from pydantic import BaseModel


class RegraClassificacaoOut(BaseModel):
    id: UUID
    titular_pix_padrao: str
    orcamento_linha_id: UUID | None
    categoria_id: UUID | None
    projeto_id: UUID | None
    empresa_id: UUID | None
    confianca_base: float
    uso_count: int
    ativa: bool
    ultima_utilizacao: str | None


class RegraClassificacaoPatch(BaseModel):
    ativa: bool | None = None
    confianca_base: float | None = None
