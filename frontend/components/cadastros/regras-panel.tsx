"use client";
import { useEffect, useState } from "react";
import { listarRegras, editarRegra, desativarRegra } from "@/lib/api/regra";
import type { RegraClassificacaoOut } from "@/types/v2";
import { toast } from "sonner";

export function RegrasPanel() {
  const [items, setItems] = useState<RegraClassificacaoOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [filtroAtiva, setFiltroAtiva] = useState<"todas" | "ativas" | "inativas">(
    "todas"
  );
  const [togglingId, setTogglingId] = useState<string | null>(null);

  async function recarregar() {
    setLoading(true);
    try {
      const params =
        filtroAtiva === "todas"
          ? {}
          : { ativa: filtroAtiva === "ativas" };
      const data = await listarRegras(params);
      setItems(data);
    } catch (e) {
      toast.error("Falha ao listar regras: " + (e instanceof Error ? e.message : "erro"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    recarregar();
  }, [filtroAtiva]);

  async function handleToggle(regra: RegraClassificacaoOut) {
    setTogglingId(regra.id);
    try {
      if (regra.ativa) {
        await desativarRegra(regra.id);
        toast.success("Regra desativada");
      } else {
        await editarRegra(regra.id, { ativa: true });
        toast.success("Regra ativada");
      }
      recarregar();
    } catch (e) {
      toast.error("Falha: " + (e instanceof Error ? e.message : "erro"));
    } finally {
      setTogglingId(null);
    }
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500 mb-3">
        Aprendidas automaticamente quando voce aprova uma conciliacao nao-REGRA. Use para desativar ou revisar matches que ficaram ruins.
      </p>
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">
          {items.length} regra(s)
        </h2>
        <div className="flex gap-1 text-xs">
          {(["todas", "ativas", "inativas"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFiltroAtiva(f)}
              className={`px-2 py-1 rounded border ${
                filtroAtiva === f
                  ? "bg-slate-900 text-white border-slate-900"
                  : "bg-white text-slate-700 border-slate-300 hover:bg-slate-50"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>
      {loading ? (
        <p className="text-sm text-slate-500">Carregando...</p>
      ) : (
        <div className="bg-white border border-slate-200 rounded-lg overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-100">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 uppercase">
                  Titular PIX padrao
                </th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-slate-600 uppercase">
                  Confianca base
                </th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-slate-600 uppercase">
                  Uso
                </th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 uppercase">
                  Ultima utilizacao
                </th>
                <th className="px-3 py-2 text-center text-xs font-semibold text-slate-600 uppercase">
                  Ativa
                </th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-slate-600 uppercase">
                  Acao
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((r) => (
                <tr key={r.id} className="border-t border-slate-100">
                  <td className="px-3 py-2 text-slate-900 font-medium">
                    {r.titular_pix_padrao}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-700 tabular-nums">
                    {r.confianca_base.toFixed(2)}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-700 tabular-nums">
                    {r.uso_count}
                  </td>
                  <td className="px-3 py-2 text-slate-600 text-xs">
                    {r.ultima_utilizacao
                      ? new Date(r.ultima_utilizacao).toLocaleString("pt-BR")
                      : "-"}
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-semibold uppercase ${
                        r.ativa
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {r.ativa ? "Sim" : "Nao"}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      disabled={togglingId === r.id}
                      onClick={() => handleToggle(r)}
                      className={`text-xs hover:underline disabled:opacity-50 ${
                        r.ativa ? "text-red-600" : "text-emerald-700"
                      }`}
                    >
                      {togglingId === r.id
                        ? "..."
                        : r.ativa
                        ? "Desativar"
                        : "Ativar"}
                    </button>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-3 py-6 text-center text-sm text-slate-500"
                  >
                    Nenhuma regra encontrada.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
