from uuid import UUID
from pydantic import BaseModel


class AdiantamentoOut(BaseModel):
    id: UUID
    prestador_id: UUID
    valor_bruto_solicitado: float
    percentual_desconto: float
    valor_liquido_pago: float
    receita_financeira: float
    data_pagamento: str
    status: str
    compensado_em_registro_pp_id: UUID | None


class AdiantamentoCompensarIn(BaseModel):
    registro_pp_id: UUID
