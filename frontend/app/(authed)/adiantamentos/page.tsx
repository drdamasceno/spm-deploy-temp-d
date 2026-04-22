"use client";
import { useEffect, useState } from "react";
import { listarAdiantamentos } from "@/lib/api/adiantamento";
import { ListaTabela } from "@/components/adiantamento/lista-tabela";
import { CompensarDialog } from "@/components/adiantamento/compensar-dialog";
import type { AdiantamentoOut } from "@/types/v2";
import { toast } from "sonner";

export default function AdiantamentosPage() {
  const [items, setItems] = useState<AdiantamentoOut[]>([]);
  const [filtro, setFiltro] = useState<AdiantamentoOut["status"] | "TODOS">("TODOS");
  const [loading, setLoading] = useState(true);
  const [dialogId, setDialogId] = useState<string | null>(null);

  async function recarregar() {
    setLoading(true);
    try {
      const r = await listarAdiantamentos(
        filtro === "TODOS" ? {} : { status_filtro: filtro }
      );
      setItems(r);
    } catch (e) {
      toast.error("Falha: " + (e instanceof Error ? e.message : "erro"));
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { recarregar(); }, [filtro]);

  return (
    <div className="p-6 space-y-3">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-900">Adiantamentos</h1>
        <div className="flex gap-2 items-center text-xs">
          <span className="text-slate-500">Filtro status:</span>
          <select className="border border-slate-300 rounded px-2 py-1" value={filtro} onChange={e => setFiltro(e.target.value as AdiantamentoOut["status"] | "TODOS")}>
            <option value="TODOS">Todos</option>
            <option value="ABERTO">Aberto</option>
            <option value="COMPENSADO_PARCIAL">Compensado parcial</option>
            <option value="COMPENSADO_TOTAL">Compensado total</option>
            <option value="BAIXADO_MANUAL">Baixado manual</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="p-6 text-slate-500 text-sm">Carregando...</div>
      ) : (
        <ListaTabela adiantamentos={items} onCompensar={(id) => setDialogId(id)} />
      )}

      <CompensarDialog
        adiantamentoId={dialogId}
        open={dialogId !== null}
        onClose={() => setDialogId(null)}
        onSuccess={recarregar}
      />
    </div>
  );
}
