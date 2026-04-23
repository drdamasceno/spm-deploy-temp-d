"use client"

import { useEffect, useState } from "react"
import { fetchHistorico } from "@/lib/api/dashboard"
import type { HistoricoResponse } from "@/types/v2"
import { CrescimentoCaixa } from "./crescimento-caixa"
import { Faturamento } from "./faturamento"
import { DespesasPorTipo } from "./despesas-por-tipo"
import { PosicaoEmAberto } from "./posicao-em-aberto"

export function TendenciaGrid() {
  const [data, setData] = useState<HistoricoResponse | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    fetchHistorico(6)
      .then(setData)
      .catch((e) => setErro(e instanceof Error ? e.message : "erro"))
  }, [])

  if (erro) {
    return (
      <div className="text-xs text-slate-500 p-4">Tendência indisponível: {erro}</div>
    )
  }
  if (!data) {
    return <div className="text-xs text-slate-500 p-4">Carregando tendência…</div>
  }

  return (
    <div className="bg-slate-50 rounded-lg p-4">
      <div className="text-xs font-bold text-slate-800 uppercase tracking-wide mb-3">
        Tendência · últimos {data.meses.length} meses
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <CrescimentoCaixa meses={data.meses} />
        <Faturamento meses={data.meses} />
        <DespesasPorTipo meses={data.meses} />
        <PosicaoEmAberto meses={data.meses} />
      </div>
    </div>
  )
}
