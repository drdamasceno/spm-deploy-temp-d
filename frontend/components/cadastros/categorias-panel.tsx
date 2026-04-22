"use client";
import { useEffect, useState } from "react";
import { listarCategorias } from "@/lib/api/catalogos";
import type { CategoriaOut } from "@/types/v2";

export function CategoriasPanel() {
  const [items, setItems] = useState<CategoriaOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      setErro(null);
      try {
        const data = await listarCategorias();
        setItems(data);
      } catch (e) {
        setErro(e instanceof Error ? e.message : "erro desconhecido");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500 mb-3">
        Naturezas de despesa do sistema (Energia, Aluguel, Software, etc.). Read-only — categorias vem dos seeds e sao estendidas via SQL.
      </p>
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">
          {items.length} categoria(s)
        </h2>
        <span className="text-[10px] uppercase tracking-wide text-slate-500">
          Somente leitura (seed)
        </span>
      </div>
      {loading ? (
        <p className="text-sm text-slate-500">Carregando...</p>
      ) : erro ? (
        <p className="text-sm text-red-600">Erro: {erro}</p>
      ) : (
        <div className="bg-white border border-slate-200 rounded-lg overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-100">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 uppercase">
                  Nome
                </th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 uppercase">
                  Descricao
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id} className="border-t border-slate-100">
                  <td className="px-3 py-2 text-slate-900 font-medium">
                    {c.nome}
                  </td>
                  <td className="px-3 py-2 text-slate-700">
                    {c.descricao ?? "-"}
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td
                    colSpan={2}
                    className="px-3 py-6 text-center text-sm text-slate-500"
                  >
                    Nenhuma categoria encontrada.
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
