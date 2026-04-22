"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { uploadExtratoUnicred, uploadExtratoBradesco } from "@/lib/api/extratos";
import { listarContasBancarias, type ContaBancariaOut } from "@/lib/api/catalogos";
import { toast } from "sonner";
import type { UploadExtratoResponse } from "@/types/v2";

type TipoExtrato = "UNICRED" | "BRADESCO";

export function UploadExtratoDialog({
  tipo, open, onClose, onSuccess
}: {
  tipo: TipoExtrato; open: boolean; onClose: () => void;
  onSuccess: (r: UploadExtratoResponse) => void;
}) {
  const [contas, setContas] = useState<ContaBancariaOut[]>([]);
  const [contaId, setContaId] = useState("");
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open || tipo !== "UNICRED") return;
    listarContasBancarias().then(cs => {
      const unicred = cs.filter(c => c.banco.toUpperCase().includes("UNICRED") || c.banco === "544");
      setContas(unicred);
      setContaId(unicred[0]?.id ?? "");
    });
  }, [open, tipo]);

  if (!open) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!arquivo) { toast.error("Selecione um arquivo"); return; }
    if (tipo === "UNICRED" && !contaId) { toast.error("Selecione uma conta Unicred"); return; }
    setSubmitting(true);
    try {
      const result = tipo === "UNICRED"
        ? await uploadExtratoUnicred(contaId, arquivo)
        : await uploadExtratoBradesco(arquivo);
      toast.success(`${result.total_transacoes_inseridas} transacoes inseridas (${result.periodo_inicio} -> ${result.periodo_fim})`);
      onSuccess(result);
      onClose();
    } catch (err) {
      toast.error("Falha: " + (err instanceof Error ? err.message : "erro"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <form className="bg-white rounded-lg p-6 min-w-[400px] space-y-3" onClick={e => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2 className="text-base font-semibold text-slate-900">Upload extrato {tipo}</h2>
        {tipo === "UNICRED" && (
          <div>
            <label className="text-xs text-slate-600 block mb-1">Conta Unicred</label>
            {contas.length === 0 ? (
              <div className="border border-amber-300 bg-amber-50 rounded p-3 text-xs text-amber-900 space-y-2">
                <p>
                  Nenhuma conta Unicred cadastrada. Cadastre uma conta Unicred antes de fazer upload do extrato.
                </p>
                <Link
                  href="/cadastros?tab=contas"
                  className="inline-block px-2 py-1 text-xs rounded bg-amber-600 text-white hover:bg-amber-700"
                  onClick={onClose}
                >
                  Cadastrar conta
                </Link>
              </div>
            ) : (
              <select className="w-full border border-slate-300 rounded px-2 py-1 text-sm" value={contaId} onChange={e => setContaId(e.target.value)}>
                {contas.map(c => <option key={c.id} value={c.id}>{c.banco} | {c.agencia}/{c.conta} | {c.finalidade}</option>)}
              </select>
            )}
          </div>
        )}
        {tipo === "BRADESCO" && (
          <p className="text-xs text-slate-600">A conta e resolvida automaticamente via BANKID+ACCTID do arquivo OFX.</p>
        )}
        <div>
          <label className="text-xs text-slate-600 block mb-1">Arquivo {tipo === "UNICRED" ? "PDF" : "OFX"}</label>
          <input type="file" accept={tipo === "UNICRED" ? ".pdf,application/pdf" : ".ofx"} onChange={e => setArquivo(e.target.files?.[0] ?? null)} className="text-sm" />
        </div>
        <div className="flex gap-2 justify-end pt-2">
          <button type="button" onClick={onClose} className="px-3 py-1 text-sm rounded border border-slate-300">Cancelar</button>
          <button type="submit" disabled={submitting || !arquivo} className="px-3 py-1 text-sm rounded bg-slate-900 text-white disabled:opacity-50">
            {submitting ? "Enviando..." : "Upload"}
          </button>
        </div>
      </form>
    </div>
  );
}
