"use client";
import { useEffect, useState } from "react";
import { uploadOrcamento } from "@/lib/api/orcamento";
import { toast } from "sonner";
import type { EmpresaOut, ResultadoUploadOrcamento } from "@/types/v2";

export function UploadXlsxDialog({
  empresas,
  open,
  onClose,
  onSuccess,
}: {
  empresas: EmpresaOut[];
  open: boolean;
  onClose: () => void;
  onSuccess: (r: ResultadoUploadOrcamento) => void;
}) {
  const [empresa, setEmpresa] = useState<string>(empresas[0]?.id ?? "");

  // Sincroniza quando empresas chega depois do mount (caso page ainda estivesse
  // carregando quando o dialog for aberto pela primeira vez).
  useEffect(() => {
    if (!empresa && empresas.length > 0) {
      setEmpresa(empresas[0].id);
    }
  }, [empresas, empresa]);
  const [competencia, setCompetencia] = useState<string>(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  });
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!open) return null;

  async function handleSubmit(e: React.FormEvent, force: boolean = false) {
    e.preventDefault();
    if (!arquivo || !empresa) {
      toast.error("Preencha todos os campos");
      return;
    }
    setSubmitting(true);
    try {
      const result = await uploadOrcamento(empresa, competencia, arquivo, force);
      toast.success(`${result.total_linhas_inseridas} linhas inseridas`);
      onSuccess(result);
      onClose();
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number; data?: { detail?: { exists?: boolean; status?: string } } } };
      const status = axiosErr?.response?.status;
      const detail = axiosErr?.response?.data?.detail;
      if (status === 409 && detail?.exists && !force) {
        if (detail.status === "FECHADO") {
          toast.error(
            "Já existe um orçamento FECHADO para essa competência. Não pode ser substituído."
          );
        } else if (
          confirm(
            `Já existe orçamento para ${competencia}. Substituir? (linhas atuais serão DELETADAS)`
          )
        ) {
          // re-chama com force=true
          return handleSubmit(e, true);
        }
      } else {
        const msg = err instanceof Error ? err.message : String(err);
        toast.error("Falha no upload: " + msg);
      }
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
        className="bg-white rounded-lg p-6 min-w-[400px] space-y-3"
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
      >
        <h2 className="text-base font-semibold text-slate-900">
          Upload de Orçamento
        </h2>
        <div>
          <label className="text-xs text-slate-600 block mb-1">Empresa</label>
          <select
            className="w-full border border-slate-300 rounded px-2 py-1 text-sm"
            value={empresa}
            onChange={(e) => setEmpresa(e.target.value)}
          >
            {empresas.map((emp) => (
              <option key={emp.id} value={emp.id}>
                {emp.codigo} — {emp.razao_social}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-slate-600 block mb-1">Competência</label>
          <input
            type="month"
            className="w-full border border-slate-300 rounded px-2 py-1 text-sm"
            value={competencia}
            onChange={(e) => setCompetencia(e.target.value)}
          />
        </div>
        <div>
          <label className="text-xs text-slate-600 block mb-1">Arquivo XLSX</label>
          <input
            type="file"
            accept=".xlsx"
            onChange={(e) => setArquivo(e.target.files?.[0] ?? null)}
            className="text-sm"
          />
        </div>
        <div className="flex gap-2 justify-end pt-2">
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
            {submitting ? "Enviando..." : "Upload"}
          </button>
        </div>
      </form>
    </div>
  );
}
