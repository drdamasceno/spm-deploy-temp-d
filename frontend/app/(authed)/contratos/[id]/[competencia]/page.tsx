"use client"
import { useEffect, useState, use } from "react"
import { fetchContratoCompetencia } from "@/lib/api/contratos-competencia"
import { EditorDadosContrato } from "@/components/contratos/editor-dados-contrato"
import type { ContratoDetalheOut, ContratoDadosExtras } from "@/types/v2"
import { formatBRL } from "@/lib/format"
import Link from "next/link"
import { toast } from "sonner"

const STATUS_STYLE: Record<string, string> = {
  PAGO: "bg-emerald-100 text-emerald-800",
  PARCIAL: "bg-blue-100 text-blue-800",
  PENDENTE: "bg-amber-100 text-amber-800",
}

export default function ContratoDetalhePage({ params }: {
  params: Promise<{ id: string; competencia: string }>
}) {
  const { id, competencia } = use(params)
  const [data, setData] = useState<ContratoDetalheOut | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<"pagamentos" | "dados">("pagamentos")

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchContratoCompetencia(id, competencia)
      .then(d => { if (!cancelled) setData(d) })
      .catch((e: unknown) => {
        if (!cancelled) toast.error("Falha: " + (e instanceof Error ? e.message : "erro"))
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [id, competencia])

  function onSavedExtras(novos: ContratoDadosExtras) {
    if (data) setData({ ...data, dados_extras: novos })
  }

  if (loading) return <div className="p-6 text-slate-500">Carregando…</div>
  if (!data) return <div className="p-6 text-slate-500">Contrato não encontrado.</div>

  return (
    <div className="p-5 space-y-4">
      <div className="flex items-center gap-2 text-xs text-slate-500">
        <Link href="/contratos" className="hover:underline">← Contratos</Link>
        <span>/</span>
        <span className="font-medium">{data.uf} - {data.cidade}</span>
        <span>/</span>
        <span>{formatCompetenciaCurta(data.competencia)}</span>
      </div>

      <div className="flex gap-0 border-b-2 border-slate-200 -mx-5 px-5">
        <button onClick={() => setTab("pagamentos")}
          className={tab === "pagamentos"
            ? "py-2.5 px-4 border-b-2 border-blue-500 -mb-0.5 text-blue-900 font-semibold text-sm"
            : "py-2.5 px-4 text-slate-500 text-sm hover:text-slate-700"}>
          Pagamentos
        </button>
        <button onClick={() => setTab("dados")}
          className={tab === "dados"
            ? "py-2.5 px-4 border-b-2 border-blue-500 -mb-0.5 text-blue-900 font-semibold text-sm"
            : "py-2.5 px-4 text-slate-500 text-sm hover:text-slate-700"}>
          Dados do contrato
        </button>
      </div>

      {tab === "pagamentos" && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-slate-900 text-white rounded px-3.5 py-2.5">
              <div className="text-[10px] uppercase text-slate-400 tracking-wide">Total</div>
              <div className="text-base font-bold mt-1 tabular-nums">{formatBRL(data.total)}</div>
            </div>
            <div className="bg-white border border-slate-200 rounded px-3.5 py-2.5">
              <div className="text-[10px] uppercase text-slate-500 tracking-wide">Total Pago</div>
              <div className="text-base font-bold mt-1 tabular-nums">{formatBRL(data.total_pago)}</div>
            </div>
            <div className="bg-white border border-slate-200 rounded px-3.5 py-2.5">
              <div className="text-[10px] uppercase text-slate-500 tracking-wide">Saldo</div>
              <div className="text-base font-bold mt-1 tabular-nums text-red-900">{formatBRL(data.saldo)}</div>
            </div>
            <div className="bg-white border border-slate-200 rounded px-3.5 py-2.5">
              <div className="text-[10px] uppercase text-slate-500 tracking-wide">Prestadores</div>
              <div className="text-base font-bold mt-1">{data.prestadores_count} · {data.registros_count} reg.</div>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-slate-100 border-b-2 border-slate-300">
                <tr>
                  <th className="px-2.5 py-2 text-left text-[10px] uppercase text-slate-600">Competência</th>
                  <th className="px-2.5 py-2 text-left text-[10px] uppercase text-slate-600">Prestador</th>
                  <th className="px-2.5 py-2 text-left text-[10px] uppercase text-slate-600">Local</th>
                  <th className="px-2.5 py-2 text-right text-[10px] uppercase text-slate-600">Total</th>
                  <th className="px-2.5 py-2 text-right text-[10px] uppercase text-slate-600">Pago</th>
                  <th className="px-2.5 py-2 text-right text-[10px] uppercase text-slate-600">Saldo</th>
                  <th className="px-2.5 py-2 text-center text-[10px] uppercase text-slate-600">Status</th>
                  <th className="px-2.5 py-2 text-left text-[10px] uppercase text-slate-600">Data pag.</th>
                </tr>
              </thead>
              <tbody className="tabular-nums">
                {data.linhas.map(l => (
                  <tr key={l.prestador_id + (l.local ?? "")} className="border-b border-slate-200">
                    <td className="px-2.5 py-2 text-slate-700">{formatCompetenciaCurta(l.competencia)}</td>
                    <td className="px-2.5 py-2 font-semibold text-slate-900">{l.prestador_nome}</td>
                    <td className="px-2.5 py-2 text-slate-600 text-[11px]">{l.local ?? "—"}</td>
                    <td className="px-2.5 py-2 text-right">{formatBRL(l.total)}</td>
                    <td className="px-2.5 py-2 text-right text-slate-500">{formatBRL(l.total_pago)}</td>
                    <td className="px-2.5 py-2 text-right font-semibold">{formatBRL(l.saldo)}</td>
                    <td className="px-2.5 py-2 text-center">
                      <span className={`inline-block text-[10px] font-semibold px-2 py-0.5 rounded-full ${STATUS_STYLE[l.status]}`}>
                        {l.status[0] + l.status.slice(1).toLowerCase()}
                      </span>
                    </td>
                    <td className="px-2.5 py-2 text-slate-600">{l.data_pagamento ? formatDataBR(l.data_pagamento) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {tab === "dados" && (
        <EditorDadosContrato contratoId={data.contrato_id} inicial={data.dados_extras} onSaved={onSavedExtras} />
      )}
    </div>
  )
}

function formatCompetenciaCurta(comp: string): string {
  const [y, m] = comp.split("-")
  return `${m}.${y.slice(2)}`
}

function formatDataBR(s: string): string {
  const [y, m, d] = s.split("-")
  return `${d}/${m}/${y.slice(2)}`
}
