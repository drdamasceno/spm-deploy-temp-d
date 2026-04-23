"use client"

import { useEffect, useState, use } from "react"
import { apiClient } from "@/lib/api"
import { fetchSplit } from "@/lib/api/transacoes"
import type { SplitResponse } from "@/types/v2"
import { SplitEditor } from "@/components/transacoes/split-editor"
import { toast } from "sonner"

interface TransacaoBancaria {
  id: string
  valor: number
  titular_pix: string | null
  descricao: string | null
  data_extrato: string | null
}

export default function SplitPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const [transacao, setTransacao] = useState<TransacaoBancaria | null>(null)
  const [split, setSplit] = useState<SplitResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      apiClient.get<TransacaoBancaria>(`/transacoes/${id}`).then((r) => r.data).catch(() => null),
      fetchSplit(id),
    ])
      .then(([tx, sp]) => {
        setSplit(sp)
        if (tx) {
          setTransacao(tx)
        } else {
          setTransacao({
            id,
            valor: sp.valor_transacao,
            titular_pix: null,
            descricao: null,
            data_extrato: null,
          })
        }
      })
      .catch((err) => {
        toast.error("Falha ao carregar transação: " + (err instanceof Error ? err.message : "erro"))
      })
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="p-6 text-slate-500">Carregando…</div>
  if (!transacao || !split) return <div className="p-6 text-slate-500">Sem dados.</div>

  return (
    <div className="p-6 max-w-4xl">
      <div className="mb-4">
        <a href="/conciliacao" className="text-xs text-slate-500 hover:text-slate-900">
          ← Voltar
        </a>
        <h1 className="mt-1 text-lg font-semibold text-slate-900">Dividir transação</h1>
        <p className="mt-1 text-xs text-slate-500">
          Quebre este lançamento em N alocações com bolsos diferentes (ex: fatura de cartão metade SPM,
          metade pessoal). A soma precisa bater com o valor da transação.
        </p>
      </div>
      <SplitEditor transacao={transacao} inicial={split.linhas} />
    </div>
  )
}
