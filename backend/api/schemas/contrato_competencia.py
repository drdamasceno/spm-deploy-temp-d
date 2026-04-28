"""Schemas de contratos por cidade + carry-over + campos extras."""
from datetime import date
from typing import Optional
from pydantic import BaseModel


class ContratoCidadeListItem(BaseModel):
    """1 linha da tela lista /contratos."""
    id: str
    uf: str
    cidade: str
    competencia: str
    total: float
    total_pago: float
    saldo: float
    prestadores: int
    status: str  # "PAGO" | "PARCIAL" | "PENDENTE"
    data_pagamento: Optional[date] = None  # data do PIX que quitou; None se nao quitado


class ContratoAnteriorItem(BaseModel):
    """1 linha do carry-over (compete < atual). Inclui quitados-no-mes-do-filtro."""
    contrato_id: str
    uf: str
    cidade: str
    competencia: str
    total_original: float
    total_pago: float
    saldo_aberto: float
    prestadores: int
    status: str
    idade_dias: int
    data_pagamento: Optional[date] = None  # data do PIX que quitou; None se nao quitado


class PrestadorLinhaDetalhe(BaseModel):
    """1 linha da tabela de detalhe do contrato (prestador × local × competência)."""
    prestador_id: str
    prestador_nome: str
    local: Optional[str]
    competencia: str
    total: float
    total_pago: float
    saldo: float
    status: str
    data_pagamento: Optional[date]


class ContratoDadosExtras(BaseModel):
    """Campos editáveis na tab 'Dados do contrato'."""
    nome_oficial: Optional[str] = None
    cnpj: Optional[str] = None
    tipo: Optional[str] = None  # "PUBLICO" | "PRIVADO"
    valor_faturamento_mensal: Optional[float] = None
    retencao_tributaria_pct: Optional[float] = None
    observacoes: Optional[str] = None


class ContratoDetalheOut(BaseModel):
    """Resposta GET /contratos/{id}/competencia/{mes}."""
    contrato_id: str
    uf: str
    cidade: str
    competencia: str
    total: float
    total_pago: float
    saldo: float
    prestadores_count: int
    registros_count: int
    linhas: list[PrestadorLinhaDetalhe]
    dados_extras: ContratoDadosExtras
