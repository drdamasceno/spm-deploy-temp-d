from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from pydantic import BaseModel


class AprovarRodadaRequest(BaseModel):
    """Body vazio; aprovacao nao requer campos extras. Reservado para extensao."""
    pass


class RodadaSnapshotResponse(BaseModel):
    id: UUID
    rodada_id: UUID
    aprovada_em: datetime
    aprovada_por: UUID

    total_pp_elegivel: float
    total_conciliado: float
    percentual_conciliado: float
    qtd_transacoes: int
    qtd_registros_pp: int

    payload: Dict[str, Any]
    hash_payload: str

    created_at: datetime
