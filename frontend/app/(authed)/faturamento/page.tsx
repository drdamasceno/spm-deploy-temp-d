"use client";
import { useEffect, useState, useMemo, useCallback } from "react";
import { useFilters } from "@/lib/filters-context";
import { listarEmpresas, listarCategorias, listarProjetos } from "@/lib/api/catalogos";
import { apiClient } from "@/lib/api";
import {
  listarOrcamentos,
  listarLinhasDoOrcamento,
} from "@/lib/api/orcamento";
import { getRealizadoPorLinha, type RealizadoPorLinha } from "@/lib/api/margem";
import { TabelaLinhas } from "@/components/orcamento/tabela-linhas";
import { LinhaEditorModal } from "@/components/orcamento/linha-editor-modal";
import { DrawerMultiConta } from "@/components/conciliacao/drawer-multi-conta";
import type {
  EmpresaOut,
  CategoriaOut,
  ProjetoOut,
  OrcamentoOut,
  OrcamentoLinhaOut,
} from "@/types/v2";
import { formatBRL } from "@/lib/format";
import { toast } from "sonner";

// Aba Faturamento — receita por contrato (natureza=FATURAMENTO).
// Diferente de Despesas Fixas: cores invertidas (saldo positivo = vermelho =
// "A Receber"), sem coluna Bolso (irrelevante em receita), sem tabs internas.
export default function FaturamentoPage() {
  const { competencia } = useFilters();
  const [empresas, setEmpresas] = useState<EmpresaOut[]>([]);
  const [orcamentoAtual, setOrcamentoAtual] = useState<OrcamentoOut | null>(null);
  const [linhas, setLinhas] = useState<OrcamentoLinhaOut[]>([]);
  const [categorias, setCategorias] = useState<CategoriaOut[]>([]);
  const [projetos, setProjetos] = useState<ProjetoOut[]>([]);
  const [contratoRotuloPorId, setContratoRotuloPorId] = useState<Record<string, string>>({});
  const [realizadoPorLinhaId, setRealizadoPorLinhaId] = useState<Record<string, RealizadoPorLinha>>({});
  const [loading, setLoading] = useState(true);
  const [linhaEditando, setLinhaEditando] = useState<OrcamentoLinhaOut | null>(null);
  const [linhaConciliacao, setLinhaConciliacao] = useState<OrcamentoLinhaOut | null>(null);

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
        const [ls, realizadosArr] = await Promise.all([
          listarLinhasDoOrcamento(atual.id, "FATURAMENTO"),
          getRealizadoPorLinha(atual.id).catch(() => []),
        ]);
        setLinhas(ls);
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
  const totalRecebido = useMemo(
    () => linhas.reduce((acc, l) => acc + (realizadoPorLinhaId[l.id]?.pago ?? 0), 0),
    [linhas, realizadoPorLinhaId]
  );
  const aReceber = totalPrevisto - totalRecebido;
  const aderencia = totalPrevisto > 0 ? (totalRecebido / totalPrevisto) * 100 : 0;

  if (loading) return <div className="p-6 text-slate-500">Carregando...</div>;

  return (
    <div className="flex flex-col">
      <div className="bg-white border-b border-slate-200 px-4 py-3 flex items-center justify-between">
        <h1 className="text-base font-semibold text-slate-900">Faturamento · {competencia}</h1>
      </div>

      {orcamentoAtual && (
        <div className="bg-slate-50 border-b border-slate-200 px-4 py-3 grid grid-cols-2 md:grid-cols-4 gap-3">
          <KpiMini label="Receita Prevista" value={formatBRL(totalPrevisto)} destaque />
          <KpiMini label="Recebido" value={formatBRL(totalRecebido)} />
          <KpiMini
            label="A Receber"
            value={formatBRL(aReceber)}
            corValor={aReceber > 0.01 ? "text-red-700" : "text-emerald-700"}
          />
          <KpiMini label="Aderência" value={`${aderencia.toFixed(1)}%`} />
        </div>
      )}

      {orcamentoAtual ? (
        <>
          <div className="bg-slate-50 px-4 py-2 text-xs text-slate-600 border-b border-slate-200">
            Total previsto: <b className="text-slate-900 tabular-nums">{formatBRL(totalPrevisto)}</b>
            {" · "}
            Total recebido: <b className="text-slate-900 tabular-nums">{formatBRL(totalRecebido)}</b>
            {" · "}
            {linhas.length} contrato(s) com receita prevista
          </div>
          <TabelaLinhas
            linhas={linhas}
            categoriaPorId={categoriaPorId}
            projetoPorId={projetoPorId}
            onRowClick={(l) => setLinhaConciliacao(l)}
            empresaCodigoPorId={Object.fromEntries(empresas.map((e) => [e.id, e.codigo]))}
            empresaOrcamentoId={orcamentoAtual?.empresa_id}
            contratoRotuloPorId={contratoRotuloPorId}
            modo="faturamento"
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
