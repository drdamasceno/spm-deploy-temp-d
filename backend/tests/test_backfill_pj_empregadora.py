import json
from unittest.mock import MagicMock
import pytest
from backend.scripts.backfill_pj_empregadora import (
    carregar_config,
    encontrar_prestadores_por_nome,
    aplicar_backfill,
    PlanoBackfill,
)


def test_carregar_config_valida(tmp_path):
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({
        "empresa_codigo": "FD",
        "prestadores": ["Ana"],
        "contratos_lotados": {"cidades": ["X/UF"]},
    }))
    data = carregar_config(str(cfg))
    assert data["empresa_codigo"] == "FD"
    assert data["prestadores"] == ["Ana"]


def test_encontrar_prestadores_por_nome_match_exato():
    client = MagicMock()
    client.table.return_value.select.return_value.execute.return_value.data = [
        {"id": "p1", "nome": "Thais Alessandra", "razao_social_pj": None, "pj_empregadora_id": None},
        {"id": "p2", "nome": "Vinicius Augusto", "razao_social_pj": None, "pj_empregadora_id": None},
        {"id": "p3", "nome": "Outro Nome", "razao_social_pj": None, "pj_empregadora_id": None},
    ]
    matches = encontrar_prestadores_por_nome(client, nomes=["Thais Alessandra", "Vinicius Augusto"])
    assert len(matches) == 2
    assert {m["id"] for m in matches} == {"p1", "p2"}


def test_encontrar_prestadores_por_nome_ja_vinculado_ignora():
    client = MagicMock()
    client.table.return_value.select.return_value.execute.return_value.data = [
        {"id": "p1", "nome": "Thais", "razao_social_pj": None, "pj_empregadora_id": "fd-id"},
    ]
    matches = encontrar_prestadores_por_nome(client, nomes=["Thais"])
    assert matches == []


def test_plano_backfill_dry_run_nao_modifica():
    client = MagicMock()
    plano = PlanoBackfill(empresa_id="fd-id", prestadores_a_vincular=[{"id": "p1", "nome": "Thais"}])
    aplicar_backfill(client, plano, dry_run=True)
    client.table.return_value.update.assert_not_called()


def test_plano_backfill_aplicado_chama_update():
    client = MagicMock()
    plano = PlanoBackfill(empresa_id="fd-id", prestadores_a_vincular=[{"id": "p1", "nome": "Thais"}])
    aplicar_backfill(client, plano, dry_run=False)
    client.table.return_value.update.assert_called_once_with({"pj_empregadora_id": "fd-id"})
