"""
Script idempotente de backfill de prestador.pj_empregadora_id para empresa FD.

Uso:
    python -m backend.scripts.backfill_pj_empregadora \
        --config backend/scripts/backfill_pj_empregadora_config.json \
        --dry-run

    python -m backend.scripts.backfill_pj_empregadora \
        --config backend/scripts/backfill_pj_empregadora_config.json \
        --apply

Idempotente: prestadores com pj_empregadora_id ja preenchido sao ignorados.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field


@dataclass
class PlanoBackfill:
    empresa_id: str
    prestadores_a_vincular: list[dict] = field(default_factory=list)


def carregar_config(path: str) -> dict:
    """Le o arquivo JSON de configuracao e devolve o dict."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolver_empresa_id(client, codigo: str) -> str:
    """Busca empresa.id por codigo. Raise se nao achar."""
    resp = client.table("empresa").select("id,codigo").eq("codigo", codigo).execute()
    data = resp.data or []
    if not data:
        raise ValueError(f"Empresa com codigo={codigo!r} nao encontrada.")
    return data[0]["id"]


def _norm(s: str | None) -> str:
    """Normaliza: strip, upper e colapsa espaços múltiplos em um único espaço."""
    if s is None:
        return ""
    return " ".join(s.upper().split())


def encontrar_prestadores_por_nome(client, nomes: list[str]) -> list[dict]:
    """
    SELECT id, nome, razao_social_pj, pj_empregadora_id de prestador.
    Retorna os que:
      - tem pj_empregadora_id null, E
      - nome OR razao_social_pj (normalizado strip+upper) in nomes.
    Case-insensitive.
    """
    resp = (
        client.table("prestador")
        .select("id,nome,razao_social_pj,pj_empregadora_id")
        .execute()
    )
    linhas = resp.data or []
    alvos = {_norm(n) for n in nomes}
    matches: list[dict] = []
    for p in linhas:
        if p.get("pj_empregadora_id") is not None:
            continue
        nome_n = _norm(p.get("nome"))
        razao_n = _norm(p.get("razao_social_pj"))
        if nome_n in alvos or (razao_n and razao_n in alvos):
            matches.append(p)
    return matches


def encontrar_prestadores_por_cidade(client, cidades: list[str]) -> list[dict]:
    """
    Para cada entrada "CIDADE/UF" do JSON, busca contratos com cidade+uf
    correspondentes; pega registro_pp.prestador_id vinculados; retorna
    prestadores distintos sem pj_empregadora_id.

    Fix 2026-04-22: tabela contrato tem colunas `cidade` e `uf` separadas,
    não `cidade_uf`. Parse "CIDADE/UF" ao lidar com o JSON.
    """
    if not cidades:
        return []

    contrato_ids: list[str] = []
    for entrada in cidades:
        partes = [p.strip() for p in entrada.split("/")]
        if len(partes) != 2 or not partes[0] or not partes[1]:
            continue
        cidade, uf = partes[0].upper(), partes[1].upper()
        resp = (
            client.table("contrato")
            .select("id")
            .ilike("cidade", cidade)
            .ilike("uf", uf)
            .execute()
        )
        contrato_ids.extend(c["id"] for c in (resp.data or []))
    contrato_ids = list(set(contrato_ids))
    if not contrato_ids:
        return []

    rpp_resp = (
        client.table("registro_pp")
        .select("prestador_id,contrato_id")
        .in_("contrato_id", contrato_ids)
        .execute()
    )
    prestador_ids = list({r["prestador_id"] for r in (rpp_resp.data or []) if r.get("prestador_id")})
    if not prestador_ids:
        return []

    prest_resp = (
        client.table("prestador")
        .select("id,nome,razao_social_pj,pj_empregadora_id")
        .in_("id", prestador_ids)
        .execute()
    )
    return [p for p in (prest_resp.data or []) if p.get("pj_empregadora_id") is None]


def aplicar_backfill(client, plano: PlanoBackfill, dry_run: bool) -> None:
    """
    Se dry_run=True, apenas imprime. Senao, faz UPDATE prestador
    SET pj_empregadora_id = plano.empresa_id WHERE id = p.id para cada.
    """
    if not plano.prestadores_a_vincular:
        print("[backfill] Nenhum prestador para vincular. Nada a fazer.")
        return

    print(f"[backfill] empresa_id={plano.empresa_id}")
    print(f"[backfill] {len(plano.prestadores_a_vincular)} prestador(es) a vincular:")
    for p in plano.prestadores_a_vincular:
        nome = p.get("nome") or p.get("razao_social_pj") or "?"
        print(f"  - {p['id']}  {nome}")

    if dry_run:
        print("[backfill] DRY-RUN: nenhum update executado.")
        return

    for p in plano.prestadores_a_vincular:
        (
            client.table("prestador")
            .update({"pj_empregadora_id": plano.empresa_id})
            .eq("id", p["id"])
            .execute()
        )
    print(f"[backfill] APLICADO: {len(plano.prestadores_a_vincular)} prestador(es) atualizado(s).")


def _build_client():
    """Lazy import para nao quebrar testes unitarios com MagicMock."""
    import os
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY precisam estar no ambiente."
        )
    return create_client(url, key)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill idempotente de prestador.pj_empregadora_id."
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Caminho para o JSON de configuracao.",
    )
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--dry-run", action="store_true", help="Apenas imprime o plano.")
    grp.add_argument("--apply", action="store_true", help="Executa os updates.")
    args = parser.parse_args(argv)

    cfg = carregar_config(args.config)
    empresa_codigo = cfg["empresa_codigo"]
    nomes = cfg.get("prestadores") or []
    cidades = (cfg.get("contratos_lotados") or {}).get("cidades") or []

    client = _build_client()
    empresa_id = resolver_empresa_id(client, empresa_codigo)

    por_nome = encontrar_prestadores_por_nome(client, nomes)
    por_cidade = encontrar_prestadores_por_cidade(client, cidades)

    # dedup por id
    vistos: set[str] = set()
    prestadores: list[dict] = []
    for p in por_nome + por_cidade:
        if p["id"] in vistos:
            continue
        vistos.add(p["id"])
        prestadores.append(p)

    plano = PlanoBackfill(empresa_id=empresa_id, prestadores_a_vincular=prestadores)
    aplicar_backfill(client, plano, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
