"use client";
import { useEffect, useMemo, useState } from "react";
import { useFilters } from "@/lib/filters-context";
import { listarOrcamentos } from "@/lib/api/orcamento";
import { listarEmpresas } from "@/lib/api/catalogos";
import {
  fetchSugestoes,
  aplicarConciliacao,
  lookupDetalhes,
  type TransacaoDetalhe,
  type OrcamentoLinhaDetalhe,
} from "@/lib/api/conciliacao";
import type { SugestaoOut, OrcamentoOut, EmpresaOut } from "@/types/v2";
import { toast } from "sonner";
import { TwoPanel } from "@/components/conciliacao/two-panel";

export default function ConciliacaoPage() {
  const { empresa, competencia } = useFilters();
  const [empresas, setEmpresas] = useState<EmpresaOut[]>([]);
  const [orcamento, setOrcamento] = useState<OrcamentoOut | null>(null);
  const [sugestoes, setSugestoes] = useState<SugestaoOut[]>([]);
  const [txDetalhes, setTxDetalhes] = useState<Map<string, TransacaoDetalhe>>(
    new Map()
  );
  const [linhaDetalhes, setLinhaDetalhes] = useState<
    Map<string, OrcamentoLinhaDetalhe>
  >(new Map());
  const [selecionadas, setSelecionadas] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [aplicando, setAplicando] = useState(false);

  // Carrega empresas uma vez (para resolver codigo -> empresa_id no filtro).
  useEffect(() => {
    listarEmpresas()
      .then(setEmpresas)
      .catch(() => {
        /* silencioso; se falhar cai no fluxo sem filtro */
      });
  }, []);

  // Resolve empresa_id via codigo do FiltersContext.
  // Se empresa=="TODAS", nao passa filtro (traz todos os orcamentos da competencia).
  const empresaId = useMemo(() => {
    if (empresa === "TODAS") return undefined;
    return empresas.find((e) => e.codigo === empresa)?.id;
  }, [empresa, empresas]);

  const recarregar = async () => {
    setLoading(true);
    setSelecionadas(new Set());
    try {
      const orcs = await listarOrcamentos({
        competencia,
        empresa_id: empresaId,
      });
      if (!orcs.length) {
        setOrcamento(null);
        setSugestoes([]);
        setTxDetalhes(new Map());
        setLinhaDetalhes(new Map());
        setLoading(false);
        return;
      }
      const orc = orcs[0];
      setOrcamento(orc);

      const sugs = await fetchSugestoes({ orcamento_id: orc.id });
      setSugestoes(sugs);

      const txIds = Array.from(new Set(sugs.map((s) => s.transacao_id)));
      const linhaIds = Array.from(
        new Set(sugs.map((s) => s.orcamento_linha_id))
      );
      if (txIds.length === 0 && linhaIds.length === 0) {
        setTxDetalhes(new Map());
        setLinhaDetalhes(new Map());
      } else {
        const det = await lookupDetalhes({
          transacao_ids: txIds,
          orcamento_linha_ids: linhaIds,
        });
        setTxDetalhes(new Map(det.transacoes.map((t) => [t.id, t])));
        setLinhaDetalhes(new Map(det.orcamento_linhas.map((l) => [l.id, l])));
      }
    } catch (e: unknown) {
      const msg =
        e instanceof Error
          ? e.message
          : typeof e === "object" && e && "message" in e
          ? String((e as { message?: string }).message ?? "")
          : "erro";
      toast.error("Falha ao carregar: " + msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // espera empresas carregarem se o filtro exige resolucao
    if (empresa !== "TODAS" && empresas.length === 0) return;
    recarregar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [empresa, competencia, empresaId, empresas.length]);

  const stats = useMemo(() => {
    const por_origem: Record<string, number> = {
      REGRA: 0,
      SIMILARIDADE: 0,
      VALOR: 0,
      MANUAL: 0,
    };
    sugestoes.forEach((s) => {
      por_origem[s.origem] = (por_origem[s.origem] ?? 0) + 1;
    });
    return por_origem;
  }, [sugestoes]);

  async function confirmarTodosSugeridosRegra() {
    const de_regra = sugestoes.filter((s) => s.origem === "REGRA");
    if (!de_regra.length) {
      toast.info("Nenhuma sugestao de alta confianca (REGRA) para aplicar");
      return;
    }
    setAplicando(true);
    let ok = 0;
    let erros = 0;
    for (const s of de_regra) {
      try {
        await aplicarConciliacao({
          transacao_id: s.transacao_id,
          orcamento_linha_id: s.orcamento_linha_id,
          valor_aplicado: s.valor_aplicado,
          confianca: s.confianca,
          origem: s.origem,
        });
        ok++;
      } catch {
        erros++;
      }
    }
    if (erros === 0) toast.success(`${ok} sugestoes aplicadas`);
    else toast.warning(`${ok} aplicadas, ${erros} falharam`);
    await recarregar();
    setAplicando(false);
  }

  async function confirmarSelecionadas() {
    const idxs = Array.from(selecionadas);
    if (!idxs.length) {
      toast.info("Nenhuma sugestao selecionada");
      return;
    }
    setAplicando(true);
    let ok = 0;
    let erros = 0;
    for (const i of idxs) {
      const s = sugestoes[i];
      if (!s) continue;
      try {
        await aplicarConciliacao({
          transacao_id: s.transacao_id,
          orcamento_linha_id: s.orcamento_linha_id,
          valor_aplicado: s.valor_aplicado,
          confianca: s.confianca,
          origem: s.origem,
        });
        ok++;
      } catch {
        erros++;
      }
    }
    if (erros === 0) toast.success(`${ok} sugestoes aplicadas`);
    else toast.warning(`${ok} aplicadas, ${erros} falharam`);
    setSelecionadas(new Set());
    await recarregar();
    setAplicando(false);
  }

  if (loading) {
    return <div className="p-6 text-slate-500">Carregando sugestoes...</div>;
  }
  if (!orcamento) {
    return (
      <div className="p-6 text-slate-500">
        Nenhum orcamento encontrado para a competencia {competencia}
        {empresa !== "TODAS" ? ` / ${empresa}` : ""}. Faca upload de um
        orcamento na tela{" "}
        <a className="underline text-blue-600" href="/orcamento">
          Orcamento
        </a>{" "}
        primeiro.
      </div>
    );
  }

  return (
    <div className="p-6 space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-lg font-semibold text-slate-900">
          Conciliacao Extrato x Orcamento · {competencia}
        </h1>
        <div className="text-xs text-slate-600 flex gap-3 flex-wrap items-center">
          <span>
            <span className="text-emerald-600">●</span> REGRA:{" "}
            <b>{stats.REGRA}</b>
          </span>
          <span>
            <span className="text-yellow-500">●</span> SIMILARIDADE:{" "}
            <b>{stats.SIMILARIDADE}</b>
          </span>
          <span>
            <span className="text-slate-400">●</span> VALOR:{" "}
            <b>{stats.VALOR}</b>
          </span>
          <a
            href="/conciliacao/intragrupo"
            className="px-2 py-1 rounded border border-amber-300 bg-amber-50 text-amber-900 hover:bg-amber-100 text-[11px] font-medium"
            title="Conciliar PIX SPM→FD em lote (FIFO contra linhas empresa_pagadora=FD)"
          >
            PIX intragrupo →
          </a>
        </div>
      </div>

      <TwoPanel
        sugestoes={sugestoes}
        txDetalhes={txDetalhes}
        linhaDetalhes={linhaDetalhes}
        selecionadas={selecionadas}
        empresaCodigo={empresa !== "TODAS" ? empresa : undefined}
        onToggle={(i) =>
          setSelecionadas((prev) => {
            const next = new Set(prev);
            if (next.has(i)) next.delete(i);
            else next.add(i);
            return next;
          })
        }
      />

      <div className="flex gap-2 justify-end pt-2 border-t border-slate-200">
        <button
          className="px-3 py-2 text-sm rounded-md border border-slate-300 bg-white hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={aplicando || selecionadas.size === 0}
          onClick={confirmarSelecionadas}
        >
          Confirmar {selecionadas.size} selecionadas
        </button>
        <button
          className="px-3 py-2 text-sm rounded-md bg-emerald-600 text-white font-medium hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={aplicando || stats.REGRA === 0}
          onClick={confirmarTodosSugeridosRegra}
        >
          Confirmar TODOS os {stats.REGRA} sugeridos (alta confianca)
        </button>
      </div>
    </div>
  );
}
