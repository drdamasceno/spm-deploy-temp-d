# spm-faturas: Classificador PF/PJ

from __future__ import annotations

import json
import re
import logging
import unicodedata
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------

def classificar_lancamentos(
    lancamentos: list[dict],
    historico: dict,
    config: dict,
) -> dict:
    """Classifica lancamentos em 'classificados' e 'pendentes'.

    Suporta tanto faturas de cartao (sem campo 'efetivado') quanto
    extratos bancarios (com campo 'efetivado').

    Para extratos:
    - efetivado=False → classificacao="nao_efetivado", pula revisao
    - valor > 0 → receita, usa categorias_receita
    - valor < 0 → despesa, usa categorias PF/PJ existentes

    Retorna {
        "classificados": [...],
        "pendentes": [...],
        "nao_efetivados": [...],
        "stats": {
            "total": int,
            "classificados": int,
            "pendentes": int,
            "nao_efetivados": int,
            "por_origem": {"historico": int, "recorrencia": int},
        },
    }

    Cada item e o lancamento original + campos:
      classificacao (PF|PJ|receita|nao_efetivado), categoria, confianca, origem
    """
    confianca_minima = config.get("classificacao", {}).get("confianca_minima", 0.85)
    sempre_revisar = config.get("classificacao", {}).get("sempre_revisar", [])
    recorrencias = config.get("recorrencias", [])

    classificados = []
    pendentes = []
    nao_efetivados = []
    stats_origem = {"historico": 0, "recorrencia": 0}

    for lanc in lancamentos:
        descricao = lanc.get("descricao", "")
        valor = lanc.get("valor", 0.0)

        # 0. Extrato: lancamentos nao efetivados — pula revisao
        if lanc.get("efetivado") is False:
            nao_efetivados.append(_montar_resultado(
                lanc,
                match={"classificacao": "nao_efetivado", "categoria": "", "confianca": 1.0},
                origem="estorno",
            ))
            continue

        # 1. Lista de revisao obrigatoria — sempre pendente
        if _deve_revisar(descricao, sempre_revisar):
            pendentes.append(_montar_resultado(lanc, pendente=True))
            continue

        # 2. Recorrencias do config.yaml
        match_rec = _buscar_recorrencia(descricao, valor, recorrencias)
        if match_rec:
            classificados.append(_montar_resultado(lanc, match=match_rec, origem="recorrencia"))
            stats_origem["recorrencia"] += 1
            continue

        # 3. Historico de classificacoes anteriores
        match_hist = _buscar_historico(descricao, historico, confianca_minima)
        if match_hist:
            classificados.append(_montar_resultado(lanc, match=match_hist, origem="historico"))
            stats_origem["historico"] += 1
            continue

        # 4. Nenhum match — pendente
        pendentes.append(_montar_resultado(lanc, pendente=True))

    return {
        "classificados": classificados,
        "pendentes": pendentes,
        "nao_efetivados": nao_efetivados,
        "stats": {
            "total": len(lancamentos),
            "classificados": len(classificados),
            "pendentes": len(pendentes),
            "nao_efetivados": len(nao_efetivados),
            "por_origem": stats_origem,
        },
    }


def carregar_historico(caminho: str) -> dict:
    """Le historico_classificacoes.json do disco."""
    path = Path(caminho)
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def salvar_historico(caminho: str, historico: dict) -> None:
    """Persiste historico_classificacoes.json atualizado."""
    path = Path(caminho)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)
    logger.info("Historico salvo em %s (%d entradas)", caminho, len(historico))


# ---------------------------------------------------------------------------
# Funcoes internas — busca e matching
# ---------------------------------------------------------------------------

def _buscar_historico(
    descricao: str,
    historico: dict,
    confianca_minima: float,
) -> dict | None:
    """Busca estabelecimento no historico por 3 estrategias:

    1. Match exato normalizado
    2. Match sem sufixo de parcela (remove 'PARC XX/XX' e texto apos)
    3. Match parcial — inicio da descricao com 4+ palavras

    Retorna {"classificacao", "categoria", "confianca"} do melhor match
    que passar confianca_minima, ou None.
    """
    if not historico:
        return None

    desc_norm = _normalizar(descricao)
    candidatos = []

    # Indexar historico normalizado
    historico_norm = {}
    for chave, dados in historico.items():
        historico_norm[_normalizar(chave)] = dados

    # 1. Match exato
    if desc_norm in historico_norm:
        dados = historico_norm[desc_norm]
        conf = dados.get("confianca", 1.0)
        if conf >= confianca_minima:
            candidatos.append({
                "classificacao": dados["classificacao"],
                "categoria": dados["categoria"],
                "confianca": conf,
            })

    # 2. Match sem sufixo de parcela — "LATAM AIR PARC 04/04" -> "LATAM AIR"
    desc_sem_parc = _remover_sufixo_parcela(desc_norm)
    if desc_sem_parc != desc_norm and desc_sem_parc in historico_norm:
        dados = historico_norm[desc_sem_parc]
        conf = dados.get("confianca", 1.0)
        if conf >= confianca_minima:
            candidatos.append({
                "classificacao": dados["classificacao"],
                "categoria": dados["categoria"],
                "confianca": conf,
            })

    # 3. Match parcial — inicio com 4+ palavras
    palavras = desc_sem_parc.split()
    if len(palavras) >= 4:
        prefixo = " ".join(palavras[:4])
        for chave_norm, dados in historico_norm.items():
            if chave_norm.startswith(prefixo):
                conf = dados.get("confianca", 1.0)
                if conf >= confianca_minima:
                    candidatos.append({
                        "classificacao": dados["classificacao"],
                        "categoria": dados["categoria"],
                        "confianca": conf,
                    })
                    break  # primeiro match parcial

    if not candidatos:
        return None

    # Retorna o de maior confianca
    return max(candidatos, key=lambda c: c["confianca"])


def _buscar_recorrencia(
    descricao: str,
    valor: float,
    recorrencias: list[dict],
) -> dict | None:
    """Verifica se o lancamento casa com uma recorrencia do config.yaml.

    Match por nome do estabelecimento na descricao.
    Retorna {"classificacao", "categoria", "confianca": 1.0} ou None.
    """
    desc_norm = _normalizar(descricao)

    for rec in recorrencias:
        estab_norm = _normalizar(rec.get("estabelecimento", ""))
        if not estab_norm:
            continue
        if estab_norm in desc_norm and len(estab_norm) >= 5:
            return {
                "classificacao": rec.get("classificacao", "PJ"),
                "categoria": rec.get("categoria", "Outros"),
                "confianca": 1.0,
            }

    return None


def _deve_revisar(descricao: str, sempre_revisar: list[str]) -> bool:
    """Retorna True se o estabelecimento esta na lista de revisao obrigatoria."""
    desc_norm = _normalizar(descricao)
    for item in sempre_revisar:
        if _normalizar(item) in desc_norm:
            return True
    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalizar(texto: str) -> str:
    """Normaliza descricao para matching: upper, sem acentos, sem espacos extras."""
    texto = texto.upper().strip()
    # Remove acentos
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    # Colapsar espacos
    texto = re.sub(r"\s+", " ", texto)
    return texto


def _remover_sufixo_parcela(texto_normalizado: str) -> str:
    """Remove sufixo 'PARC XX/XX' e qualquer texto apos ele.

    'LATAM AIR PARC 04/04' -> 'LATAM AIR'
    'OUTLE PARC 10/10'     -> 'OUTLE'
    'PGTO DEBITO CONTA'    -> 'PGTO DEBITO CONTA' (sem alteracao)
    """
    resultado = re.sub(r"\s+PARC\s+\d{1,2}/\d{1,2}.*$", "", texto_normalizado)
    return resultado.strip()


def _montar_resultado(
    lancamento: dict,
    match: dict | None = None,
    origem: str = "pendente",
    pendente: bool = False,
) -> dict:
    """Monta dict de retorno: lancamento original + campos de classificacao."""
    resultado = {**lancamento}
    if pendente or match is None:
        resultado["classificacao"] = ""
        resultado["categoria"] = ""
        resultado["confianca"] = 0.0
        resultado["origem"] = "pendente"
    else:
        resultado["classificacao"] = match["classificacao"]
        resultado["categoria"] = match["categoria"]
        resultado["confianca"] = match["confianca"]
        resultado["origem"] = origem
    return resultado
