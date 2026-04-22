"use client";
import { useEffect, useState } from "react";
import {
  listarProjetos,
  criarProjeto,
  deletarProjeto,
  listarEmpresas,
} from "@/lib/api/catalogos";
import type { ProjetoOut, EmpresaOut } from "@/types/v2";
import { toast } from "sonner";

export function ProjetosPanel() {
  const [items, setItems] = useState<ProjetoOut[]>([]);
  const [empresas, setEmpresas] = useState<EmpresaOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [codigo, setCodigo] = useState("");
  const [descricao, setDescricao] = useState("");
  const [empresaId, setEmpresaId] = useState("");

  async function recarregar() {
    setLoading(true);
    try {
      const [p, e] = await Promise.all([listarProjetos(), listarEmpresas()]);
      setItems(p);
      setEmpresas(e);
      setEmpresaId((prev) => (prev ? prev : e[0]?.id ?? ""));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    recarregar();
  }, []);

  async function handleCriar(ev: React.FormEvent) {
    ev.preventDefault();
    if (!codigo || !empresaId) {
      toast.error("Preencha codigo e empresa");
      return;
    }
    try {
      await criarProjeto({
        codigo,
        descricao: descricao || undefined,
        empresa_id: empresaId,
      });
      toast.success("Projeto criado");
      setCodigo("");
      setDescricao("");
      setMostrarForm(false);
      recarregar();
    } catch (e) {
      toast.error("Falha: " + (e instanceof Error ? e.message : "erro"));
    }
  }

  async function handleDeletar(id: string) {
    if (!confirm("Deletar este projeto?")) return;
    try {
      await deletarProjeto(id);
      toast.success("Projeto deletado");
      recarregar();
    } catch (e) {
      toast.error("Falha: " + (e instanceof Error ? e.message : "erro"));
    }
  }

  const empresaCodigoById = new Map(empresas.map((e) => [e.id, e.codigo]));

  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500 mb-3">
        Centros de custo que o orcamento usa para classificar despesas por area (ex: AD-ADMINISTRACAO GERAL-SPM, MG-UNAI).
      </p>
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">
          {items.length} projeto(s)
        </h2>
        <button
          onClick={() => setMostrarForm(!mostrarForm)}
          className="text-xs px-3 py-1 rounded bg-slate-900 text-white"
        >
          {mostrarForm ? "Cancelar" : "+ Novo projeto"}
        </button>
      </div>
      {mostrarForm && (
        <form
          onSubmit={handleCriar}
          className="bg-white border border-slate-200 rounded-lg p-3 space-y-2 flex flex-wrap gap-2 items-end"
        >
          <div className="flex-1 min-w-[200px]">
            <label className="text-[10px] text-slate-500 uppercase block">
              Codigo
            </label>
            <input
              value={codigo}
              onChange={(e) => setCodigo(e.target.value)}
              placeholder="AD-GERAL-SPM"
              className="w-full border border-slate-300 rounded px-2 py-1 text-sm"
            />
          </div>
          <div className="flex-1 min-w-[200px]">
            <label className="text-[10px] text-slate-500 uppercase block">
              Descricao
            </label>
            <input
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
              className="w-full border border-slate-300 rounded px-2 py-1 text-sm"
            />
          </div>
          <div className="flex-1 min-w-[150px]">
            <label className="text-[10px] text-slate-500 uppercase block">
              Empresa
            </label>
            <select
              value={empresaId}
              onChange={(e) => setEmpresaId(e.target.value)}
              className="w-full border border-slate-300 rounded px-2 py-1 text-sm"
            >
              {empresas.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.codigo}
                </option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            className="px-3 py-1 text-sm rounded bg-emerald-600 text-white"
          >
            Criar
          </button>
        </form>
      )}
      {loading ? (
        <p className="text-sm text-slate-500">Carregando...</p>
      ) : (
        <div className="bg-white border border-slate-200 rounded-lg overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-100">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 uppercase">
                  Codigo
                </th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 uppercase">
                  Descricao
                </th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 uppercase">
                  Empresa
                </th>
                <th className="px-3 py-2 text-center text-xs font-semibold text-slate-600 uppercase">
                  Ativo
                </th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-slate-600 uppercase">
                  Acao
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.id} className="border-t border-slate-100">
                  <td className="px-3 py-2 text-slate-900 font-medium">
                    {p.codigo}
                  </td>
                  <td className="px-3 py-2 text-slate-700">
                    {p.descricao ?? "-"}
                  </td>
                  <td className="px-3 py-2 text-slate-700">
                    {empresaCodigoById.get(p.empresa_id) ?? (
                      <span
                        className="text-slate-500 text-xs truncate inline-block max-w-[120px]"
                        title={p.empresa_id}
                      >
                        {p.empresa_id.slice(0, 8)}...
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-semibold uppercase ${
                        p.ativo
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {p.ativo ? "Sim" : "Nao"}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      onClick={() => handleDeletar(p.id)}
                      className="text-xs text-red-600 hover:underline"
                    >
                      Deletar
                    </button>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td
                    colSpan={5}
                    className="px-3 py-6 text-center text-sm text-slate-500"
                  >
                    Nenhum projeto cadastrado.
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
