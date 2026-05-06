"""Schemas Pydantic para o router de margem.

Cobrem 3 visões agregadas que faltavam ao sistema:

  1. realizado-por-linha — soma `conciliacao_orcamento.valor_aplicado` por
     `orcamento_linha_id`, com data do último PIX e contagem.
  2. margem/por-contrato — agrupa orcamento_linha por contrato_id para as
     naturezas FATURAMENTO e DESPESA_PROFISSIONAIS, calculando margem absoluta
     e percentual (previsto e realizado).
  3. margem/por-profissional — rateio proporcional da receita do contrato
     pelos prestadores que executaram plantões na competência (cruza com
     registro_pp.valor_bonificado).
"""
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class RealizadoPorLinhaItem(BaseModel):
    """Quanto efetivamente saiu/entrou para uma linha de orçamento.

    Duas fontes:

    1. **Heurística orçamento** — `conciliacao_orcamento.valor_aplicado`. Boa
       pra FATURAMENTO, DESPESA_FIXA, TRIBUTO etc. (qualquer linha que case
       contra `transacao_bancaria` por valor/titular).
       Campos: `pago`, `data_max`, `txs_count`.

    2. **CNAB-240 retorno PIX** — `retorno_pix.valor_efetivado` matched contra
       `registro_pp` que pertence ao mesmo (contrato_id, mes_competencia) da
       linha. Fonte determinística (banco confirma via .RET) — preferida para
       DESPESA_PROFISSIONAIS (substitui inferência extrato↔PP). Só preenchido
       quando há retorno_pix matched para registros_pp da chave.
       Campos: `pago_cnab`, `data_max_cnab`, `retornos_count`.

    Frontend escolhe qual coluna usar baseado em `orcamento_linha.natureza`:
      - DESPESA_PROFISSIONAIS → preferir `pago_cnab` (fallback `pago` se 0).
      - demais → usar `pago`.
    """
    linha_id: UUID
    pago: float
    data_max: Optional[str] = None
    txs_count: int
    pago_cnab: float = 0.0
    data_max_cnab: Optional[str] = None
    retornos_count: int = 0


class MargemPorContratoOut(BaseModel):
    contrato_id: Optional[UUID]
    rotulo: str  # ex: "PR-LONDRINA" ou "(sem contrato)"
    faturamento_previsto: float
    faturamento_realizado: float
    despesa_prof_previsto: float
    despesa_prof_realizado: float
    margem_previsto: float
    margem_realizado: float
    margem_pct: Optional[float] = None  # margem_realizado / faturamento_realizado, None se receita 0


class MargemPorProfissionalOut(BaseModel):
    prestador_id: UUID
    prestador_nome: str
    bonificacao: float  # soma valor_bonificado dos plantões na competência
    share: float  # bonificacao / total_bonificacao do contrato (0..1)
    receita_atribuida: float  # share * receita_total_contrato
    margem_absoluta: float  # receita_atribuida - bonificacao
    margem_pct: Optional[float] = None  # margem_absoluta / receita_atribuida, None se receita 0
    pix_confirmado: float = 0.0  # soma retorno_pix.valor_efetivado matched ao prestador (CONFIRMADO)
    data_ultimo_pix: Optional[str] = None  # data_pagamento mais recente do CNAB


class ConciliacaoDetalheOut(BaseModel):
    """Conciliação individual de uma linha de orçamento — exibida no drawer
    multi-conta. Cada item carrega o suficiente para o frontend mostrar:
    chip de conta (origem_banco), valor aplicado, data, titular, descrição.
    """
    conciliacao_id: UUID
    transacao_id: UUID
    valor_aplicado: float
    titular_pix: Optional[str] = None
    data_extrato: str
    descricao_tx: Optional[str] = None
    origem_banco: str  # BRADESCO ou UNICRED
    conta_id: Optional[UUID] = None
    natureza_lancamento: Optional[str] = None
    aprovada_em: Optional[str] = None
    origem: Optional[str] = None  # REGRA / SIMILARIDADE / VALOR / MANUAL
