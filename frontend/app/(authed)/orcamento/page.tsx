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
} from "@/lib/api/orcamento";
import { TabsSecoes } from "@/components/orcamento/tabs-secoes";
import { TabelaLinhas } from "@/components/orcamento/tabela-linhas";
import { UploadXlsxDialog } from "@/components/orcamento/upload-xlsx-dialog";
import { LinhaEditorModal } from "@/components/orcamento/linha-editor-modal";
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

export default function OrcamentoPage() {
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
  const [tab, setTab] = useState<NaturezaOrcamento>("DESPESA_FIXA");
  const [loading, setLoading] = useState(true);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [linhaEditando, setLinhaEditando] =
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
        const ls = await listarLinhasDoOrcamento(atual.id);
        setLinhas(ls);
      } else {
        setLinhas([]);
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
    const m: Record<NaturezaOrcamento, number> = {
      DESPESA_FIXA: 0,
      TRIBUTO: 0,
      SALARIO_VARIAVEL: 0,
      COMISSAO: 0,
      VALOR_VARIAVEL: 0,
      DESPESA_PROFISSIONAIS: 0,
      FATURAMENTO: 0,
    };
    linhas.forEach((l) => {
      m[l.natureza] = (m[l.natureza] ?? 0) + 1;
    });
    return m;
  }, [linhas]);

  const linhasDoTab = linhas.filter((l) => l.natureza === tab);

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

  const totalGeral = useMemo(
    () => linhas.reduce((acc, l) => acc + l.valor_previsto, 0),
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
          Orçamento · {competencia}
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
          <KpiMini label="Total orçado" value={formatBRL(totalGeral)} destaque />
          <KpiMini label="Linhas" value={`${linhas.length}`} />
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
          <KpiMini
            label="Var. outros"
            value={formatBRL(totaisPorSecao["VALOR_VARIAVEL"] ?? 0)}
          />
          <KpiMini
            label="Profissionais PP"
            value={formatBRL(totaisPorSecao["DESPESA_PROFISSIONAIS"] ?? 0)}
          />
          <KpiMini
            label="Faturamento"
            value={formatBRL(totaisPorSecao["FATURAMENTO"] ?? 0)}
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
            onRowClick={(l) => setLinhaEditando(l)}
            empresaCodigoPorId={Object.fromEntries(empresas.map((e) => [e.id, e.codigo]))}
            empresaOrcamentoId={orcamentoAtual?.empresa_id}
            contratoRotuloPorId={contratoRotuloPorId}
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
