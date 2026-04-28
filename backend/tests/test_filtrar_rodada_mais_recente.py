"""Testes unit puros do helper _filtrar_pela_rodada_mais_recente.

Sem dependência de DB. Garante que registros_pp do mesmo (contrato, comp,
prestador) em rodadas distintas são deduplicados pela rodada com
created_at mais recente.
"""
from __future__ import annotations

from backend.api.routers.contratos_competencia import (
    _filtrar_pela_rodada_mais_recente,
)


def test_lista_vazia_retorna_lista_vazia():
    assert _filtrar_pela_rodada_mais_recente([], {}) == []


def test_uma_rodada_so_preserva_tudo():
    rpps = [
        {"id": "rpp1", "contrato_id": "C1", "mes_competencia": "2026-02",
         "prestador_id": "P1", "rodada_id": "R1", "saldo_pp": 100.0},
        {"id": "rpp2", "contrato_id": "C1", "mes_competencia": "2026-02",
         "prestador_id": "P2", "rodada_id": "R1", "saldo_pp": 50.0},
    ]
    lookup = {"R1": "2026-04-20T10:00:00Z"}
    out = _filtrar_pela_rodada_mais_recente(rpps, lookup)
    assert {r["id"] for r in out} == {"rpp1", "rpp2"}


def test_duas_rodadas_mesma_chave_preserva_apenas_mais_recente():
    """Caso Unai: rodada baseline (R1, antiga) + rodada nova (R2, recente)."""
    rpps = [
        # Mesmo prestador P1 em duas rodadas — só R2 fica
        {"id": "seed", "contrato_id": "UNAI", "mes_competencia": "2026-02",
         "prestador_id": "P1", "rodada_id": "R_BASE", "saldo_pp": 5000.00},
        {"id": "novo", "contrato_id": "UNAI", "mes_competencia": "2026-02",
         "prestador_id": "P1", "rodada_id": "R_NOVA", "saldo_pp": 5500.00},
    ]
    lookup = {
        "R_BASE": "2026-04-19T15:00:00Z",
        "R_NOVA": "2026-04-25T02:30:00Z",
    }
    out = _filtrar_pela_rodada_mais_recente(rpps, lookup)
    assert len(out) == 1
    assert out[0]["id"] == "novo"


def test_chaves_diferentes_independentes():
    """C1/2026-02/P1 mais recente em R2; C2/2026-02/P2 mais recente em R1.
    Cada chave avalia independente."""
    rpps = [
        {"id": "a", "contrato_id": "C1", "mes_competencia": "2026-02",
         "prestador_id": "P1", "rodada_id": "R1", "saldo_pp": 10.0},
        {"id": "b", "contrato_id": "C1", "mes_competencia": "2026-02",
         "prestador_id": "P1", "rodada_id": "R2", "saldo_pp": 20.0},
        {"id": "c", "contrato_id": "C2", "mes_competencia": "2026-02",
         "prestador_id": "P2", "rodada_id": "R1", "saldo_pp": 30.0},
    ]
    lookup = {"R1": "2026-04-19T10:00:00Z", "R2": "2026-04-25T10:00:00Z"}
    out = _filtrar_pela_rodada_mais_recente(rpps, lookup)
    assert {r["id"] for r in out} == {"b", "c"}


def test_mesmo_prestador_em_dois_contratos_sao_chaves_distintas():
    """Prestador X tem registros em contratos A e B na mesma comp.
    Cada (contrato, comp, prestador) é chave própria."""
    rpps = [
        {"id": "rA", "contrato_id": "CA", "mes_competencia": "2026-02",
         "prestador_id": "X", "rodada_id": "R1", "saldo_pp": 100.0},
        {"id": "rB", "contrato_id": "CB", "mes_competencia": "2026-02",
         "prestador_id": "X", "rodada_id": "R1", "saldo_pp": 200.0},
    ]
    lookup = {"R1": "2026-04-25T10:00:00Z"}
    out = _filtrar_pela_rodada_mais_recente(rpps, lookup)
    assert {r["id"] for r in out} == {"rA", "rB"}


def test_registro_sem_rodada_id_e_descartado():
    rpps = [
        {"id": "ok", "contrato_id": "C1", "mes_competencia": "2026-02",
         "prestador_id": "P1", "rodada_id": "R1", "saldo_pp": 100.0},
        {"id": "broken", "contrato_id": "C1", "mes_competencia": "2026-02",
         "prestador_id": "P2", "rodada_id": None, "saldo_pp": 999.0},
    ]
    lookup = {"R1": "2026-04-25T10:00:00Z"}
    out = _filtrar_pela_rodada_mais_recente(rpps, lookup)
    assert {r["id"] for r in out} == {"ok"}


def test_rodada_ausente_no_lookup_e_tratada_como_mais_antiga():
    """Defensivo: rodada sem timestamp no lookup perde para qualquer outra com timestamp."""
    rpps = [
        {"id": "a", "contrato_id": "C1", "mes_competencia": "2026-02",
         "prestador_id": "P1", "rodada_id": "R_SEM_TS", "saldo_pp": 10.0},
        {"id": "b", "contrato_id": "C1", "mes_competencia": "2026-02",
         "prestador_id": "P1", "rodada_id": "R_COM_TS", "saldo_pp": 20.0},
    ]
    lookup = {"R_COM_TS": "2026-04-25T10:00:00Z"}
    out = _filtrar_pela_rodada_mais_recente(rpps, lookup)
    assert {r["id"] for r in out} == {"b"}
