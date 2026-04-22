from __future__ import annotations

from uuid import UUID
from typing import List, Optional

from pydantic import BaseModel


class ExtratoPeriodo(BaseModel):
    inicio: str  # YYYY-MM-DD
    fim: str    # YYYY-MM-DD


class UploadRodadaResponse(BaseModel):
    rodada_id: UUID
    pp_competencias: List[str]   # ["2026-02", "2026-03"]
    extrato_periodo: ExtratoPeriodo
    total_registros_pp: int
    total_transacoes: int


class RodadaListItem(BaseModel):
    id: UUID
    periodo_extrato_inicio: str
    periodo_extrato_fim: str
    pp_competencias: List[str]
    status: str
    criado_em: str
    criado_por: Optional[UUID] = None
