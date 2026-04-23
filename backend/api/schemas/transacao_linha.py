"""Schemas Pydantic para split de transação (Track B Fase D)."""
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from backend.api.schemas.bolso import BolsoTipo


class TransacaoLinhaCreate(BaseModel):
    valor: float = Field(..., description="Valor da linha. Sinal segue o da transação pai.")
    bolso: BolsoTipo
    orcamento_linha_id: Optional[UUID] = None
    empresa_pagadora_id: Optional[UUID] = None
    descricao: Optional[str] = None


class TransacaoLinhaOut(TransacaoLinhaCreate):
    id: UUID
    transacao_bancaria_id: UUID
    criado_em: str
    criado_por: Optional[UUID] = None


class SplitRequest(BaseModel):
    linhas: List[TransacaoLinhaCreate]


class SplitResponse(BaseModel):
    transacao_bancaria_id: UUID
    valor_transacao: float
    valor_soma_linhas: float
    linhas: List[TransacaoLinhaOut]
