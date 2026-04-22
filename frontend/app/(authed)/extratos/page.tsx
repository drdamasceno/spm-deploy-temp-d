"use client";
import { useState } from "react";
import { UploadExtratoDialog } from "@/components/extrato/upload-dialog";
import type { UploadExtratoResponse } from "@/types/v2";

export default function ExtratosPage() {
  const [dialogAberto, setDialogAberto] = useState<"UNICRED" | "BRADESCO" | null>(null);
  const [uploadsRecentes, setUploadsRecentes] = useState<UploadExtratoResponse[]>([]);

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-900">Extratos</h1>
        <div className="flex gap-2">
          <button onClick={() => setDialogAberto("UNICRED")} className="px-3 py-2 text-sm rounded bg-blue-600 text-white hover:bg-blue-700">
            Unicred PDF
          </button>
          <button onClick={() => setDialogAberto("BRADESCO")} className="px-3 py-2 text-sm rounded bg-red-600 text-white hover:bg-red-700">
            Bradesco OFX
          </button>
        </div>
      </div>

      {uploadsRecentes.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-2">
          <h2 className="text-xs font-semibold uppercase text-slate-600 tracking-wide">Uploads nesta sessao</h2>
          {uploadsRecentes.map((r, i) => (
            <div key={i} className="text-sm text-slate-700 flex justify-between">
              <span>{r.origem_banco} | {r.periodo_inicio} -&gt; {r.periodo_fim}</span>
              <span className="tabular-nums text-slate-900 font-semibold">
                {r.total_transacoes_inseridas} transacoes
              </span>
            </div>
          ))}
        </div>
      )}

      <div className="bg-white border border-slate-200 rounded-lg p-4 text-sm text-slate-600">
        <p className="mb-1"><b>Unicred PDF:</b> exportar &quot;EXTRATO DE CONTA CORRENTE PARA SIMPLES CONFERENCIA&quot; direto da plataforma Unicred, periodo completo.</p>
        <p><b>Bradesco OFX:</b> exportar OFX do iBanking em qualquer conta (REMESSAS, AVISTA, TRIBUTOS) — a conta e resolvida automaticamente via BANKID+ACCTID.</p>
      </div>

      <UploadExtratoDialog
        tipo={dialogAberto ?? "UNICRED"}
        open={dialogAberto !== null}
        onClose={() => setDialogAberto(null)}
        onSuccess={(r) => setUploadsRecentes(prev => [...prev, r])}
      />
    </div>
  );
}
