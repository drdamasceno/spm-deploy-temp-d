"""Testes unitários dos endpoints /transacoes/{id}/split (Track B Fase D)."""
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from backend.api.routers import transacao_linha as mod
from backend.api.routers.transacao_linha import (
    delete_split,
    get_split,
    save_split,
    sugerir_split_do_ultimo,
)
from backend.api.schemas.bolso import BolsoTipo
from backend.api.schemas.transacao_linha import SplitRequest, TransacaoLinhaCreate


def _current():
    return {"jwt": "fake", "id": str(uuid4())}


def _patch_client(monkeypatch, client):
    monkeypatch.setattr(mod, "get_supabase_authed", lambda jwt: client)


def _mk_linha_row(tx_id, valor, bolso="SPM_OPERACIONAL"):
    return {
        "id": str(uuid4()),
        "transacao_bancaria_id": str(tx_id),
        "valor": valor,
        "bolso": bolso,
        "orcamento_linha_id": None,
        "empresa_pagadora_id": None,
        "descricao": None,
        "criado_em": "2026-04-23T00:00:00Z",
        "criado_por": None,
    }


def test_get_split_vazio_retorna_valor_transacao(monkeypatch):
    """Transação existe, sem linhas: soma=0, valor_transacao preservado."""
    tx_id = uuid4()
    client = MagicMock()

    def table_side(nome):
        m = MagicMock()
        if nome == "transacao_bancaria":
            m.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
                {"id": str(tx_id), "valor": 250.0}
            ]
        elif nome == "transacao_linha":
            m.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
        return m

    client.table.side_effect = table_side
    _patch_client(monkeypatch, client)

    resp = get_split(tx_id=tx_id, current=_current())
    assert resp.valor_transacao == 250.0
    assert resp.valor_soma_linhas == 0.0
    assert resp.linhas == []


def test_post_split_valida_soma_igual_valor(monkeypatch):
    """Soma das linhas diverge do valor da transação -> HTTP 400."""
    tx_id = uuid4()
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"id": str(tx_id), "valor": 100.0}
    ]
    _patch_client(monkeypatch, client)

    req = SplitRequest(
        linhas=[
            TransacaoLinhaCreate(valor=30.0, bolso=BolsoTipo.SPM_OPERACIONAL),
            TransacaoLinhaCreate(valor=40.0, bolso=BolsoTipo.HUGO_PESSOAL),
        ]
    )
    with pytest.raises(HTTPException) as exc:
        save_split(tx_id=tx_id, payload=req, current=_current())
    assert exc.value.status_code == 400
    assert "diverge" in exc.value.detail["error"]


def test_post_split_soma_bate(monkeypatch):
    """2 linhas R$50 para tx R$100: insert chamado, retorno OK."""
    tx_id = uuid4()
    client = MagicMock()

    inserted = [
        _mk_linha_row(tx_id, 50.0, "SPM_OPERACIONAL"),
        _mk_linha_row(tx_id, 50.0, "HUGO_PESSOAL"),
    ]

    tx_table = MagicMock()
    tx_table.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"id": str(tx_id), "valor": 100.0}
    ]

    linha_table = MagicMock()
    linha_table.delete.return_value.eq.return_value.execute.return_value.data = []
    linha_table.insert.return_value.execute.return_value.data = inserted

    def table_side(nome):
        if nome == "transacao_bancaria":
            return tx_table
        if nome == "transacao_linha":
            return linha_table
        return MagicMock()

    client.table.side_effect = table_side
    _patch_client(monkeypatch, client)

    req = SplitRequest(
        linhas=[
            TransacaoLinhaCreate(valor=50.0, bolso=BolsoTipo.SPM_OPERACIONAL),
            TransacaoLinhaCreate(valor=50.0, bolso=BolsoTipo.HUGO_PESSOAL),
        ]
    )
    resp = save_split(tx_id=tx_id, payload=req, current=_current())

    assert resp.valor_transacao == 100.0
    assert resp.valor_soma_linhas == 100.0
    assert len(resp.linhas) == 2
    linha_table.insert.assert_called_once()


def test_post_split_substitui_anterior(monkeypatch):
    """DELETE é chamado antes do INSERT (substitui split anterior)."""
    tx_id = uuid4()
    client = MagicMock()

    call_order = []

    tx_table = MagicMock()
    tx_table.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"id": str(tx_id), "valor": 100.0}
    ]

    linha_table = MagicMock()

    def delete_exec():
        call_order.append("delete")
        r = MagicMock()
        r.data = []
        return r

    def insert_exec():
        call_order.append("insert")
        r = MagicMock()
        r.data = [_mk_linha_row(tx_id, 100.0)]
        return r

    linha_table.delete.return_value.eq.return_value.execute.side_effect = delete_exec
    linha_table.insert.return_value.execute.side_effect = insert_exec

    def table_side(nome):
        if nome == "transacao_bancaria":
            return tx_table
        if nome == "transacao_linha":
            return linha_table
        return MagicMock()

    client.table.side_effect = table_side
    _patch_client(monkeypatch, client)

    req = SplitRequest(linhas=[TransacaoLinhaCreate(valor=100.0, bolso=BolsoTipo.SPM_OPERACIONAL)])
    save_split(tx_id=tx_id, payload=req, current=_current())

    assert call_order == ["delete", "insert"]


def test_delete_split_remove_linhas(monkeypatch):
    """DELETE remove linhas filtrando por transacao_bancaria_id."""
    tx_id = uuid4()
    client = MagicMock()
    _patch_client(monkeypatch, client)

    delete_split(tx_id=tx_id, current=_current())

    client.table.assert_called_with("transacao_linha")
    client.table.return_value.delete.return_value.eq.assert_called_with(
        "transacao_bancaria_id", str(tx_id)
    )
    client.table.return_value.delete.return_value.eq.return_value.execute.assert_called()


def test_sugerir_vazio_titular_retorna_zero(monkeypatch):
    """titular_pix vazio -> SplitResponse com linhas=[] e soma=0."""
    tx_id = uuid4()
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
        {"id": str(tx_id), "valor": 150.0, "titular_pix": ""}
    ]
    _patch_client(monkeypatch, client)

    resp = sugerir_split_do_ultimo(tx_id=tx_id, current=_current())
    assert resp.valor_transacao == 150.0
    assert resp.valor_soma_linhas == 0.0
    assert resp.linhas == []
