"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Plus } from "lucide-react"
import { AxiosError } from "axios"
import { toast } from "sonner"

import { listarRodadas } from "@/lib/api"
import { listarAdiantamentos } from "@/lib/api/adiantamento"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { Skeleton } from "@/components/ui/skeleton"
import { RodadaStatusBadge } from "@/components/rodada/RodadaStatusBadge"
import { formatDateTime, formatPeriodo } from "@/lib/format"
import type { RodadaListItem } from "@/lib/types"

export default function RodadasPage() {
  const router = useRouter()
  const [rodadas, setRodadas] = useState<RodadaListItem[] | null>(null)
  const [adiantamentosAbertos, setAdiantamentosAbertos] = useState(0)

  useEffect(() => {
    listarRodadas()
      .then(setRodadas)
      .catch((err: AxiosError<{ error?: string }>) => {
        toast.error(err.response?.data?.error || "Falha ao listar rodadas")
        setRodadas([])
      })
  }, [])

  useEffect(() => {
    listarAdiantamentos({ status_filtro: "ABERTO" })
      .then((lista) => setAdiantamentosAbertos(lista.length))
      .catch(() => setAdiantamentosAbertos(0))
  }, [])

  return (
    <main className="mx-auto max-w-7xl w-full px-6 py-8 flex-1">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Rodadas de conciliacao</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Histórico de rodadas. Clique em uma para ver detalhes.
          </p>
        </div>
        <Link href="/rodadas/nova">
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Nova rodada
          </Button>
        </Link>
      </div>

      {adiantamentosAbertos > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-3 flex items-center justify-between">
          <div className="text-sm text-amber-900">
            ⚠ Há <b>{adiantamentosAbertos}</b> adiantamento(s) em aberto. Confira antes de aprovar rodadas.
          </div>
          <Link
            href="/adiantamentos"
            className="text-xs bg-amber-600 text-white px-3 py-1 rounded hover:bg-amber-700"
          >
            Ver adiantamentos →
          </Link>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Todas as rodadas</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Periodo do extrato</TableHead>
                <TableHead>Competencias PP</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Criado em</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rodadas === null && (
                <>
                  {[1, 2, 3].map((i) => (
                    <TableRow key={i}>
                      <TableCell><Skeleton className="h-4 w-40" /></TableCell>
                      <TableCell><Skeleton className="h-4 w-24" /></TableCell>
                      <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                      <TableCell><Skeleton className="h-4 w-32" /></TableCell>
                    </TableRow>
                  ))}
                </>
              )}
              {rodadas?.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground py-10">
                    Nenhuma rodada ainda. Clique em &ldquo;Nova rodada&rdquo; para comecar.
                  </TableCell>
                </TableRow>
              )}
              {rodadas?.map((r) => (
                <TableRow
                  key={r.id}
                  className="cursor-pointer hover:bg-muted/30"
                  onClick={() => router.push(`/rodadas/${r.id}`)}
                >
                  <TableCell className="tabular-nums">
                    {formatPeriodo(r.periodo_extrato_inicio, r.periodo_extrato_fim)}
                  </TableCell>
                  <TableCell className="tabular-nums">{(r.pp_competencias || []).join(", ")}</TableCell>
                  <TableCell><RodadaStatusBadge status={r.status} /></TableCell>
                  <TableCell className="tabular-nums text-muted-foreground">
                    {formatDateTime(r.criado_em)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </main>
  )
}
