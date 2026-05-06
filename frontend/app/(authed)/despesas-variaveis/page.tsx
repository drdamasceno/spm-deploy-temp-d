"use client";
import { useEffect, useState, useMemo, useCallback } from "react";
import { useFilters } from "@/lib/filters-context";
import { listarEmpresas, listarCategorias, listarProjetos } from "@/lib/api/catalogos";
import { apiClient } from "@/lib/api";
import {
  listarOrcamentos,
  listarLinhasDoOrcamento,
} from "@/lib/api/orcamento";
import {
  getRealizadoPorLinha,
  getMargemPorContrato,
  type RealizadoPorLinha,
  type MargemPorContrato,
} from "@/lib/api/margem";
import { TabelaLinhas } from "@/components/orcamento/tabela-linhas";
import { LinhaEditorModal } from "@/components/orcamento/linha-editor-modal";
import { DrawerMultiConta } from "@/components/conciliacao/drawer-multi-conta";
import { DrawerMargemPrestadores } from "@/components/contratos/drawer-margem-prestadores";
import type {
  EmpresaOut,
  CategoriaOut,
  ProjetoOut,
  OrcamentoOut,
  OrcamentoLinhaOut,
} from "@/types/v2";
import { formatBRL } from "@/lib/format";
import { toast } from "sonner";

// Aba Despesas Variáveis — mão-de-obra de plantão por contrato
// (natureza=DESPESA_PROFISSIONAIS). Característica única: o "Pago" prefere
// retorno_pix CNAB-240 (fonte determinística do banco) e cai em fallback
// para conciliacao_orcamento se CNAB ainda não chegou.
//
// KPIs adicionam Margem (Faturamento - Despesa Profissionais) consumindo
// /margem/por-contrato — reusa dado do orçamento, sem cálculo separado.
export default function DespesasVariaveisPage() {
  const { competencia } = useFilters();
  const [empresas, setEmpresas] = useState<EmpresaOut[]>([]);
  const [orcamentoAtual, setOrcamentoAtual] = useState<OrcamentoOut | null>(null);
  const [linhas, setLinhas] = useState<OrcamentoLinhaOut[]>([]);
  const [categorias, setCategorias] = useState<CategoriaOut[]>([]);
  const [projetos, setProjetos] = useState<ProjetoOut[]>([]);
  const [contratoRotuloPorId, setContratoRotuloPorId] = useState<Record<string, string>>({});
  const [realizadoPorLinhaId, setRealizadoPorLinhaId] = useState<Record<string, RealizadoPorLinha>>({});
  const [margemContratos, setMargemContratos] = useState<MargemPorContrato[]>([]);
  const [loading, setLoading] = useState(true);
  const [linhaEditando, setLinhaEditando] = useState<OrcamentoLinhaOut | null>(null);
  const [linhaConciliacao, setLinhaConciliacao] = useState<OrcamentoLinhaOut | null>(null);
  // Drilldown de prestadores: usado quando linha tem contrato_id (caso normal
  // em DESPESA_PROFISSIONAIS). Mostra rateio de margem por médico via
  // /margem/por-profissional.
  const [drawerPrestadores, setDrawerPrestadores] = useState<{
    contratoId: string;
    rotulo: string;
  } | null>(null);

  const recarregar = useCallback(async () => {
    setLoading(true);
    try {
      const [emps, orcs, cats, projs, contratosResp] = await Promise.all([
        listarEmpresas(),
        listarOrcamentos({ competencia }),
        listarCategorias(),
        listarProjetos(),
        apiClient
          .get<Array<{ id: string; uf: string; cidade: string }>>("/contratos")
          .then((r) => r.data)
          .catch(() => []),
      ]);
      setEmpresas(emps);
      setCategorias(cats);
      setProjetos(projs);
      const rotulos: Record<string, string> = {};
      for (const c of contratosResp) {
        if (!rotulos[c.id]) rotulos[c.id] = `${c.uf}-${c.cidade}`;
      }
      setContratoRotuloPorId(rotulos);
      const atual = orcs[0] ?? null;
      setOrcamentoAtual(atual);
      if (atual) {
        const [ls, realizadosArr, margens] = await Promise.all([
          listarLinhasDoOrcamento(atual.id, "DESPESA_PROFISSIONAIS"),
          getRealizadoPorLinha(atual.id).catch(() => []),
          getMargemPorContrato(competencia, atual.empresa_id).catch(() => []),
        ]);
        setLinhas(ls);
        const map: Record<string, RealizadoPorLinha> = {};
        for (const r of realizadosArr) map[r.linha_id] = r;
        setRealizadoPorLinhaId(map);
        setMargemContratos(margens);
      } else {
        setLinhas([]);
        setRealizadoPorLinhaId({});
        setMargemContratos([]);
      }
    } catch (e: unknown) {
      toast.error("Falha: " + (e instanceof Error ? e.message : "erro"));
    } finally {
      setLoading(false);
    }
  }, [competencia]);

  const categoriaPorId = useMemo(() => {
    const m: Record<string, CategoriaOut> = {};
    categorias.forEach((c) => { m[c.id] = c; });
    return m;
  }, [categorias]);

  const projetoPorId = useMemo(() => {
    const m: Record<string, ProjetoOut> = {};
    projetos.forEach((p) => { m[p.id] = p; });
    return m;
  }, [projetos]);

  useEffect(() => { recarregar(); }, [recarregar]);

  const totalPrevisto = useMemo(
    () => linhas.reduce((acc, l) => acc + l.valor_previsto, 0),
    [linhas]
  );
  // Variáveis: prefere pago_cnab (retorno_pix), fallback pra pago (conciliacao_orcamento)
  const totalPago = useMemo(
    () =>
      linhas.reduce((acc, l) => {
        const r = realizadoPorLinhaId[l.id];
        const pago = (r?.pago_cnab ?? 0) || (r?.pago ?? 0);
        return acc + pago;
      }, 0),
    [linhas, realizadoPorLinhaId]
  );
  const saldo = totalPrevisto - totalPago;

  const margemRealizadaTotal = useMemo(
    () => margemContratos.reduce((acc, m) => acc + m.margem_realizado, 0),
    [margemContratos]
  );
  const faturamentoRealizadoTotal = useMemo(
    () => margemContratos.reduce((acc, m) => acc + m.faturamento_realizado, 0),
    [margemContratos]
  );
  const margemPctRealizada =
    faturamentoRealizadoTotal > 0
      ? (margemRealizadaTotal / faturamentoRealizadoTotal) * 100
      : null;
  // Quando realizado=0 (sem PIX recebido nem pago), mostra margem PREVISTA
  // pra evitar UI vazia. Decisão de design — comunica margem esperada.
  const margemPrevistaTotal = useMemo(
    () => margemContratos.reduce((acc, m) => acc + m.margem_previsto, 0),
    [margemContratos]
  );
  const faturamentoPrevistoTotal = useMemo(
    () => margemContratos.reduce((acc, m) => acc + m.faturamento_previsto, 0),
    [margemContratos]
  );
  const margemPctPrevista =
    faturamentoPrevistoTotal > 0
      ? (margemPrevistaTotal / faturamentoPrevistoTotal) * 100
      : null;

  if (loading) return <div className="p-6 text-slate-500">Carregando...</div>;

  return (
    <div className="flex flex-col">
      <div className="bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between">
        <h1 className="text-base font-semibold text-slate-900">
          Despesas Variáveis · {competencia}
        </h1>
      </div>

      {orcamentoAtual && (
        <div className="bg-slate-50 border-b border-slate-200 px-4 py-3 grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiMini label="Despesa Prevista" value={formatBRL(totalPrevisto)} destaque />
          <KpiMini label="Pago (CNAB+heur)" value={formatBRL(totalPago)} />
          <KpiMini
            label="Saldo"
            value={formatBRL(saldo)}
            corValor={saldo >= -0.01 ? "text-emerald-700" : "text-red-700"}
          />
          <KpiMini
            label={margemPctRealizada !== null ? "Margem Realizada" : "Margem Prevista"}
            value={
              margemPctRealizada !== null
                ? `${formatBRL(margemRealizadaTotal)} (${margemPctRealizada.toFixed(1)}%)`
                : margemPctPrevista !== null
                  ? `${formatBRL(margemPrevistaTotal)} (${margemPctPrevista.toFixed(1)}% est.)`
                  : "—"
            }
            corValor={
              (margemPctRealizada !== null ? margemRealizadaTotal : margemPrevistaTotal) >= 0
                ? "text-emerald-700"
                : "text-red-700"
            }
          />
        </div>
      )}

      {orcamentoAtual ? (
        <>
          <div className="bg-slate-50 px-4 py-2 text-xs text-slate-600 border-b border-slate-200">
            Total previsto: <b className="text-slate-900 tabular-nums">{formatBRL(totalPrevisto)}</b>
            {" · "}
            Total pago: <b className="text-slate-900 tabular-nums">{formatBRL(totalPago)}</b>
            {" · "}
            {linhas.length} contrato(s) com mão-de-obra prevista
          </div>
          <TabelaLinhas
            linhas={linhas}
            categoriaPorId={categoriaPorId}
            projetoPorId={projetoPorId}
            onRowClick={(l) => {
              // Linha com contrato vinculado → abre drilldown de prestadores
              // (rateio de margem por médico). Sem contrato → cai no drawer
              // de conciliação bancária (caso raro pra DESPESA_PROFISSIONAIS).
              if (l.contrato_id) {
                const rotulo =
                  contratoRotuloPorId[l.contrato_id] ?? l.titular_razao_social;
                setDrawerPrestadores({ contratoId: l.contrato_id, rotulo });
              } else {
                setLinhaConciliacao(l);
              }
            }}
            empresaCodigoPorId={Object.fromEntries(empresas.map((e) => [e.id, e.codigo]))}
            empresaOrcamentoId={orcamentoAtual?.empresa_id}
            contratoRotuloPorId={contratoRotuloPorId}
            modo="variaveis"
            realizadoPorLinhaId={realizadoPorLinhaId}
          />
        </>
      ) : (
        <div className="p-6 text-slate-500 text-sm">
          Sem orçamento para {competencia}. Suba um XLSX em <b>Despesas Fixas</b>.
        </div>
      )}

      <DrawerMultiConta
        linha={linhaConciliacao}
        onClose={() => setLinhaConciliacao(null)}
        onEditar={(l) => {
          setLinhaConciliacao(null);
          setLinhaEditando(l);
        }}
      />

      <DrawerMargemPrestadores
        contratoId={drawerPrestadores?.contratoId ?? null}
        rotuloContrato={drawerPrestadores?.rotulo ?? null}
        competencia={competencia}
        onClose={() => setDrawerPrestadores(null)}
      />

      <LinhaEditorModal
        linha={linhaEditando}
        categoriaPorId={categoriaPorId}
        onClose={(atualizada) => {
          if (atualizada) {
            setLinhas((prev) => prev.map((x) => (x.id === atualizada.id ? atualizada : x)));
          }
          setLinhaEditando(null);
        }}
        onDelete={(linhaId) => {
          setLinhas((prev) => prev.filter((x) => x.id !== linhaId));
        }}
      />
    </div>
  );
}

function KpiMini({
  label,
  value,
  destaque = false,
  corValor,
}: {
  label: string;
  value: string;
  destaque?: boolean;
  corValor?: string;
}) {
  return (
    <div className={destaque ? "bg-slate-900 text-white rounded px-3 py-2" : "bg-white border border-slate-200 rounded px-3 py-2"}>
      <div className={`text-[10px] uppercase tracking-wide ${destaque ? "text-slate-300" : "text-slate-500"}`}>
        {label}
      </div>
      <div className={`text-sm font-bold tabular-nums ${corValor ?? (destaque ? "text-white" : "text-slate-900")}`}>
        {value}
      </div>
    </div>
  );
}
