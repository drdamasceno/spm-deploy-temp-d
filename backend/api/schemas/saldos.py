"""Schemas para /saldos e /aplicacoes — Track D."""
from datetime import date
from typing import Optional, Literal
from pydantic import BaseModel, Field


class ContaLiquidezItem(BaseModel):
    """1 linha de conta corrente no dashboard de liquidez."""
    conta_id: str
    banco: str
    agencia: str
    conta: str
    finalidade: str
    saldo_valor: float
    data_referencia: Optional[date]
    origem: Optional[str]  # BRADESCO_OFX | UNICRED_PDF | MANUAL
    dias_desatualizado: Optional[int]  # null se nunca atualizado


class AplicacaoOut(BaseModel):
    id: str
    nome: str
    tipo: str
    valor_atual: float
    data_atualizacao: date
    modo: Literal["AUTOMATICA", "MANUAL"]
    instituicao: Optional[str]
    rentabilidade: Optional[str]
    data_vencimento: Optional[date]
    liquidez: Optional[str]
    observacoes: Optional[str]
    ativo: bool = True


class AplicacaoCreate(BaseModel):
    nome: str = Field(min_length=1)
    tipo: Literal["CDB", "LCA", "LCI", "FUNDO", "POUPANCA", "TESOURO", "ACOES", "FII", "OUTROS"]
    valor_atual: float = Field(ge=0)
    data_atualizacao: Optional[date] = None
    modo: Literal["AUTOMATICA", "MANUAL"]
    instituicao: Optional[str] = None
    rentabilidade: Optional[str] = None
    data_vencimento: Optional[date] = None
    liquidez: Optional[Literal["DIARIA", "VENCIMENTO", "D30", "D90", "D180"]] = None
    observacoes: Optional[str] = None


class AplicacaoPatch(BaseModel):
    nome: Optional[str] = None
    tipo: Optional[Literal["CDB", "LCA", "LCI", "FUNDO", "POUPANCA", "TESOURO", "ACOES", "FII", "OUTROS"]] = None
    valor_atual: Optional[float] = None
    data_atualizacao: Optional[date] = None
    modo: Optional[Literal["AUTOMATICA", "MANUAL"]] = None
    instituicao: Optional[str] = None
    rentabilidade: Optional[str] = None
    data_vencimento: Optional[date] = None
    liquidez: Optional[Literal["DIARIA", "VENCIMENTO", "D30", "D90", "D180"]] = None
    observacoes: Optional[str] = None
    ativo: Optional[bool] = None


class DashboardSaldos(BaseModel):
    """Resposta de GET /saldos/dashboard."""
    contas: list[ContaLiquidezItem]
    aplicacoes: list[AplicacaoOut]
    liquidez_total: float
    disponivel_agora: float       # contas + aplicacoes AUTOMATICA
    reserva_travada: float        # aplicacoes MANUAL


class SaldoManualInput(BaseModel):
    conta_bancaria_id: str
    saldo_valor: float = Field(ge=0)
    data_referencia: date
    observacao: Optional[str] = None
