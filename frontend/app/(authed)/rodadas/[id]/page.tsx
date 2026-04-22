"use client"

import { use, useEffect, useState } from "react"
import { RefreshCw } from "lucide-react"
import { AxiosError } from "axios"
import { toast } from "sonner"

import { conciliarRodada, getResultado } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { RodadaStatusBadge } from "@/components/rodada/RodadaStatusBadge"
import { ResumoCards } from "@/components/rodada/ResumoCards"
import { TransacoesTable } from "@/components/rodada/TransacoesTable"
import { formatBRL, formatPct } from "@/lib/format"
import type { ResultadoResponse } from "@/lib/types"

export default function RodadaDetalhesPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const [resultado, setResultado] = useState<ResultadoResponse | null>(null)
  const [page, setPage] = useState(1)
  const [reconciliando, setReconciliando] = useState(false)

  async function load(p = page) {
    setResultado(null)
    try {
      const r = await getResultado(id, p, 50)
      setResultado(r)
    } catch (err) {
      const ax = err as AxiosError<{ error?: string }>
      toast.error(ax.response?.data?.error || "Falha ao carregar resultado")
    }
  }

  useEffect(() => { load(page) }, [id, page])  // eslint-disable-line react-hooks/exhaustive-deps

  async function reprocessar() {
    setReconciliando(true)
    try {
      await conciliarRodada(id)
      toast.success("Rodada reprocessada")
      await load(1)
      setPage(1)
    } catch (err) {
      const ax = err as AxiosError<{ error?: string }>
      toast.error(ax.response?.data?.error || "Falha ao reprocessar")
    } finally {
      setReconciliando(false)
    }
  }

  return (
    <main className="mx-auto max-w-7xl w-full px-6 py-8 flex-1 space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Rodada</h1>
          <p className="text-xs text-muted-foreground mt-1 font-mono">{id}</p>
        </div>
        <Button variant="outline" size="sm" onClick={reprocessar} disabled={reconciliando}>
          <RefreshCw className={`h-4 w-4 mr-2 ${reconciliando ? "animate-spin" : ""}`} />
          {reconciliando ? "Reprocessando..." : "Reprocessar"}
        </Button>
      </div>

      {/* Resumo principal */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Resumo</CardTitle>
        </CardHeader>
        <CardContent>
          {!resultado ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[1, 2, 3, 4].map((i) => (<Skeleton key={i} className="h-20" />))}
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <div className="text-xs uppercase text-muted-foreground tracking-wide">% Conciliado</div>
                <div className="text-3xl font-semibold tabular-nums mt-1">{formatPct(resultado.percentual_conciliado)}</div>
              </div>
              <div>
                <div className="text-xs uppercase text-muted-foreground tracking-wide">Valor conciliado</div>
                <div className="text-xl font-semibold tabular-nums mt-1">{formatBRL(resultado.valor_total_conciliado)}</div>
              </div>
              <div>
                <div className="text-xs uppercase text-muted-foreground tracking-wide">Valor total PP</div>
                <div className="text-xl font-semibold tabular-nums mt-1">{formatBRL(resultado.valor_total_pp)}</div>
              </div>
              <div>
                <div className="text-xs uppercase text-muted-foreground tracking-wide">Transacoes</div>
                <div className="text-xl font-semibold tabular-nums mt-1">
                  {resultado.pagination.total}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Cards por status */}
      {resultado && (
        <ResumoCards
          resumoTransacoes={resultado.resumo_transacoes}
          resumoRegistrosPP={resultado.resumo_registros_pp}
          valorTotalPP={resultado.valor_total_pp}
          valorTotalConciliado={resultado.valor_total_conciliado}
          percentualConciliado={resultado.percentual_conciliado}
        />
      )}

      {/* Tabela de transacoes */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Transacoes</CardTitle>
        </CardHeader>
        <CardContent>
          {!resultado ? (
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map((i) => (<Skeleton key={i} className="h-10" />))}
            </div>
          ) : (
            <TransacoesTable
              transacoes={resultado.transacoes}
              page={resultado.pagination.page}
              perPage={resultado.pagination.per_page}
              total={resultado.pagination.total}
              onPageChange={setPage}
            />
          )}
        </CardContent>
      </Card>
    </main>
  )
}
