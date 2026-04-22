"use client";
import { useEffect, useState } from "react";
import type { OrcamentoLinhaOut, CategoriaOut, ProjetoOut } from "@/types/v2";
import {
  editarOrcamentoLinha,
  deletarOrcamentoLinha,
} from "@/lib/api/orcamento";
import { toast } from "sonner";

interface Props {
  linha: OrcamentoLinhaOut | null;
  categorias: CategoriaOut[];
  projetos: ProjetoOut[];
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function EditarLinhaDialog({
  linha,
  categorias,
  projetos,
  open,
  onClose,
  onSuccess,
}: Props) {
  const [titular, setTitular] = useState("");
  const [cpfCnpj, setCpfCnpj] = useState("");
  const [categoriaId, setCategoriaId] = useState<string>("");
  const [projetoId, setProjetoId] = useState<string>("");
  const [valor, setValor] = useState("");
  const [data, setData] = useState("");
  const [obs, setObs] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!linha) return;
    setTitular(linha.titular_razao_social);
    setCpfCnpj(linha.titular_cpf_cnpj ?? "");
    setCategoriaId(linha.categoria_id ?? "");
    setProjetoId(linha.projeto_id ?? "");
    setValor(String(linha.valor_previsto));
    setData(linha.data_previsao ?? "");
    setObs(linha.observacao ?? "");
  }, [linha]);

  if (!open || !linha) return null;

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!linha) return;
    setSubmitting(true);
    try {
      const valorNum = parseFloat(valor.replace(",", "."));
      if (!Number.isFinite(valorNum)) {
        toast.error("Valor previsto invalido");
        setSubmitting(false);
        return;
      }
      await editarOrcamentoLinha(linha.id, {
        titular_razao_social: titular,
        titular_cpf_cnpj: cpfCnpj || null,
        categoria_id: categoriaId || null,
        projeto_id: projetoId || null,
        valor_previsto: valorNum,
        data_previsao: data || null,
        observacao: obs || null,
      });
      toast.success("Linha atualizada");
      onSuccess();
      onClose();
    } catch (err) {
      toast.error("Falha: " + (err instanceof Error ? err.message : "erro"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete() {
    if (!linha) return;
    if (!confirm(`Deletar a linha "${linha.titular_razao_social}"?`)) return;
    setSubmitting(true);
    try {
      await deletarOrcamentoLinha(linha.id);
      toast.success("Linha deletada");
      onSuccess();
      onClose();
    } catch (err) {
      toast.error("Falha: " + (err instanceof Error ? err.message : "erro"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <form
        className="bg-white rounded-lg p-6 min-w-[500px] max-w-[600px] space-y-3"
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSave}
      >
        <h2 className="text-base font-semibold text-slate-900">
          Editar linha do orçamento
        </h2>

        <div>
          <label className="text-xs text-slate-600 block mb-1">
            Razão social
          </label>
          <input
            value={titular}
            onChange={(e) => setTitular(e.target.value)}
            className="w-full border border-slate-300 rounded px-2 py-1 text-sm"
          />
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-slate-600 block mb-1">
              CPF/CNPJ
            </label>
            <input
              value={cpfCnpj}
              onChange={(e) => setCpfCnpj(e.target.value)}
              className="w-full border border-slate-300 rounded px-2 py-1 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-slate-600 block mb-1">
              Valor previsto (R$)
            </label>
            <input
              type="number"
              step="0.01"
              value={valor}
              onChange={(e) => setValor(e.target.value)}
              className="w-full border border-slate-300 rounded px-2 py-1 text-sm"
            />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-slate-600 block mb-1">
              Categoria
            </label>
            <select
              value={categoriaId}
              onChange={(e) => setCategoriaId(e.target.value)}
              className="w-full border border-slate-300 rounded px-2 py-1 text-sm"
            >
              <option value="">— Nenhuma —</option>
              {categorias.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nome}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-600 block mb-1">Projeto</label>
            <select
              value={projetoId}
              onChange={(e) => setProjetoId(e.target.value)}
              className="w-full border border-slate-300 rounded px-2 py-1 text-sm"
            >
              <option value="">— Nenhum —</option>
              {projetos.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.codigo}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <label className="text-xs text-slate-600 block mb-1">
            Data previsão
          </label>
          <input
            type="date"
            value={data}
            onChange={(e) => setData(e.target.value)}
            className="w-full border border-slate-300 rounded px-2 py-1 text-sm"
          />
        </div>
        <div>
          <label className="text-xs text-slate-600 block mb-1">
            Observação
          </label>
          <textarea
            value={obs}
            onChange={(e) => setObs(e.target.value)}
            rows={2}
            className="w-full border border-slate-300 rounded px-2 py-1 text-sm"
          />
        </div>

        <div className="flex gap-2 justify-between pt-2">
          <button
            type="button"
            onClick={handleDelete}
            disabled={submitting}
            className="text-xs px-3 py-1 rounded border border-red-300 text-red-700 hover:bg-red-50 disabled:opacity-50"
          >
            Deletar linha
          </button>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1 text-sm rounded border border-slate-300"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-3 py-1 text-sm rounded bg-slate-900 text-white disabled:opacity-50"
            >
              {submitting ? "Salvando..." : "Salvar"}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
