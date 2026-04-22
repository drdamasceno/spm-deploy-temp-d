"use client";
import { useEffect, useState } from "react";
import { compensarAdiantamento, listarRegistrosDisponiveis, type RegistroPPDisponivel } from "@/lib/api/adiantamento";
import { formatBRL } from "@/lib/format";
import { toast } from "sonner";

export function CompensarDialog({
  adiantamentoId, open, onClose, onSuccess
}: {
  adiantamentoId: string | null; open: boolean; onClose: () => void; onSuccess: () => void;
}) {
  const [registros, setRegistros] = useState<RegistroPPDisponivel[]>([]);
  const [escolhido, setEscolhido] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!open || !adiantamentoId) return;
    setLoading(true);
    listarRegistrosDisponiveis(adiantamentoId)
      .then(r => { setRegistros(r); setEscolhido(r[0]?.id ?? ""); })
      .catch(e => toast.error("Falha: " + (e instanceof Error ? e.message : "erro")))
      .finally(() => setLoading(false));
  }, [open, adiantamentoId]);

  if (!open || !adiantamentoId) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!escolhido) { toast.error("Selecione um registro PP"); return; }
    setSubmitting(true);
    try {
      await compensarAdiantamento(adiantamentoId!, escolhido);
      toast.success("Compensado com sucesso");
      onSuccess();
      onClose();
    } catch (err) {
      toast.error("Falha: " + (err instanceof Error ? err.message : "erro"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <form className="bg-white rounded-lg p-6 min-w-[500px] space-y-3" onClick={e => e.stopPropagation()} onSubmit={handleSubmit}>
        <h2 className="text-base font-semibold text-slate-900">Compensar adiantamento</h2>
        {loading ? (
          <p className="text-sm text-slate-500">Carregando registros PP...</p>
        ) : registros.length === 0 ? (
          <p className="text-sm text-slate-500">Nenhum registro PP elegível encontrado para este prestador.</p>
        ) : (
          <div>
            <label className="text-xs text-slate-600 block mb-1">Registro PP para compensar:</label>
            <select className="w-full border border-slate-300 rounded px-2 py-1 text-sm" value={escolhido} onChange={e => setEscolhido(e.target.value)}>
              {registros.map(r => (
                <option key={r.id} value={r.id}>
                  {r.contrato?.nome ?? "—"} · {r.mes_competencia} · saldo {formatBRL(r.saldo_pp)}
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="flex gap-2 justify-end pt-2">
          <button type="button" onClick={onClose} className="px-3 py-1 text-sm rounded border border-slate-300">Cancelar</button>
          <button type="submit" disabled={submitting || !escolhido} className="px-3 py-1 text-sm rounded bg-slate-900 text-white disabled:opacity-50">
            {submitting ? "Confirmando..." : "Confirmar compensação"}
          </button>
        </div>
      </form>
    </div>
  );
}
