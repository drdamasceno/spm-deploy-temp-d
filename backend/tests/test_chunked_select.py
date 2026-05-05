"""Testes unit do helper _chunked_select.

Garante que listas grandes em `.in_(col, ids)` são divididas em batches
para evitar URLs gigantes que estouram limites de proxy (Cloudflare ~16KB,
nginx 8KB padrão).
"""
from __future__ import annotations

from unittest.mock import MagicMock

from backend.api.routers.contratos_competencia import (
    _IN_BATCH_SIZE,
    _chunked_select,
)


def _build_client(per_chunk_data):
    """Retorna mock client cujo `.execute()` devolve `per_chunk_data[N]` na
    N-ésima chamada (registra todas as chamadas)."""
    client = MagicMock()
    qb = MagicMock()
    for m in ("select", "in_", "eq", "lt"):
        getattr(qb, m).return_value = qb
    qb.execute.side_effect = [MagicMock(data=d) for d in per_chunk_data]
    client.table.return_value = qb
    return client, qb


def test_lista_vazia_nao_chama_db_e_retorna_lista_vazia():
    client = MagicMock()
    out = _chunked_select(client, [], lambda c, chunk: c.table("x"))
    assert out == []
    client.table.assert_not_called()


def test_lista_menor_que_batch_faz_uma_chamada():
    ids = [f"u{i}" for i in range(5)]
    client, qb = _build_client([[{"id": "x"}]])

    chunks_seen: list[list[str]] = []

    def builder(c, chunk):
        chunks_seen.append(list(chunk))
        return c.table("registro_pp").select("id").in_("id", chunk)

    out = _chunked_select(client, ids, builder, batch_size=200)

    assert len(chunks_seen) == 1
    assert chunks_seen[0] == ids
    assert out == [{"id": "x"}]


def test_lista_exatamente_batch_size_faz_uma_chamada():
    ids = [f"u{i}" for i in range(50)]
    client, _ = _build_client([[{"id": "x"}] * 50])

    chunks_seen: list[list[str]] = []

    def builder(c, chunk):
        chunks_seen.append(list(chunk))
        return c.table("registro_pp").select("id").in_("id", chunk)

    out = _chunked_select(client, ids, builder, batch_size=50)

    assert len(chunks_seen) == 1
    assert len(out) == 50


def test_lista_maior_que_batch_concatena_em_ordem():
    ids = [f"u{i}" for i in range(7)]
    client, _ = _build_client([
        [{"id": "a"}, {"id": "b"}, {"id": "c"}],  # chunk 0: u0..u2
        [{"id": "d"}, {"id": "e"}, {"id": "f"}],  # chunk 1: u3..u5
        [{"id": "g"}],                            # chunk 2: u6
    ])

    chunks_seen: list[list[str]] = []

    def builder(c, chunk):
        chunks_seen.append(list(chunk))
        return c.table("registro_pp").select("id").in_("id", chunk)

    out = _chunked_select(client, ids, builder, batch_size=3)

    assert chunks_seen == [
        ["u0", "u1", "u2"],
        ["u3", "u4", "u5"],
        ["u6"],
    ]
    assert [r["id"] for r in out] == ["a", "b", "c", "d", "e", "f", "g"]


def test_default_batch_size_e_seguro_para_url_de_proxy():
    """Defesa contra regressão: o default precisa manter URL bem abaixo de
    16KB pra qualquer combinação razoável de colunas."""
    # 200 UUIDs * (36 + 1 vírgula) = 7400 chars na lista
    # Resto da URL (host, table, select, headers): ~1KB
    # Total: ~8.5KB → abaixo dos 16KB do Cloudflare/Render proxy.
    assert _IN_BATCH_SIZE <= 250
    # E grande o bastante pra não fragmentar demais (1-5 calls em casos típicos):
    assert _IN_BATCH_SIZE >= 100
