"use client";
import type { AdiantamentoOut } from "@/types/v2";
import { formatBRL } from "@/lib/format";

export function ListaTabela({
  adiantamentos, onCompensar
}: { adiantamentos: AdiantamentoOut[]; onCompensar: (id: string) => void }) {
  if (!adiantamentos.length) {
    return <div className="p-6 text-slate-500 text-sm bg-white">Nenhum adiantamento registrado.</div>;
  }
  return (
    <div className="bg-white border border-slate-200 rounded-lg overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-slate-100">
          <tr>
            <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 uppercase">Prestador</th>
            <th className="px-3 py-2 text-right text-xs font-semibold text-slate-600 uppercase">Bruto</th>
            <th className="px-3 py-2 text-right text-xs font-semibold text-slate-600 uppercase">Desconto</th>
            <th className="px-3 py-2 text-right text-xs font-semibold text-slate-600 uppercase">Líquido</th>
            <th className="px-3 py-2 text-right text-xs font-semibold text-slate-600 uppercase">Receita financ.</th>
            <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 uppercase">Data Pagamento</th>
            <th className="px-3 py-2 text-center text-xs font-semibold text-slate-600 uppercase">Status</th>
            <th className="px-3 py-2 text-right text-xs font-semibold text-slate-600 uppercase">Ação</th>
          </tr>
        </thead>
        <tbody>
          {adiantamentos.map(a => <Row key={a.id} a={a} onCompensar={() => onCompensar(a.id)} />)}
        </tbody>
      </table>
    </div>
  );
}

function Row({ a, onCompensar }: { a: AdiantamentoOut; onCompensar: () => void }) {
  let badge = "bg-slate-100 text-slate-700";
  if (a.status === "ABERTO") badge = "bg-amber-100 text-amber-900";
  else if (a.status === "COMPENSADO_TOTAL") badge = "bg-emerald-100 text-emerald-900";
  else if (a.status === "COMPENSADO_PARCIAL") badge = "bg-blue-100 text-blue-900";
  else if (a.status === "BAIXADO_MANUAL") badge = "bg-red-100 text-red-900";

  return (
    <tr className="border-t border-slate-100">
      <td className="px-3 py-2 text-slate-900 text-xs truncate max-w-[200px]" title={a.prestador_id}>{a.prestador_id.slice(0, 8)}...</td>
      <td className="px-3 py-2 text-right tabular-nums">{formatBRL(a.valor_bruto_solicitado)}</td>
      <td className="px-3 py-2 text-right tabular-nums text-slate-600">{a.percentual_desconto}%</td>
      <td className="px-3 py-2 text-right tabular-nums">{formatBRL(a.valor_liquido_pago)}</td>
      <td className="px-3 py-2 text-right tabular-nums text-emerald-700">{formatBRL(a.receita_financeira)}</td>
      <td className="px-3 py-2 text-xs text-slate-600">{a.data_pagamento}</td>
      <td className="px-3 py-2 text-center">
        <span className={`text-[10px] px-2 py-0.5 rounded font-semibold uppercase ${badge}`}>{a.status}</span>
      </td>
      <td className="px-3 py-2 text-right">
        {a.status === "ABERTO" && (
          <button onClick={onCompensar} className="text-xs bg-slate-900 text-white px-2 py-1 rounded hover:bg-slate-700">Compensar</button>
        )}
      </td>
    </tr>
  );
}
