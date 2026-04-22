from __future__ import annotations

from uuid import UUID
from typing import List, Optional

from pydantic import BaseModel


class ResumoTransacoes(BaseModel):
    match_automatico: int
    fracionado: int
    conciliado_categoria: int
    manual_pendente: int
    nao_classificado: int


class ResumoRegistrosPP(BaseModel):
    total_elegivel: int
    sem_movimento: int
    saldo_negativo: int


class ConciliarResponse(BaseModel):
    rodada_id: UUID
    resumo_transacoes: ResumoTransacoes
    resumo_registros_pp: ResumoRegistrosPP
    valor_total_pp: float
    valor_total_conciliado: float
    percentual_conciliado: float


class RegistroPPNested(BaseModel):
    id: UUID
    prestador_nome: Optional[str] = None
    contrato_nome: Optional[str] = None
    mes_competencia: str
    saldo_pp: float
    status_saldo: str


class TransacaoResultado(BaseModel):
    id: UUID
    valor: float
    data_extrato: str
    titular_pix: Optional[str] = None
    descricao: Optional[str] = None
    status_conciliacao: str
    categoria: Optional[str] = None
    registro_pp_id: Optional[UUID] = None
    registro_pp: Optional[RegistroPPNested] = None


class Pagination(BaseModel):
    page: int
    per_page: int
    total: int


class ResultadoResponse(BaseModel):
    rodada_id: UUID
    resumo_transacoes: ResumoTransacoes
    resumo_registros_pp: ResumoRegistrosPP
    valor_total_pp: float
    valor_total_conciliado: float
    percentual_conciliado: float
    transacoes: List[TransacaoResultado]
    pagination: Pagination
