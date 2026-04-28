"""Smoke tests dos endpoints de contratos com mock do supabase client.

Cenario realista: PP re-importado em rodadas distintas SEMPRE traz os
MESMOS prestadores. O bug do agregador era somar saldo_pp de ambas as
rodadas para os mesmos prestadores. O filtro per-prestador resolve
mantendo apenas o registro_pp da rodada mais recente por chave."""
from __future__ import annotations

from unittest.mock import MagicMock, patch


ROD_BASE = "rb-1111-1111-1111-111111111111"
ROD_NOVA = "rn-2222-2222-2222-222222222222"
CONTRATO_UNAI = "cu-3333-3333-3333-333333333333"
CONTRATO_OUTRO = "co-4444-4444-4444-444444444444"
PRESTADOR_A = "pa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
PRESTADOR_B = "pb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
PRESTADOR_OUTRO = "po-cccc-cccc-cccc-cccccccccccc"


def _rpps_unai_re_importado_em_2_rodadas():
    """Caso real: PP de UNAI 02.26 com Dr. A e Dr. B importado duas vezes
    (R_BASE e R_NOVA). Mesmos prestadores, mesmos valores. Sem filtro,
    sistema soma R$ (4000+3000) duas vezes = R$ 14000. Com filtro
    per-prestador, fica R$ 7000 (so a rodada mais recente por chave)."""
    return [
        # Rodada baseline (antiga)
        {"id": "rpp-base-A", "contrato_id": CONTRATO_UNAI, "mes_competencia": "2026-02",
         "prestador_id": PRESTADOR_A, "rodada_id": ROD_BASE, "saldo_pp": 4000.00},
        {"id": "rpp-base-B", "contrato_id": CONTRATO_UNAI, "mes_competencia": "2026-02",
         "prestador_id": PRESTADOR_B, "rodada_id": ROD_BASE, "saldo_pp": 3000.00},
        # Rodada nova: mesmos prestadores, mesmos valores (PP nao mudou)
        {"id": "rpp-nova-A", "contrato_id": CONTRATO_UNAI, "mes_competencia": "2026-02",
         "prestador_id": PRESTADOR_A, "rodada_id": ROD_NOVA, "saldo_pp": 4000.00},
        {"id": "rpp-nova-B", "contrato_id": CONTRATO_UNAI, "mes_competencia": "2026-02",
         "prestador_id": PRESTADOR_B, "rodada_id": ROD_NOVA, "saldo_pp": 3000.00},
        # Outro contrato so na rodada nova
        {"id": "rpp-outro", "contrato_id": CONTRATO_OUTRO, "mes_competencia": "2026-02",
         "prestador_id": PRESTADOR_OUTRO, "rodada_id": ROD_NOVA, "saldo_pp": 5000.00},
    ]


def _build_mock_client(rpps_data, contratos_data, txs_data, rodadas_data):
    client = MagicMock()

    def side(nome):
        qb = MagicMock()
        for m in ("select", "eq", "lt", "in_", "limit", "order", "not_", "is_", "gte", "lte"):
            getattr(qb, m).return_value = qb
        if nome == "registro_pp":
            qb.execute.return_value = MagicMock(data=rpps_data)
        elif nome == "contrato":
            qb.execute.return_value = MagicMock(data=contratos_data)
        elif nome == "transacao_bancaria":
            qb.execute.return_value = MagicMock(data=txs_data)
        elif nome == "rodada":
            qb.execute.return_value = MagicMock(data=rodadas_data)
        else:
            qb.execute.return_value = MagicMock(data=[])
        return qb
    client.table.side_effect = side
    return client


def test_listar_contratos_unai_descarta_pp_antigo_para_mesmos_prestadores():
    """GET /contratos?competencia=2026-02 — Unai com PP re-importado.

    Esperado: total = R$ 7000 (soma uma vez por prestador, vencendo
    a rodada mais recente). Sem filtro daria R$ 14000.
    """
    from backend.api.routers.contratos_competencia import listar_contratos

    rpps = _rpps_unai_re_importado_em_2_rodadas()
    contratos_meta = [
        {"id": CONTRATO_UNAI, "uf": "MG", "cidade": "UNAI"},
        {"id": CONTRATO_OUTRO, "uf": "SP", "cidade": "OUTRO"},
    ]
    rodadas_meta = [
        {"id": ROD_BASE, "criado_em": "2026-04-19T15:00:00+00:00"},
        {"id": ROD_NOVA, "criado_em": "2026-04-25T02:30:00+00:00"},
    ]
    txs = []
    mock_client = _build_mock_client(rpps, contratos_meta, txs, rodadas_meta)

    fake_user = {"jwt": "fake", "id": "u1"}
    with patch(
        "backend.api.routers.contratos_competencia.get_supabase_authed",
        return_value=mock_client,
    ):
        out = listar_contratos(competencia="2026-02", current=fake_user)

    by_id = {x.id: x for x in out}
    assert by_id[CONTRATO_UNAI].total == 7000.00
    assert by_id[CONTRATO_UNAI].prestadores == 2
    assert by_id[CONTRATO_UNAI].data_pagamento is None  # zero PIX
    assert by_id[CONTRATO_OUTRO].total == 5000.00


def test_listar_contratos_quitado_traz_data_pagamento():
    """Contrato com PIX que somam saldo total → status PAGO + data_pagamento preenchido.

    Cenario: PP de C_QUIT 02.26 importado em 1 rodada, com 1 prestador,
    pago em 2 PIX que totalizam o saldo."""
    from datetime import date
    from backend.api.routers.contratos_competencia import listar_contratos

    rpps = [
        {"id": "rpp1", "contrato_id": "C_QUIT", "mes_competencia": "2026-02",
         "prestador_id": "P1", "rodada_id": "R1", "saldo_pp": 1000.00},
    ]
    contratos_meta = [{"id": "C_QUIT", "uf": "SP", "cidade": "TESTE"}]
    rodadas_meta = [{"id": "R1", "criado_em": "2026-04-25T10:00:00+00:00"}]
    txs = [
        {"registro_pp_id": "rpp1", "valor": -600.00, "data_extrato": "2026-04-15"},
        {"registro_pp_id": "rpp1", "valor": -400.00, "data_extrato": "2026-04-20"},
    ]
    mock_client = _build_mock_client(rpps, contratos_meta, txs, rodadas_meta)

    fake_user = {"jwt": "fake", "id": "u1"}
    with patch(
        "backend.api.routers.contratos_competencia.get_supabase_authed",
        return_value=mock_client,
    ):
        out = listar_contratos(competencia="2026-02", current=fake_user)

    item = next(x for x in out if x.id == "C_QUIT")
    assert item.status == "PAGO"
    assert item.data_pagamento == date(2026, 4, 20)
    assert item.total_pago == 1000.00


def test_listar_contratos_parcial_data_vazia():
    """PIX cobre parcialmente → PARCIAL + data_pagamento None."""
    from backend.api.routers.contratos_competencia import listar_contratos

    rpps = [
        {"id": "rpp1", "contrato_id": "C_PARC", "mes_competencia": "2026-02",
         "prestador_id": "P1", "rodada_id": "R1", "saldo_pp": 1000.00},
    ]
    contratos_meta = [{"id": "C_PARC", "uf": "SP", "cidade": "TESTE"}]
    rodadas_meta = [{"id": "R1", "criado_em": "2026-04-25T10:00:00+00:00"}]
    txs = [
        {"registro_pp_id": "rpp1", "valor": -300.00, "data_extrato": "2026-04-15"},
    ]
    mock_client = _build_mock_client(rpps, contratos_meta, txs, rodadas_meta)
    fake_user = {"jwt": "fake", "id": "u1"}
    with patch(
        "backend.api.routers.contratos_competencia.get_supabase_authed",
        return_value=mock_client,
    ):
        out = listar_contratos(competencia="2026-02", current=fake_user)

    item = next(x for x in out if x.id == "C_PARC")
    assert item.status == "PARCIAL"
    assert item.data_pagamento is None


def test_listar_contratos_pix_cross_rodada_contam():
    """Cenario operacional do Hugo: PP importado em rodada Abril, depois
    re-importado em rodada Maio, depois Junho. PIX entrou em rodadas distintas.
    Sistema deve somar TODOS os PIX de todas as rodadas para o mesmo prestador,
    e usar saldo_pp da rodada mais recente.
    """
    from datetime import date
    from backend.api.routers.contratos_competencia import listar_contratos

    # PP de Unai 02.26: Dr. A R$ 1000, importado em 3 rodadas (Abril, Maio, Junho)
    rpps = [
        {"id": "rpp-abr-A", "contrato_id": "C_UNAI", "mes_competencia": "2026-02",
         "prestador_id": "P_A", "rodada_id": "R_ABR", "saldo_pp": 1000.00},
        {"id": "rpp-mai-A", "contrato_id": "C_UNAI", "mes_competencia": "2026-02",
         "prestador_id": "P_A", "rodada_id": "R_MAI", "saldo_pp": 1000.00},
        {"id": "rpp-jun-A", "contrato_id": "C_UNAI", "mes_competencia": "2026-02",
         "prestador_id": "P_A", "rodada_id": "R_JUN", "saldo_pp": 1000.00},
    ]
    contratos_meta = [{"id": "C_UNAI", "uf": "MG", "cidade": "UNAI"}]
    rodadas_meta = [
        {"id": "R_ABR", "criado_em": "2026-04-15T10:00:00+00:00"},
        {"id": "R_MAI", "criado_em": "2026-05-20T10:00:00+00:00"},
        {"id": "R_JUN", "criado_em": "2026-06-10T10:00:00+00:00"},
    ]
    # PIX classificados em rodadas distintas, todos do mesmo prestador
    txs = [
        {"registro_pp_id": "rpp-abr-A", "valor": -400.00, "data_extrato": "2026-04-12"},
        {"registro_pp_id": "rpp-mai-A", "valor": -300.00, "data_extrato": "2026-05-18"},
        {"registro_pp_id": "rpp-jun-A", "valor": -300.00, "data_extrato": "2026-06-05"},
    ]
    mock_client = _build_mock_client(rpps, contratos_meta, txs, rodadas_meta)
    fake_user = {"jwt": "fake", "id": "u1"}
    with patch(
        "backend.api.routers.contratos_competencia.get_supabase_authed",
        return_value=mock_client,
    ):
        out = listar_contratos(competencia="2026-02", current=fake_user)

    item = next(x for x in out if x.id == "C_UNAI")
    # Saldo da rodada mais recente (Junho), uma vez
    assert item.total == 1000.00
    # Pago: 400 + 300 + 300 = 1000 (todos os PIX, qualquer rodada)
    assert item.total_pago == 1000.00
    assert item.status == "PAGO"
    # Data do PIX mais recente
    assert item.data_pagamento == date(2026, 6, 5)


def test_listar_anteriores_inclui_quitado_no_mes_do_filtro():
    """Itaju 02.26 quitado em jun/2026 deve aparecer em 'Anteriores' quando
    o filtro 'ate' for 2026-06 (o proprio mes da quitacao). Em meses
    posteriores nao aparece mais."""
    from datetime import date
    from backend.api.routers.contratos_competencia import listar_anteriores_fechadas

    rpps = [
        {"id": "r1", "contrato_id": "C_ITAJU", "mes_competencia": "2026-02",
         "prestador_id": "P1", "rodada_id": "R1", "saldo_pp": 500.00},
        {"id": "r2", "contrato_id": "C_ITAJU", "mes_competencia": "2026-02",
         "prestador_id": "P2", "rodada_id": "R1", "saldo_pp": 500.00},
    ]
    contratos_meta = [{"id": "C_ITAJU", "uf": "SP", "cidade": "ITAJU"}]
    rodadas_meta = [{"id": "R1", "criado_em": "2026-04-25T10:00:00+00:00"}]
    txs = [
        {"registro_pp_id": "r1", "valor": -500.00, "data_extrato": "2026-04-12"},
        {"registro_pp_id": "r2", "valor": -500.00, "data_extrato": "2026-06-12"},
    ]
    mock_client = _build_mock_client(rpps, contratos_meta, txs, rodadas_meta)

    fake_user = {"jwt": "fake", "id": "u1"}

    # Filtro ate=2026-06: mostra Itaju 02.26 como QUITADO em jun/26 (mesmo mes)
    with patch(
        "backend.api.routers.contratos_competencia.get_supabase_authed",
        return_value=mock_client,
    ):
        out_jun = listar_anteriores_fechadas(ate="2026-06", current=fake_user)
    items_jun = [x for x in out_jun if x.contrato_id == "C_ITAJU"]
    assert len(items_jun) == 1
    assert items_jun[0].status == "QUITADO"
    assert items_jun[0].data_pagamento == date(2026, 6, 12)


def test_listar_anteriores_nao_inclui_quitado_de_mes_passado():
    """Mesmo Itaju, mas filtro ate=2026-07 (1 mes apos quitacao) — nao aparece."""
    from backend.api.routers.contratos_competencia import listar_anteriores_fechadas

    rpps = [
        {"id": "r1", "contrato_id": "C_ITAJU", "mes_competencia": "2026-02",
         "prestador_id": "P1", "rodada_id": "R1", "saldo_pp": 500.00},
    ]
    contratos_meta = [{"id": "C_ITAJU", "uf": "SP", "cidade": "ITAJU"}]
    rodadas_meta = [{"id": "R1", "criado_em": "2026-04-25T10:00:00+00:00"}]
    txs = [
        {"registro_pp_id": "r1", "valor": -500.00, "data_extrato": "2026-06-12"},
    ]
    mock_client = _build_mock_client(rpps, contratos_meta, txs, rodadas_meta)

    fake_user = {"jwt": "fake", "id": "u1"}
    with patch(
        "backend.api.routers.contratos_competencia.get_supabase_authed",
        return_value=mock_client,
    ):
        out_jul = listar_anteriores_fechadas(ate="2026-07", current=fake_user)
    items_jul = [x for x in out_jul if x.contrato_id == "C_ITAJU"]
    assert len(items_jul) == 0


def test_listar_anteriores_em_aberto_nao_tem_data():
    """PARCIAL fica em Anteriores Em Aberto sem data_pagamento."""
    from backend.api.routers.contratos_competencia import listar_anteriores

    rpps = [
        {"id": "r1", "contrato_id": "C_PARC", "mes_competencia": "2026-02",
         "prestador_id": "P1", "rodada_id": "R1", "saldo_pp": 1000.00},
    ]
    contratos_meta = [{"id": "C_PARC", "uf": "SP", "cidade": "TESTE"}]
    rodadas_meta = [{"id": "R1", "criado_em": "2026-04-25T10:00:00+00:00"}]
    txs = [
        {"registro_pp_id": "r1", "valor": -300.00, "data_extrato": "2026-04-15"},
    ]
    mock_client = _build_mock_client(rpps, contratos_meta, txs, rodadas_meta)

    fake_user = {"jwt": "fake", "id": "u1"}
    with patch(
        "backend.api.routers.contratos_competencia.get_supabase_authed",
        return_value=mock_client,
    ):
        out = listar_anteriores(ate="2026-04", current=fake_user)
    items = [x for x in out if x.contrato_id == "C_PARC"]
    assert len(items) == 1
    assert items[0].status == "PARCIAL"
    assert items[0].data_pagamento is None


def test_detalhe_unai_lista_so_prestadores_da_rodada_mais_recente():
    """GET /contratos/{UNAI}/competencia/2026-02 — apos filtro per-prestador,
    lista apenas 2 registros (1 por prestador, da rodada mais recente),
    nao 4 (somando rodada antiga e nova)."""
    from backend.api.routers.contratos_competencia import detalhe

    # Filtra apenas rpps de Unai do fixture (descarta rpp-outro)
    rpps_filtrados = [
        r for r in _rpps_unai_re_importado_em_2_rodadas() if r["contrato_id"] == CONTRATO_UNAI
    ]
    # detalhe espera campos extra (local_pp + prestador embutido)
    for r in rpps_filtrados:
        r["local_pp"] = "UNAI - PSF"
        r["prestador"] = {"nome": f"Dr {r['prestador_id'][:6]}"}

    contratos_meta = [{
        "id": CONTRATO_UNAI, "uf": "MG", "cidade": "UNAI",
        "nome_oficial": None, "cnpj": None, "tipo": None,
        "valor_faturamento_mensal": None, "retencao_tributaria_pct": None,
        "observacoes": None,
    }]
    rodadas_meta = [
        {"id": ROD_BASE, "criado_em": "2026-04-19T15:00:00+00:00"},
        {"id": ROD_NOVA, "criado_em": "2026-04-25T02:30:00+00:00"},
    ]
    txs = []
    mock_client = _build_mock_client(rpps_filtrados, contratos_meta, txs, rodadas_meta)

    fake_user = {"jwt": "fake", "id": "u1"}
    with patch(
        "backend.api.routers.contratos_competencia.get_supabase_authed",
        return_value=mock_client,
    ):
        out = detalhe(contrato_id=CONTRATO_UNAI, competencia="2026-02", current=fake_user)

    # Sem filtro: 4 rpps, total = 14000. Com filtro per-prestador: 2 rpps, total = 7000.
    assert out.prestadores_count == 2
    assert out.total == 7000.00
    assert out.registros_count == 2
    # Cada prestador aparece exatamente uma vez nas linhas
    prest_ids = [l.prestador_id for l in out.linhas]
    assert prest_ids.count(PRESTADOR_A) == 1
    assert prest_ids.count(PRESTADOR_B) == 1
