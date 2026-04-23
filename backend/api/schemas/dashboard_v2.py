"""Schemas dos endpoints v2 do Dashboard (Track B)."""
from typing import Dict, List, Optional

from pydantic import BaseModel


class EvolucaoCaixaResponse(BaseModel):
    abertura_data: str
    abertura_valor: float
    hoje_data: str
    hoje_valor: float
    variacao_valor: float
    variacao_pct: float
    sparkline: List[float]


class CompromissoItem(BaseModel):
    fonte: str  # "PP" | "FATURA"
    descricao: str
    valor: float
    vencimento: Optional[str] = None


class CompromissosResponse(BaseModel):
    total: float
    por_fonte: Dict[str, float]
    itens: List[CompromissoItem]


class RecebivelItem(BaseModel):
    contratante: str
    valor: float
    dias_atraso: int
    faixa_aging: str  # "0-30" | "30-60" | "60-90" | "90+"


class RecebiveisResponse(BaseModel):
    total: float
    por_aging: Dict[str, float]
    itens: List[RecebivelItem]


class ReceitaFinanceiraResponse(BaseModel):
    rendimento_mes: float
    acumulado_ano: float
    rentabilidade_pct: float
    cdi_mes_pct: float
    percent_cdi: float


class MesHistorico(BaseModel):
    competencia: str
    liquidez: float
    faturamento: float
    despesa_fixa: float
    despesa_variavel: float
    tributo: float
    compromissos_abertos: float
    recebiveis_atraso: float


class HistoricoResponse(BaseModel):
    meses: List[MesHistorico]
