from pydantic import BaseModel


class KPIs(BaseModel):
    entradas_do_mes: float
    saidas_mes: float
    previsto_a_pagar: float
    saldo_atual: float


class BarraPxR(BaseModel):
    categoria: str
    previsto: float
    realizado: float
    pct: float


class Alerta(BaseModel):
    tipo: str                                # "NAO_CONCILIADO" | "VENCIDO" | "PAGO_A_MAIOR" | "ESTORNO"
    mensagem: str
    ref_id: str | None
    ref_tipo: str | None


class DashboardResponse(BaseModel):
    competencia: str
    empresa_filtro: str                      # "SPM" | "FD" | "TODAS"
    kpis: KPIs
    saidas_por_natureza: dict[str, float]    # { "DESPESA_FIXA": 123.45, ... }
    previsto_x_realizado: list[BarraPxR]
    alertas: list[Alerta]
