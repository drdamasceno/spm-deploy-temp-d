"use client"

import { useEffect, useState } from "react"
import { toast } from "sonner"
import {
  fetchIntragrupoPendentes,
  conciliarIntragrupoLote,
  type TxIntragrupoPendente,
  type ConciliacaoLoteResult,
} from "@/lib/api/conciliacao_intragrupo"
import { formatBRL } from "@/lib/format"

export default function IntragrupoPage() {
  const [pendentes, setPendentes] = useState<TxIntragrupoPendente[]>([])
  const [loading, setLoading] = useState(true)
  const [executandoId, setExecutandoId] = useState<string | null>(null)
  const [resultados, setResultados] = useState<Record<string, ConciliacaoLoteResult>>({})

  useEffect(() => {
    recarregar()
  }, [])

  async function recarregar() {
    setLoading(true)
    try {
      const data = await fetchIntragrupoPendentes()
      setPendentes(data)
    } catch (e) {
      toast.error("Falha ao carregar: " + (e instanceof Error ? e.message : "erro"))
    } finally {
      setLoading(false)
    }
  }

  async function handleConciliar(tx: TxIntragrupoPendente) {
    if (!confirm(`Conciliar em lote o PIX de ${formatBRL(Math.abs(tx.valor))} para "${tx.titular_pix ?? "?"}"?`)) {
      return
    }
    setExecutandoId(tx.id)
    try {
      const res = await conciliarIntragrupoLote(tx.id)
      setResultados((prev) => ({ ...prev, [tx.id]: res }))
      toast.success(
        `${res.conciliadas.length} linhas conciliadas · Consumido ${formatBRL(res.valor_consumido)}` +
          (res.residuo_nao_consumido > 0 ? ` · Resíduo ${formatBRL(res.residuo_nao_consumido)}` : "") +
          (res.linhas_remanescentes_em_aberto > 0 ? ` · ${res.linhas_remanescentes_em_aberto} linhas remanescentes` : "")
      )
      // remove da lista de pendentes (foi conciliada com sucesso)
      setPendentes((prev) => prev.filter((p) => p.id !== tx.id))
    } catch (e) {
      const msg = e instanceof Error ? e.message : "erro"
      toast.error("Falha: " + msg)
    } finally {
      setExecutandoId(null)
    }
  }

  if (loading) return <div className="p-6 text-slate-500">Carregando…</div>

  return (
    <div className="p-6 space-y-5 max-w-5xl">
      <div>
        <a href="/conciliacao" className="text-xs text-slate-500 hover:text-slate-900">
          ← Voltar
        </a>
        <h1 className="mt-1 text-lg font-semibold text-slate-900">
          Pagamentos intragrupo (SPM → FD) · Conciliação em lote
        </h1>
        <p className="mt-1 text-xs text-slate-500 max-w-2xl">
          Cada PIX consolidado para empresa do grupo (categoria PAGAMENTO_INTRAGRUPO) é
          consumido em FIFO contra as linhas do orçamento com <code>empresa_pagadora=&lt;FD&gt;</code>,
          ordenadas por competência. Resíduo (tx maior que soma das linhas) fica reportado
          sem conciliação; déficit (tx menor) deixa linhas remanescentes em aberto.
        </p>
      </div>

      {pendentes.length === 0 ? (
        <div className="rounded-lg border border-slate-200 bg-white p-8 text-center">
          <div className="text-sm text-slate-700 font-semibold">Nenhuma transação pendente</div>
          <div className="text-xs text-slate-500 mt-1">
            Todas as PIX intragrupo estão conciliadas — ou não há classificação
            PAGAMENTO_INTRAGRUPO no período.
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {pendentes.map((tx) => {
            const resultado = resultados[tx.id]
            return (
              <div
                key={tx.id}
                className="rounded-lg border border-slate-200 bg-white p-4"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="text-xs text-slate-500">{tx.data_extrato}</div>
                    <div className="text-sm font-semibold text-slate-900 mt-0.5 truncate">
                      {tx.titular_pix ?? "(sem titular)"}
                    </div>
                    {tx.descricao && (
                      <div className="text-[11px] text-slate-500 mt-0.5 truncate">
                        {tx.descricao}
                      </div>
                    )}
                    <div className="mt-2 text-lg font-bold tabular-nums text-red-700">
                      {formatBRL(Math.abs(tx.valor))}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleConciliar(tx)}
                    disabled={executandoId === tx.id}
                    className="px-3 py-1.5 text-xs font-medium bg-blue-700 text-white rounded hover:bg-blue-800 disabled:opacity-50 whitespace-nowrap"
                  >
                    {executandoId === tx.id ? "Conciliando…" : "Conciliar em lote"}
                  </button>
                </div>

                {resultado && (
                  <div className="mt-3 rounded border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-900">
                    <div className="font-semibold">
                      ✓ {resultado.conciliadas.length} linhas conciliadas · Consumido {formatBRL(resultado.valor_consumido)}
                    </div>
                    {resultado.residuo_nao_consumido > 0 && (
                      <div className="mt-1 text-amber-800">
                        Resíduo: {formatBRL(resultado.residuo_nao_consumido)} (tx maior que soma das linhas)
                      </div>
                    )}
                    {resultado.linhas_remanescentes_em_aberto > 0 && (
                      <div className="mt-1 text-amber-800">
                        {resultado.linhas_remanescentes_em_aberto} linhas remanescentes em aberto (tx menor que soma)
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
