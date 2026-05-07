"use client";
import { useEffect, useState, useMemo, useCallback, startTransition } from "react";
import { useFilters } from "@/lib/filters-context";
import { listarEmpresas, listarCategorias, listarProjetos } from "@/lib/api/catalogos";
import { apiClient } from "@/lib/api";
import {
  listarOrcamentos,
  listarLinhasDoOrcamento,
  validarOrcamento,
  replicarOrcamento,
  deletarOrcamento,
} from "@/lib/api/orcamento";
import { getRealizadoPorLinha, type RealizadoPorLinha } from "@/lib/api/margem";
import { TabsSecoes } from "@/components/orcamento/tabs-secoes";
import { TabelaLinhas } from "@/components/orcamento/tabela-linhas";
import { UploadXlsxDialog } from "@/components/orcamento/upload-xlsx-dialog";
import { LinhaEditorModal } from "@/components/orcamento/linha-editor-modal";
import { DrawerMultiConta } from "@/components/conciliacao/drawer-multi-conta";
import type {
  EmpresaOut,
  CategoriaOut,
  ProjetoOut,
  OrcamentoOut,
  OrcamentoLinhaOut,
  NaturezaOrcamento,
} from "@/types/v2";
import { formatBRL } from "@/lib/format";
import { toast } from "sonner";

// Naturezas que pertencem à aba Despesas Fixas. FATURAMENTO e
// DESPESA_PROFISSIONAIS foram extraídos pra abas próprias (/faturamento,
// /despesas-variaveis) na re-arquitetura de 2026-05-06.
const NATUREZAS_DESPESAS_FIXAS: NaturezaOrcamento[] = [
  "DESPESA_FIXA",
  "TRIBUTO",
  "SALARIO_VARIAVEL",
  "COMISSAO",
  "VALOR_VARIAVEL",
];

export default function DespesasFixasPage() {
  const { competencia } = useFilters();
  const [empresas, setEmpresas] = useState<EmpresaOut[]>([]);
  const [orcamentos, setOrcamentos] = useState<OrcamentoOut[]>([]);
  const [orcamentoAtual, setOrcamentoAtual] = useState<OrcamentoOut | null>(
    null
  );
  const [linhas, setLinhas] = useState<OrcamentoLinhaOut[]>([]);
  const [categorias, setCategorias] = useState<CategoriaOut[]>([]);
  const [projetos, setProjetos] = useState<ProjetoOut[]>([]);
  const [contratoRotuloPorId, setContratoRotuloPorId] = useState<Record<string, string>>({});
  // Tab inicial: TRIBUTO (maior número, top of mind). Pode evoluir pra
  // "PENDENTE" virtual que filtra linhas com categoria_id NULL — ver tab-pendente abaixo.
  const [tab, setTab] = useState<string>("TRIBUTO");
  const [loading, setLoading] = useState(true);
  const [realizadoPorLinhaId, setRealizadoPorLinhaId] = useState<Record<string, RealizadoPorLinha>>({});
  const [uploadOpen, setUploadOpen] = useState(false);
  const [linhaEditando, setLinhaEditando] =
    useState<OrcamentoLinhaOut | null>(null);
  const [linhaConciliacao, setLinhaConciliacao] =
    useState<OrcamentoLinhaOut | null>(null);

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
      setOrcamentos(orcs);
      setCategorias(cats);
      setProjetos(projs);
      // Dedup contratos por id (vêm múltiplas competências) e monta rótulo UF-cidade
      const rotulos: Record<string, string> = {};
      for (const c of contratosResp) {
        if (!rotulos[c.id]) rotulos[c.id] = `${c.uf}-${c.cidade}`;
      }
      setContratoRotuloPorId(rotulos);
      const atual = orcs[0] ?? null;
      setOrcamentoAtual(atual);
      if (atual) {
        const [ls, realizadosArr] = await Promise.all([
          listarLinhasDoOrcamento(atual.id),
          getRealizadoPorLinha(atual.id).catch(() => []),
        ]);
        // Filtra naturezas de outras abas — vivem em /faturamento e /despesas-variaveis
        setLinhas(ls.filter((l) => NATUREZAS_DESPESAS_FIXAS.includes(l.natureza)));
        const map: Record<string, RealizadoPorLinha> = {};
        for (const r of realizadosArr) map[r.linha_id] = r;
        setRealizadoPorLinhaId(map);
      } else {
        setLinhas([]);
        setRealizadoPorLinhaId({});
      }
    } catch (e: unknown) {
      toast.error("Falha: " + (e instanceof Error ? e.message : "erro"));
    } finally {
      setLoading(false);
    }
  }, [competencia]);

  const categoriaPorId = useMemo(() => {
    const m: Record<string, CategoriaOut> = {};
    categorias.forEach((c) => {
      m[c.id] = c;
    });
    return m;
  }, [categorias]);

  const projetoPorId = useMemo(() => {
    const m: Record<string, ProjetoOut> = {};
    projetos.forEach((p) => {
      m[p.id] = p;
    });
    return m;
  }, [projetos]);

  useEffect(() => {
    recarregar();
  }, [recarregar]);

  const contagens = useMemo(() => {
    const m: Record<string, number> = {
      DESPESA_FIXA: 0,
      TRIBUTO: 0,
      SALARIO_VARIAVEL: 0,
      COMISSAO: 0,
      VALOR_VARIAVEL: 0,
      DESPESA_PROFISSIONAIS: 0,
      FATURAMENTO: 0,
      // PENDENTE é virtual — count = linhas sem categoria_id (foco do usuário:
      // identificar e classificar pra que apareçam nos buckets corretos).
      PENDENTE: 0,
    };
    linhas.forEach((l) => {
      m[l.natureza] = (m[l.natureza] ?? 0) + 1;
      if (!l.categoria_id) m.PENDENTE = (m.PENDENTE ?? 0) + 1;
    });
    return m;
  }, [linhas]);

  const totaisRealizadosPorSecao = useMemo(() => {
    const m: Record<string, number> = {};
    linhas.forEach((l) => {
      const real = realizadoPorLinhaId[l.id]?.pago ?? 0;
      m[l.natureza] = (m[l.natureza] ?? 0) + real;
    });
    return m;
  }, [linhas, realizadoPorLinhaId]);

  const totalRealizado = useMemo(
    () => Object.values(totaisRealizadosPorSecao).reduce((a, b) => a + b, 0),
    [totaisRealizadosPorSecao]
  );

  // Tab "PENDENTE" é virtual: filtra linhas com categoria_id NULL em qualquer
  // natureza. As demais filtram por natureza específica.
  const linhasDoTab =
    tab === "PENDENTE"
      ? linhas.filter((l) => !l.categoria_id)
      : linhas.filter((l) => l.natureza === tab);

  const totalPrevisto = useMemo(
    () => linhasDoTab.reduce((acc, l) => acc + l.valor_previsto, 0),
    [linhasDoTab]
  );

  const totaisPorSecao = useMemo(() => {
    const m: Record<string, number> = {};
    linhas.forEach((l) => {
      m[l.natureza] = (m[l.natureza] ?? 0) + l.valor_previsto;
    });
    return m;
  }, [linhas]);

  // Breakdown por bolso — soma previsto + realizado pra cada um dos 4 bolsos
  // (SPM_OPERACIONAL, FD_VIA_SPM, HUGO_PESSOAL, INVESTIMENTO_HUGO).
  // Mostra "para onde vai o dinheiro" com barra de uso (% realizado/previsto).
  const totaisPorBolso = useMemo(() => {
    const m: Record<string, { previsto: number; realizado: number }> = {
      SPM_OPERACIONAL: { previsto: 0, realizado: 0 },
      FD_VIA_SPM: { previsto: 0, realizado: 0 },
      HUGO_PESSOAL: { previsto: 0, realizado: 0 },
      INVESTIMENTO_HUGO: { previsto: 0, realizado: 0 },
    };
    linhas.forEach((l) => {
      const bolso = l.bolso ?? "SPM_OPERACIONAL";
      const real = realizadoPorLinhaId[l.id]?.pago ?? 0;
      if (!m[bolso]) m[bolso] = { previsto: 0, realizado: 0 };
      m[bolso].previsto += l.valor_previsto;
      m[bolso].realizado += real;
    });
    return m;
  }, [linhas, realizadoPorLinhaId]);

  const totalGeral = useMemo(
    () =>
      linhas
        .filter((l) => l.natureza !== "FATURAMENTO")
        .reduce((acc, l) => acc + l.valor_previsto, 0),
    [linhas]
  );

  async function handleValidar() {
    if (!orcamentoAtual) return;
    try {
      await validarOrcamento(orcamentoAtual.id);
      toast.success("Orçamento validado");
      recarregar();
    } catch (e: unknown) {
      toast.error("Falha: " + (e instanceof Error ? e.message : "erro"));
    }
  }

  async function handleReplicar() {
    if (!orcamentoAtual) return;
    const proxima = proximaCompetencia(competencia);
    try {
      await replicarOrcamento(orcamentoAtual.id, proxima);
      toast.success(`Replicado para ${proxima}`);
    } catch (e: unknown) {
      toast.error("Falha: " + (e instanceof Error ? e.message : "erro"));
    }
  }

  if (loading)
    return <div className="p-6 text-slate-500">Carregando...</div>;

  return (
    <div className="flex flex-col">
      {/* sub-header com ações */}
      <div className="bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between">
        <h1 className="text-base font-semibold text-slate-900">
          Despesas Fixas · {competencia}
        </h1>
        <div className="flex gap-2">
          <button
            onClick={() => {
              // startTransition: prioriza a montagem do dialog sobre qualquer
              // reconciliacao pendente (tabela grande), evitando a "trava"
              // percebida ao abrir o dialog em orcamentos com muitas linhas.
              startTransition(() => setUploadOpen(true));
            }}
            className="px-3 py-1 text-xs rounded border border-slate-300 bg-white"
          >
            ↑ Upload XLSX
          </button>
          {orcamentoAtual && orcamentoAtual.status === "RASCUNHO" && (
            <button
              onClick={handleValidar}
              className="px-3 py-1 text-xs rounded bg-slate-900 text-white"
            >
              Validar
            </button>
          )}
          {orcamentoAtual && (
            <button
              onClick={handleReplicar}
              className="px-3 py-1 text-xs rounded bg-blue-600 text-white"
            >
              Replicar para próximo mês
            </button>
          )}
          {orcamentoAtual && orcamentoAtual.status !== "FECHADO" && (
            <button
              onClick={async () => {
                if (
                  !confirm(
                    `Deletar orçamento de ${competencia} (${orcamentoAtual.status}) e TODAS as suas linhas? Esta ação não pode ser desfeita.`
                  )
                ) {
                  return;
                }
                try {
                  await deletarOrcamento(orcamentoAtual.id);
                  toast.success(`Orçamento ${competencia} deletado`);
                  recarregar();
                } catch (err) {
                  toast.error(
                    "Falha: " + (err instanceof Error ? err.message : "erro")
                  );
                }
              }}
              className="px-3 py-1 text-xs rounded bg-red-600 text-white hover:bg-red-700"
              title="Deletar orçamento atual (permite novo upload)"
            >
              Deletar orçamento
            </button>
          )}
        </div>
      </div>

      {/* strip de meses */}
      <div className="bg-white border-b border-slate-200 px-4 py-2 flex gap-2 text-xs text-slate-600">
        {orcamentos.length === 0 ? (
          <span>Nenhum orçamento para {competencia}.</span>
        ) : (
          orcamentos.map((o) => (
            <span
              key={o.id}
              className="px-2 py-1 rounded border border-slate-200 bg-slate-50"
            >
              {o.competencia} · {o.status}
            </span>
          ))
        )}
      </div>

      {orcamentoAtual && (
        <div className="bg-slate-50 border-b border-slate-200 px-4 py-3 grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiMini label="Previsto" value={formatBRL(totalGeral)} destaque />
          <KpiMini label="Realizado" value={formatBRL(totalRealizado)} />
          <KpiMini
            label="Saldo"
            value={formatBRL(totalGeral - totalRealizado)}
          />
          <KpiMini
            label="Aderência"
            value={
              totalGeral > 0
                ? `${((totalRealizado / totalGeral) * 100).toFixed(1)}%`
                : "—"
            }
          />
          <KpiMini
            label="Fixas"
            value={formatBRL(totaisPorSecao["DESPESA_FIXA"] ?? 0)}
          />
          <KpiMini
            label="Tributos"
            value={formatBRL(totaisPorSecao["TRIBUTO"] ?? 0)}
          />
          <KpiMini
            label="Sal. variáveis"
            value={formatBRL(totaisPorSecao["SALARIO_VARIAVEL"] ?? 0)}
          />
          <KpiMini
            label="Comissões"
            value={formatBRL(totaisPorSecao["COMISSAO"] ?? 0)}
          />
        </div>
      )}

      {/* Breakdown por bolso — para onde vai o dinheiro */}
      {orcamentoAtual && (
        <div className="bg-slate-50 border-b border-slate-200 px-4 pb-3 grid grid-cols-2 md:grid-cols-4 gap-3">
          <BolsoCard
            label="SPM operacional"
            siglaCor="bg-slate-100 text-slate-700"
            sigla="SPM"
            previsto={totaisPorBolso.SPM_OPERACIONAL?.previsto ?? 0}
            realizado={totaisPorBolso.SPM_OPERACIONAL?.realizado ?? 0}
            barraCor="bg-slate-700"
          />
          <BolsoCard
            label="Via FD"
            siglaCor="bg-amber-100 text-amber-800"
            sigla="FD"
            previsto={totaisPorBolso.FD_VIA_SPM?.previsto ?? 0}
            realizado={totaisPorBolso.FD_VIA_SPM?.realizado ?? 0}
            barraCor="bg-amber-500"
          />
          <BolsoCard
            label="Pessoal Hugo"
            siglaCor="bg-red-100 text-red-800"
            sigla="HUGO"
            previsto={totaisPorBolso.HUGO_PESSOAL?.previsto ?? 0}
            realizado={totaisPorBolso.HUGO_PESSOAL?.realizado ?? 0}
            barraCor="bg-red-500"
          />
          <BolsoCard
            label="Investimento Hugo"
            siglaCor="bg-violet-100 text-violet-800"
            sigla="INV"
            previsto={totaisPorBolso.INVESTIMENTO_HUGO?.previsto ?? 0}
            realizado={totaisPorBolso.INVESTIMENTO_HUGO?.realizado ?? 0}
            barraCor="bg-violet-500"
          />
        </div>
      )}

      {orcamentoAtual ? (
        <>
          <TabsSecoes active={tab} contagens={contagens} onChange={setTab} />
          <div className="bg-slate-50 px-4 py-2 text-xs text-slate-600 border-b border-slate-200">
            Total previsto nesta seção:{" "}
            <b className="text-slate-900 tabular-nums">
              {formatBRL(totalPrevisto)}
            </b>{" "}
            · {linhasDoTab.length} linha(s)
          </div>
          <TabelaLinhas
            linhas={linhasDoTab}
            categoriaPorId={categoriaPorId}
            projetoPorId={projetoPorId}
            onRowClick={(l) => setLinhaConciliacao(l)}
            empresaCodigoPorId={Object.fromEntries(empresas.map((e) => [e.id, e.codigo]))}
            empresaOrcamentoId={orcamentoAtual?.empresa_id}
            contratoRotuloPorId={contratoRotuloPorId}
            modo="fixas"
            realizadoPorLinhaId={realizadoPorLinhaId}
          />
        </>
      ) : (
        <div className="p-6 text-slate-500 text-sm">
          Sem orçamento para {competencia}. Faça upload acima.
        </div>
      )}

      <UploadXlsxDialog
        empresas={empresas}
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onSuccess={() => recarregar()}
      />

      <DrawerMultiConta
        linha={linhaConciliacao}
        onClose={() => setLinhaConciliacao(null)}
        onEditar={(l) => {
          setLinhaConciliacao(null);
          setLinhaEditando(l);
        }}
      />

      <LinhaEditorModal
        linha={linhaEditando}
        categoriaPorId={categoriaPorId}
        onClose={(atualizada) => {
          if (atualizada) {
            // Atualizacao local sem refetch completo.
            setLinhas((prev) =>
              prev.map((x) => (x.id === atualizada.id ? atualizada : x))
            );
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

function proximaCompetencia(c: string): string {
  const [y, m] = c.split("-").map(Number);
  const nextM = m === 12 ? 1 : m + 1;
  const nextY = m === 12 ? y + 1 : y;
  return `${nextY}-${String(nextM).padStart(2, "0")}`;
}

function BolsoCard({
  label,
  sigla,
  siglaCor,
  previsto,
  realizado,
  barraCor,
}: {
  label: string;
  sigla: string;
  siglaCor: string;
  previsto: number;
  realizado: number;
  barraCor: string;
}) {
  const pct = previsto > 0 ? Math.min(100, (realizado / previsto) * 100) : 0;
  const acima = previsto > 0 && realizado > previsto;
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-2.5">
      <div className="text-[10px] uppercase tracking-wide text-slate-500 font-semibold flex items-center justify-between">
        <span>Bolso · {label}</span>
        <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${siglaCor}`}>{sigla}</span>
      </div>
      <div className="flex justify-between items-baseline mt-1">
        <span className="text-xs tabular-nums text-slate-500">prev {formatBRL(previsto)}</span>
        <span className="text-sm font-bold tabular-nums text-slate-900">{formatBRL(realizado)}</span>
      </div>
      <div className="w-full bg-slate-100 rounded-full h-1 mt-1.5 overflow-hidden">
        <div className={`${barraCor} h-full rounded-full transition-all`} style={{ width: `${pct.toFixed(1)}%` }}></div>
      </div>
      {acima && (
        <div className="text-[9px] text-red-600 mt-0.5">
          ▲ {((realizado / previsto - 1) * 100).toFixed(1)}% acima do previsto
        </div>
      )}
    </div>
  );
}

function KpiMini({
  label,
  value,
  destaque = false,
}: {
  label: string;
  value: string;
  destaque?: boolean;
}) {
  return (
    <div
      className={
        destaque
          ? "bg-slate-900 text-white rounded px-3 py-2"
          : "bg-white border border-slate-200 rounded px-3 py-2"
      }
    >
      <div
        className={`text-[10px] uppercase tracking-wide ${
          destaque ? "text-slate-300" : "text-slate-500"
        }`}
      >
        {label}
      </div>
      <div
        className={`text-sm font-bold tabular-nums ${
          destaque ? "text-white" : "text-slate-900"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
