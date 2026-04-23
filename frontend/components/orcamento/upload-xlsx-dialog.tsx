"use client";
import { useEffect, useState } from "react";
import { uploadOrcamento, listarOrcamentos } from "@/lib/api/orcamento";
import { toast } from "sonner";
import type { EmpresaOut, OrcamentoOut, ResultadoUploadOrcamento } from "@/types/v2";

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
  const [existente, setExistente] = useState<OrcamentoOut | null>(null);
  const [substituir, setSubstituir] = useState(false);

  // Detecta se já existe orçamento para (empresa, competência) assim que
  // usuário seleciona/muda. Mostra aviso + checkbox "Substituir" no form —
  // sem depender de pegar 409 no catch (era frágil porque depende do axios
  // preservar response.data.detail em forma específica).
  useEffect(() => {
    if (!open || !empresa || !competencia) {
      setExistente(null);
      return;
    }
    let cancelou = false;
    listarOrcamentos({ empresa_id: empresa, competencia })
      .then((orcs) => {
        if (cancelou) return;
        setExistente(orcs[0] ?? null);
      })
      .catch(() => {
        if (cancelou) return;
        setExistente(null);
      });
    return () => {
      cancelou = true;
    };
  }, [empresa, competencia, open]);

  if (!open) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!arquivo || !empresa) {
      toast.error("Preencha todos os campos");
      return;
    }
    if (existente && !substituir) {
      toast.error(
        "Já existe orçamento para essa competência. Marque 'Substituir' ou mude a competência."
      );
      return;
    }
    if (existente && existente.status === "FECHADO") {
      toast.error("Orçamento FECHADO não pode ser substituído.");
      return;
    }
    setSubmitting(true);
    try {
      const result = await uploadOrcamento(
        empresa,
        competencia,
        arquivo,
        substituir
      );
      toast.success(`${result.total_linhas_inseridas} linhas inseridas`);
      onSuccess(result);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error("Falha no upload: " + msg);
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

        {existente && (
          <div
            className={`rounded border p-3 text-xs ${
              existente.status === "FECHADO"
                ? "bg-red-50 border-red-300 text-red-900"
                : "bg-amber-50 border-amber-300 text-amber-900"
            }`}
          >
            <div className="font-semibold mb-1">
              ⚠ Já existe orçamento para {competencia} (status: {existente.status})
            </div>
            {existente.status === "FECHADO" ? (
              <div>
                Orçamento FECHADO não pode ser substituído via upload. Reabra na
                tela principal antes.
              </div>
            ) : (
              <label className="flex items-center gap-2 cursor-pointer mt-1">
                <input
                  type="checkbox"
                  checked={substituir}
                  onChange={(e) => setSubstituir(e.target.checked)}
                  className="w-4 h-4"
                />
                <span>
                  <b>Substituir</b> — as {"{"}linhas{"}"} do orçamento atual
                  serão DELETADAS antes do novo upload
                </span>
              </label>
            )}
          </div>
        )}

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
            disabled={
              submitting ||
              (existente !== null &&
                (existente.status === "FECHADO" || !substituir))
            }
            className="px-3 py-1 text-sm rounded bg-slate-900 text-white disabled:opacity-50"
          >
            {submitting ? "Enviando..." : "Upload"}
          </button>
        </div>
      </form>
    </div>
  );
}
