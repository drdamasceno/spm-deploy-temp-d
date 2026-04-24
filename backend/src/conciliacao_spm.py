"""
Motor de Conciliação SPM — 42 regras de negócio.

CATEGORIAS (7):
  1. PLANTAO_PF      — Plantão PF (PIX para CPF)
  2. PLANTAO_PJ      — Plantão PJ (PIX/TED para CNPJ/conta PJ)
  3. ADIANTAMENTO    — Adiantamento de plantão
  4. REEMBOLSO       — Reembolso de despesas (NF obrigatória)
  5. CORRECAO        — Correção de pagamento anterior
  6. TARIFA          — Tarifas bancárias e encargos
  7. OUTROS          — Transações não classificadas

STATUS (5):
  MATCH_AUTOMATICO   — titular_pix == nome_prestador + valor == saldo_pp
  FRACIONADO         — soma de N PIX == saldo_pp (mesmo prestador+contrato)
  CONCILIADO_CATEGORIA — categoria automática (INVEST_FACIL, TARIFA, etc.)
  MANUAL_PENDENTE    — nome encontrado mas valor diverge
  NAO_CLASSIFICADO   — sem match por nome e sem categoria

REGRAS CRÍTICAS:
  - Match válido EXIGE titular_pix == nome_prestador ou razao_social_pj
  - NUNCA conciliar só por valor coincidente sem titularidade confirmada
  - Pagamentos apenas segundas e quintas
  - Hugo é o único aprovador final — nenhum pagamento sem autorização
  - Sem NFE = sem pagamento
"""

from __future__ import annotations

import re
import unicodedata
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

TOLERANCIA_VALOR = 0.01  # R$0,01 de tolerância

# Exceções PJ validadas por Hugo (sessões Claude.ai 14-15/04/2026)
# razao_social_pj (parcial, normalizada) → nome_prestador (parcial, normalizado)
EXCECOES_PJ_VALIDADAS: Dict[str, str] = {
    "CLINICA DR FABIO": "FABIO",
    "GLENIO S": "GLENIO",
    # Nayara/Luana: razão social exata pendente de confirmação (sessão 15/04)
}


# Dados operacionais hardcoded (v1) — DIVIDA TECNICA Passo 5:
# migrar para tabela `vinculo_prestador` com UI de cadastro. Enquanto
# isso, entrada/saida dessas pessoas da empresa exige alterar codigo.
# Match por substring do nome normalizado (_normalizar_nome) contra o
# titular do PIX. Iteracao apos _categorizar_transacao e antes da regra
# EXCECAO_PJ (consulta DB) — ver funcao conciliar().
CLTS_FOLHA: List[str] = [
    "Ana Carolina Alves Correa",
    "Leomar Militao da Cunha",
    "Mirelly Aparecida Araujo Gomes",
    "Rafaela Aparecida Joslin Mendes",
]

COORDENADORA_CLT_PJ: List[str] = [
    "Erica Machado da Silva",
]

DESTINATARIOS_DESPESA_OPERACIONAL: List[str] = [
    "Tiago Malta",
    "Maria do Carmo",
    "Sara Kelen",
    "Carla Tatiana",
    "Klauss Yller",
    "Junior Xavier",
    "Casa das Impressoras",
    "DNAA Promocoes",   # eventos, despesas diversas fora do PP (sessao 15/04)
]


# Razoes sociais da propria SPM — PIX para esses titulares e transferencia
# entre contas da empresa (categoria TRANSFERENCIA_INTERNA). Match por
# _classificar_por_lista (tokens + substring). DIVIDA TECNICA Passo 5:
# migrar para tabela `conta_bancaria` (self-reference) ou flag `titular_interno`.
TRANSFERENCIAS_INTERNAS_SPM: List[str] = [
    "Sociedade Paranaense",
]


def _normalizar_nome(nome: str) -> str:
    """
    Normaliza nome para comparação:
      - Uppercase
      - Remove acentos
      - Remove prefixos: DR, DRA, DR., DRA., DOUTOR, DOUTORA
      - Remove espaços extras
    """
    if not nome:
        return ""
    # Remove acentos
    nfd = unicodedata.normalize('NFD', nome)
    sem_acento = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    # Uppercase e limpar espaços
    s = sem_acento.upper().strip()
    # Remover prefixos de tratamento médico
    s = re.sub(r'^(?:DR\.?A?\.?|DOUTORA?|PROF\.?)\s+', '', s)
    # Múltiplos espaços → um
    s = re.sub(r'\s+', ' ', s).strip()
    return s


try:
    from rapidfuzz import fuzz as _fuzz
    _HAS_RAPIDFUZZ = True
except ImportError:
    _HAS_RAPIDFUZZ = False


def _razao_bate(razao_pp: str, titular_pix: str) -> bool:
    """
    Match para razão social PJ. SÓ usa camadas 1-2 (exato + substring).

    Por que não fuzzy? Razões sociais do Pega Plantão compartilham tokens
    genéricos ("SERVICOS MEDICOS LTDA", "MEDICINA LTDA") que disparam
    rapidfuzz.partial_ratio >= 85 entre PJs não relacionadas. Match válido
    exige titular PIX = razão social cadastrada (CLAUDE.md regra 3).
    Truncamento do memo Bradesco em 21 chars é coberto por substring —
    não precisa de fuzzy.
    """
    a = _normalizar_nome(razao_pp)
    b = _normalizar_nome(titular_pix)
    if not a or not b:
        return False
    if a == b:
        return True
    if a in b or b in a:
        return True
    return False


def _nomes_batem(nome_pp: str, titular_pix: str) -> bool:
    """
    Match robusto entre nome do prestador (PP) e titular do PIX (extrato).

    Cobre o truncamento típico do MEMO Bradesco em ~21 chars onde o sobrenome
    do prestador fica cortado.

    Ordem de prioridade:
      1. Exato após normalização (uppercase, sem acentos, sem DR/DRA)
      2. Substring: um contém o outro
      3. Prefix match por tokens: primeiros N tokens (N=min(3, len(menor)))
         do nome menor batem com o início do nome maior; exige >=3 tokens OU
         >=15 chars em comum no prefixo
      4. Rapidfuzz (se disponível): partial_ratio >= 85
    """
    a = _normalizar_nome(nome_pp)
    b = _normalizar_nome(titular_pix)
    if not a or not b:
        return False

    # 1. Exato
    if a == b:
        return True

    # 2. Substring (qualquer direção)
    if a in b or b in a:
        return True

    # 3. Prefix match por tokens
    tokens_a = a.split()
    tokens_b = b.split()
    if tokens_a and tokens_b:
        menor, maior = (tokens_a, tokens_b) if len(tokens_a) <= len(tokens_b) else (tokens_b, tokens_a)
        n = min(3, len(menor))
        prefix_menor = menor[:n]
        prefix_maior = maior[:n]
        if prefix_menor == prefix_maior:
            chars_em_comum = len(' '.join(prefix_menor))
            if n >= 3 or chars_em_comum >= 15:
                return True

    # 4. Rapidfuzz partial_ratio (lida bem com truncamento)
    if _HAS_RAPIDFUZZ:
        if _fuzz.partial_ratio(a, b) >= 85:
            return True

    return False


def _nomes_coincidem(nome_a: str, nome_b: str) -> bool:
    """Wrapper de compatibilidade — delega para _nomes_batem."""
    return _nomes_batem(nome_a, nome_b)


def _classificar_por_lista(titular_pix: str, lista: List[str]) -> bool:
    """
    True se o titular do PIX bate com algum nome da lista (normalizado).

    Estrategias de match (em ordem):
      1) Substring direta bidirecional (cobre truncamento MEMO Bradesco)
      2) Token subset: todos os tokens do nome da lista aparecem no titular
         (cobre nome do meio inserido — ex: "TIAGO MALTA" em lista vs
         "TIAGO TEIXEIRA MALTA" no PIX)

    Normaliza ambos os lados via _normalizar_nome (uppercase, sem acentos,
    sem prefixos DR/DRA).
    """
    titular_norm = _normalizar_nome(titular_pix)
    if not titular_norm:
        return False
    titular_tokens = set(titular_norm.split())
    for nome in lista:
        nome_norm = _normalizar_nome(nome)
        if not nome_norm:
            continue
        if nome_norm in titular_norm or titular_norm in nome_norm:
            return True
        nome_tokens = set(nome_norm.split())
        if nome_tokens and nome_tokens.issubset(titular_tokens):
            return True
    return False


def _prestador_no_pp_sem_saldo(titular_pix: str, pp_data: List[Dict]) -> bool:
    """
    True se titular do PIX bate com algum prestador do PP cujo saldo <= 0
    (status SEM_MOVIMENTO ou SALDO_NEGATIVO).

    Usado para classificar tx como COMPETENCIA_ANTERIOR: PIX saiu no periodo
    para prestador real, mas o PP da competencia correspondente nao esta
    nesta rodada. Regra [ANCORADA] 9 do vault (competencias de 1-3 meses
    atras sao normais).
    """
    titular_norm = _normalizar_nome(titular_pix)
    if not titular_norm:
        return False
    for pp in pp_data:
        nome_pp = _normalizar_nome(pp.get('nome_prestador', ''))
        saldo = float(pp.get('saldo') or 0.0)
        if nome_pp and saldo <= 0 and _nomes_batem(titular_norm, nome_pp):
            return True
    return False


def _valores_coincidem(v1: float, v2: float) -> bool:
    return abs(v1 - v2) <= TOLERANCIA_VALOR


def _pix_saidas(extrato_data: List[Dict]) -> List[Dict]:
    """Filtra apenas PIX de saída do extrato."""
    return [t for t in extrato_data if t.get('tipo') in ('PIX_SAIDA',) and t.get('valor', 0) < 0]


def _categorizar_transacao(t: Dict) -> Optional[str]:
    """
    Retorna categoria automática para transações que não precisam de match PP.
    Retorna None se deve ser conciliada com PP.
    """
    tipo = t.get('tipo', '')
    trntype = t.get('trntype', '').upper()

    if tipo == 'INVEST_FACIL':
        return 'TRANSFERENCIA_INTERNA'
    if tipo == 'TARIFA_BANCARIA':
        return 'DESPESA_OPERACIONAL'
    if tipo in ('TED_ENTRADA',) and trntype == 'CREDIT':
        return 'RECEBIMENTO_CONTRATANTE'
    return None


def conciliar(
    pp_data: List[Dict[str, Any]],
    extrato_data: List[Dict[str, Any]],
    excecoes_pj: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Motor de conciliação SPM.

    Args:
        pp_data: Saída de pega_plantao.parse_relatorio()
        extrato_data: Saída de extrato_bradesco.parse_extrato()
        excecoes_pj: Dict {razao_social_pj_normalizada: nome_prestador_parcial}.
                     Se None, usa EXCECOES_PJ_VALIDADAS (default).

    Returns:
        {
          "resumo": {...},
          "registros": [...],   # um por prestador+contrato do PP
          "transacoes_extras": [...]  # PIX do extrato sem match PP (categorias automáticas etc.)
        }
    """
    if excecoes_pj is None:
        excecoes_pj = EXCECOES_PJ_VALIDADAS
    excecoes_norm = {_normalizar_nome(k): _normalizar_nome(v) for k, v in excecoes_pj.items()}

    # Separar PIX de saída (candidatos a pagamento de prestador)
    pix_saidas = _pix_saidas(extrato_data)

    # Marcar todas transações: usadas no match ou não
    pix_usados: set = set()  # fitids já matchados

    # --- helper: construir candidatos de um prestador sobre PIX disponíveis ---
    def _construir_candidatos(pp: dict) -> List[dict]:
        nome_pp_local = _normalizar_nome(pp['nome_prestador'])
        razao_pj_local = _normalizar_nome(pp.get('razao_social_pj', ''))
        cands = []
        for pix in pix_saidas:
            if pix['fitid'] in pix_usados:
                continue
            titular = _normalizar_nome(pix.get('titular_pix', ''))
            if not titular:
                continue
            match_direto = _nomes_batem(nome_pp_local, titular)
            match_pj = bool(razao_pj_local) and _razao_bate(razao_pj_local, titular)
            match_excecao = False
            for exc_razao, exc_nome in excecoes_norm.items():
                if _razao_bate(exc_razao, titular) and _nomes_batem(exc_nome, nome_pp_local):
                    match_excecao = True
                    break
            if match_direto or match_pj or match_excecao:
                cands.append({**pix, '_match_excecao': match_excecao,
                              '_valor_abs': abs(pix['valor'])})
        return cands

    def _stub(pp: dict) -> dict:
        return {
            "nome_prestador": pp['nome_prestador'],
            "contrato": pp.get('contrato', ''),
            "mes_competencia": pp.get('mes_competencia', ''),
            "saldo_pp": float(pp.get('saldo', 0.0)),
            "tipo_doc": pp.get('tipo_doc', ''),
            "chave_pix": pp.get('chave_pix', ''),
            "documento": pp.get('documento', ''),
            "status": "NAO_CLASSIFICADO",
            "categoria": "",
            "pix_matched": [],
            "valor_pix_total": 0.0,
            "divergencia": float(pp.get('saldo', 0.0)),
        }

    # Inicializa stub por prestador (preserva ordem de pp_data no retorno).
    registros = [_stub(pp) for pp in pp_data]

    # Pré-classifica SEM_MOVIMENTO e SALDO_NEGATIVO (não competem por PIX).
    pendentes_indices: List[int] = []
    for i, pp in enumerate(pp_data):
        saldo = float(pp.get('saldo', 0.0))
        if saldo < 0.0:
            registros[i]["status"] = "SALDO_NEGATIVO"
            registros[i]["categoria"] = "SALDO_NEGATIVO"
            registros[i]["divergencia"] = 0.0
        elif saldo == 0.0:
            registros[i]["status"] = "SEM_MOVIMENTO"
            registros[i]["categoria"] = "SEM_MOVIMENTO"
            registros[i]["divergencia"] = 0.0
        else:
            pendentes_indices.append(i)

    # --- PASSADA 1a: MATCH_AUTOMATICO / CONCILIADO_CATEGORIA (valor exato) ---
    for i in pendentes_indices[:]:
        pp = pp_data[i]
        saldo_pp = float(pp.get('saldo', 0.0))
        cands = _construir_candidatos(pp)
        if not cands:
            continue
        for cand in cands:
            if _valores_coincidem(cand['_valor_abs'], saldo_pp):
                pix_usados.add(cand['fitid'])
                registros[i]["status"] = (
                    "CONCILIADO_CATEGORIA" if cand['_match_excecao']
                    else "MATCH_AUTOMATICO"
                )
                registros[i]["categoria"] = (
                    "EXCECAO_PJ_PRESTADOR" if cand['_match_excecao'] else ""
                )
                registros[i]["pix_matched"] = [cand]
                registros[i]["valor_pix_total"] = cand['_valor_abs']
                registros[i]["divergencia"] = 0.0
                pendentes_indices.remove(i)
                break

    # --- PASSADA 1b: FRACIONADO (soma de candidatos == saldo) ---
    from itertools import combinations
    for i in pendentes_indices[:]:
        pp = pp_data[i]
        saldo_pp = float(pp.get('saldo', 0.0))
        cands = _construir_candidatos(pp)
        if len(cands) < 2:
            continue
        matched_frac = None
        for r in range(2, min(6, len(cands) + 1)):
            for combo in combinations(cands, r):
                soma = sum(c['_valor_abs'] for c in combo)
                if _valores_coincidem(soma, saldo_pp):
                    matched_frac = list(combo)
                    break
            if matched_frac:
                break
        if matched_frac:
            for c in matched_frac:
                pix_usados.add(c['fitid'])
            registros[i]["status"] = "FRACIONADO"
            registros[i]["pix_matched"] = matched_frac
            registros[i]["valor_pix_total"] = sum(c['_valor_abs'] for c in matched_frac)
            registros[i]["divergencia"] = saldo_pp - registros[i]["valor_pix_total"]
            pendentes_indices.remove(i)

    # --- PASSADA 2: MANUAL_PENDENTE / NAO_CLASSIFICADO (consumo conservador) ---
    for i in pendentes_indices:
        pp = pp_data[i]
        saldo_pp = float(pp.get('saldo', 0.0))
        cands = _construir_candidatos(pp)
        if cands:
            # MANUAL_PENDENTE: escolhe PIX vencedor (maior |valor|) e consome
            # só esse. Demais candidatos continuam disponíveis para outros
            # prestadores que possam tê-los como match legítimo.
            vencedor = max(cands, key=lambda c: c['_valor_abs'])
            pix_usados.add(vencedor['fitid'])
            registros[i]["status"] = "MANUAL_PENDENTE"
            registros[i]["pix_matched"] = [vencedor]
            registros[i]["valor_pix_total"] = vencedor['_valor_abs']
            registros[i]["divergencia"] = saldo_pp - vencedor['_valor_abs']
        else:
            # Sem candidato por titular — tenta VALOR_SEM_TITULAR (match só por valor)
            for pix in pix_saidas:
                if pix['fitid'] in pix_usados:
                    continue
                if _valores_coincidem(abs(pix['valor']), saldo_pp):
                    pix_usados.add(pix['fitid'])
                    registros[i]["status"] = "MANUAL_PENDENTE"
                    registros[i]["categoria"] = "VALOR_SEM_TITULAR"
                    registros[i]["pix_matched"] = [pix]
                    registros[i]["valor_pix_total"] = abs(pix['valor'])
                    registros[i]["divergencia"] = saldo_pp - abs(pix['valor'])
                    break
            # se nenhum, stub já está NAO_CLASSIFICADO (default)

    # Transações do extrato com categoria (PIX nao usados em match PP).
    # Ordem de prioridade (conforme spec do Passo 3 Bloco C + auditoria 2026-04-19):
    #   a-pre) Transferencia interna SPM (razao social da propria empresa)
    #   a)     Tipo automatico: INVEST_FACIL / TARIFA_BANCARIA / TED_ENTRADA+CREDIT
    #   d)     Lista CLTS_FOLHA
    #   e)     Lista COORDENADORA_CLT_PJ
    #   f)     Lista DESTINATARIOS_DESPESA_OPERACIONAL
    #   g)     excecao_pj (DB) — razao social em excecao validada sem PP correspondente
    #   g.5)   Prestador existe no PP mas com SEM_MOVIMENTO/SALDO_NEGATIVO
    #          (COMPETENCIA_ANTERIOR — regra [ANCORADA] 9)
    # Sem match: nao entra em transacoes_extras (fica NAO_CLASSIFICADO no router).
    transacoes_extras = []
    for t in extrato_data:
        if t.get('fitid') in pix_usados:
            continue

        titular = t.get('titular_pix', '')

        # (a-pre) Transferencia interna SPM
        cat = None
        if _classificar_por_lista(titular, TRANSFERENCIAS_INTERNAS_SPM):
            cat = 'TRANSFERENCIA_INTERNA'

        # (a) Tipo automatico
        if not cat:
            cat = _categorizar_transacao(t)

        # (d) Lista CLTS_FOLHA
        if not cat and _classificar_por_lista(titular, CLTS_FOLHA):
            cat = 'CLT_FOLHA'

        # (e) Lista COORDENADORA_CLT_PJ
        if not cat and _classificar_por_lista(titular, COORDENADORA_CLT_PJ):
            cat = 'COORDENADORA_CLT_PJ'

        # (f) Lista DESTINATARIOS_DESPESA_OPERACIONAL
        if not cat and _classificar_por_lista(titular, DESTINATARIOS_DESPESA_OPERACIONAL):
            cat = 'DESPESA_OPERACIONAL'

        # (g) excecao_pj DB — razao social validada sem PP correspondente
        if not cat and titular:
            titular_norm = _normalizar_nome(titular)
            for exc_razao in excecoes_norm.keys():
                if _nomes_coincidem(titular_norm, exc_razao):
                    cat = 'EXCECAO_PJ_PRESTADOR'
                    break

        # (g.5) Prestador no PP com saldo <= 0 — COMPETENCIA_ANTERIOR
        if not cat and _prestador_no_pp_sem_saldo(titular, pp_data):
            cat = 'COMPETENCIA_ANTERIOR'

        if cat:
            transacoes_extras.append({**t, 'categoria': cat})

    # Calcular resumo
    total_pp = len(registros)
    total_pix = len([t for t in extrato_data if t.get('tipo') in ('PIX_SAIDA',)])
    match_auto = sum(1 for r in registros if r['status'] == 'MATCH_AUTOMATICO')
    fracionado = sum(1 for r in registros if r['status'] == 'FRACIONADO')
    conc_cat = sum(1 for r in registros if r['status'] == 'CONCILIADO_CATEGORIA')
    manual = sum(1 for r in registros if r['status'] == 'MANUAL_PENDENTE')
    nao_class = sum(1 for r in registros if r['status'] == 'NAO_CLASSIFICADO')
    sem_mov = sum(1 for r in registros if r['status'] == 'SEM_MOVIMENTO')
    saldo_neg = sum(1 for r in registros if r['status'] == 'SALDO_NEGATIVO')
    # SEM_MOVIMENTO e SALDO_NEGATIVO excluídos do cálculo — não são pagamento esperado
    registros_para_percentual = [
        r for r in registros if r['status'] not in ('SEM_MOVIMENTO', 'SALDO_NEGATIVO')
    ]
    valor_total_pp = sum(r['saldo_pp'] for r in registros_para_percentual)
    valor_conciliado = sum(
        r['saldo_pp'] for r in registros_para_percentual
        if r['status'] in ('MATCH_AUTOMATICO', 'FRACIONADO', 'CONCILIADO_CATEGORIA')
    )
    pct = (valor_conciliado / valor_total_pp * 100) if valor_total_pp > 0 else 0.0

    logger.info(
        f"Conciliação: {match_auto} auto + {fracionado} frac + {conc_cat} cat "
        f"+ {manual} manual + {nao_class} nao_class + {sem_mov} sem_mov + {saldo_neg} saldo_neg | "
        f"R$ {valor_conciliado:,.2f} / R$ {valor_total_pp:,.2f} ({pct:.1f}%)"
    )

    return {
        "resumo": {
            "total_registros_pp": total_pp,
            "total_pix_extrato": total_pix,
            "match_automatico": match_auto,
            "fracionado": fracionado,
            "conciliado_categoria": conc_cat,
            "manual_pendente": manual,
            "nao_classificado": nao_class,
            "sem_movimento": sem_mov,
            "saldo_negativo": saldo_neg,
            "valor_total_pp": round(valor_total_pp, 2),
            "valor_conciliado": round(valor_conciliado, 2),
            "percentual_conciliado": round(pct, 2),
        },
        "registros": registros,
        "transacoes_extras": transacoes_extras,
    }
