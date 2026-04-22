"""
Motor de classificação de conciliação extrato ↔ orçamento.

Três camadas em cascata, da mais forte para mais fraca:
  1. REGRA SALVA       — confiança 0.95+, titular matching direto
  2. SIMILARIDADE+VALOR — confiança 0.70-0.90, rapidfuzz + tolerância de valor
  3. VALOR ÚNICO        — confiança 0.30-0.60, última opção

Stateless, Python puro. Não toca no DB.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable, List, Optional

from rapidfuzz import fuzz


def normalizar_titular(s: Optional[str]) -> str:
    """
    Normaliza um titular PIX para comparação consistente.
    - NFD + strip acentos
    - upper
    - colapsa whitespace
    - trim
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.upper()
    s = re.sub(r"\s+", " ", s).strip()
    return s


# Lista de nomes que indicam "a própria empresa" — transferências entre contas
# do grupo não devem ser conciliadas contra orçamento/PP (saldo líquido = zero).
# TODO: no futuro, carregar do DB via empresa.razao_social.
_RAZOES_PROPRIAS_SPM = [
    "SOCIEDADE PARANAENSE DE MEDICINA",
    "FD GESTAO INTELIGENTE",  # FD também é próprio
]


def eh_transferencia_interna(transacao: "Transacao") -> bool:
    """
    True se o titular_pix bate com razão social de empresa do grupo
    (transferência entre contas próprias, não deve conciliar).

    Usa match por substring na versão normalizada (upper + sem acento) para
    tolerar sufixos ("LTDA", "S.A.") e prefixos de CNPJ que aparecem em alguns
    extratos.
    """
    if not transacao.titular_pix:
        return False
    titular_norm = normalizar_titular(transacao.titular_pix)
    if not titular_norm:
        return False
    return any(razao in titular_norm for razao in _RAZOES_PROPRIAS_SPM)


@dataclass
class Transacao:
    id: str
    titular_pix: Optional[str]
    valor: float                # negativo = débito
    data_movimento: str         # YYYY-MM-DD
    origem_banco: str           # "UNICRED" | "BRADESCO"


@dataclass
class LinhaOrcamento:
    id: str
    titular_razao_social: str
    valor_previsto: float
    saldo_pendente: float       # valor_previsto - sum(conciliacao_orcamento.valor_aplicado)


@dataclass
class Regra:
    id: str
    titular_pix_padrao: str         # já normalizado
    orcamento_linha_id: Optional[str]
    confianca_base: float
    ativa: bool


@dataclass
class Sugestao:
    orcamento_linha_id: str
    confianca: float
    origem: str                     # "REGRA" | "SIMILARIDADE" | "VALOR"
    valor_aplicado: float           # quanto da transação casa com a linha


def sugerir_por_regra(
    transacao: Transacao,
    linhas_abertas: List[LinhaOrcamento],
    regras: Iterable[Regra],
) -> List[Sugestao]:
    """
    Camada 1: se existir regra ativa cujo titular_pix_padrao == normalizar(transacao.titular_pix),
    sugerir a orcamento_linha_id memorizada (se ainda estiver entre as abertas).
    """
    titular_norm = normalizar_titular(transacao.titular_pix)
    if not titular_norm:
        return []

    linhas_por_id = {l.id: l for l in linhas_abertas}
    out: List[Sugestao] = []
    for r in regras:
        if not r.ativa:
            continue
        if r.titular_pix_padrao != titular_norm:
            continue
        if not r.orcamento_linha_id or r.orcamento_linha_id not in linhas_por_id:
            continue
        linha = linhas_por_id[r.orcamento_linha_id]
        valor_aplicado = min(abs(transacao.valor), linha.saldo_pendente)
        out.append(Sugestao(
            orcamento_linha_id=r.orcamento_linha_id,
            confianca=r.confianca_base,
            origem="REGRA",
            valor_aplicado=valor_aplicado,
        ))
    return out


def sugerir_por_similaridade(
    transacao: Transacao,
    linhas_abertas: List[LinhaOrcamento],
    threshold_nome: int = 75,
    tolerancia_valor_pct: float = 0.02,
) -> List[Sugestao]:
    """
    Camada 2: similaridade de nome (WRatio do rapidfuzz) + valor dentro de 2%.

    Usa WRatio (Weighted Ratio) porque casos reais têm hífens conectando palavras
    (ex: "COPEL-DIS" no Unicred vs "COPEL DISTRIBUICAO S.A." no XLSX). WRatio
    combina ratio/partial_ratio/token_set_ratio/token_sort_ratio e escolhe a
    melhor — robusto a essas variações. token_set_ratio falha pois "COPEL-DIS"
    vira 1 token único (hífen não separa em rapidfuzz).

    Confiança mapeada linearmente do threshold ao máximo:
      score 75 → confiança 0.70
      score 100 → confiança 0.90
    """
    titular_norm = normalizar_titular(transacao.titular_pix)
    if not titular_norm:
        return []
    valor_tx = abs(transacao.valor)
    if valor_tx <= 0:
        return []

    out: List[Sugestao] = []
    for linha in linhas_abertas:
        razao_norm = normalizar_titular(linha.titular_razao_social)
        if not razao_norm:
            continue
        score = fuzz.WRatio(titular_norm, razao_norm)
        if score < threshold_nome:
            continue
        if linha.saldo_pendente <= 0:
            continue
        diff_rel = abs(valor_tx - linha.saldo_pendente) / max(valor_tx, linha.saldo_pendente)
        if diff_rel > tolerancia_valor_pct:
            continue
        # mapeia score ∈ [threshold_nome, 100] -> confiança ∈ [0.70, 0.90]
        confianca = 0.70 + (score - threshold_nome) / (100 - threshold_nome) * 0.20
        out.append(Sugestao(
            orcamento_linha_id=linha.id,
            confianca=round(confianca, 2),
            origem="SIMILARIDADE",
            valor_aplicado=min(valor_tx, linha.saldo_pendente),
        ))
    out.sort(key=lambda s: -s.confianca)
    return out


def sugerir_por_valor(
    transacao: Transacao,
    linhas_abertas: List[LinhaOrcamento],
    tolerancia_centavos: float = 0.01,
) -> List[Sugestao]:
    """
    Camada 3: se exatamente 1 linha tem valor_previsto == |valor_tx| (±1 centavo), sugerir.
    Confiança fixa 0.45 (meio do range 0.30-0.60).
    """
    valor_tx = abs(transacao.valor)
    if valor_tx <= 0:
        return []
    candidatas = [
        l for l in linhas_abertas
        if l.saldo_pendente > 0 and abs(l.saldo_pendente - valor_tx) <= tolerancia_centavos
    ]
    if len(candidatas) != 1:
        return []
    linha = candidatas[0]
    return [Sugestao(
        orcamento_linha_id=linha.id,
        confianca=0.45,
        origem="VALOR",
        valor_aplicado=min(valor_tx, linha.saldo_pendente),
    )]


def sugerir_cascata(
    transacao: Transacao,
    linhas_abertas: List[LinhaOrcamento],
    regras: Iterable[Regra],
) -> List[Sugestao]:
    """
    Aplica as 3 camadas em cascata. Para assim que alguma camada produz resultado.
    Retorna lista ordenada por confiança desc (normalmente 0 ou 1 sugestão).

    Curto-circuito: transferências internas (titular == razão social de empresa
    do grupo SPM/FD) retornam [] imediatamente — saldo líquido é zero e não
    devem bater contra PP/orçamento.
    """
    if eh_transferencia_interna(transacao):
        return []

    regras_list = list(regras)

    sugs = sugerir_por_regra(transacao, linhas_abertas, regras_list)
    if sugs:
        return sorted(sugs, key=lambda s: -s.confianca)

    sugs = sugerir_por_similaridade(transacao, linhas_abertas)
    if sugs:
        return sugs  # já ordenado

    sugs = sugerir_por_valor(transacao, linhas_abertas)
    return sugs
