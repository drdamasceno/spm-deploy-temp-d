"use client"

import { Fragment, useState } from "react"
import { ChevronDown, ChevronRight } from "lucide-react"

import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { TransacaoResultado } from "@/lib/types"
import { STATUS_LABELS, STATUS_VARIANTS, type StatusConciliacao } from "@/lib/types"
import { formatBRL, formatDate } from "@/lib/format"

type Props = {
  transacoes: TransacaoResultado[]
  page: number
  perPage: number
  total: number
  onPageChange: (page: number) => void
}

const STATUS_OPTIONS: Array<StatusConciliacao | "ALL"> = [
  "ALL",
  "MATCH_AUTOMATICO",
  "FRACIONADO",
  "CONCILIADO_POR_CATEGORIA",
  "MANUAL_PENDENTE",
  "NAO_CLASSIFICADO",
]

export function TransacoesTable({ transacoes, page, perPage, total, onPageChange }: Props) {
  const [filtroStatus, setFiltroStatus] = useState<string>("ALL")
  const [filtroCategoria, setFiltroCategoria] = useState<string>("")
  const [busca, setBusca] = useState<string>("")
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  // Filtros client-side sobre a pagina atual
  const filtradas = transacoes.filter((t) => {
    if (filtroStatus !== "ALL" && t.status_conciliacao !== filtroStatus) return false
    if (filtroCategoria && (t.categoria || "").toLowerCase() !== filtroCategoria.toLowerCase()) return false
    if (busca) {
      const b = busca.toLowerCase()
      const hit = (t.titular_pix || "").toLowerCase().includes(b) || (t.descricao || "").toLowerCase().includes(b)
      if (!hit) return false
    }
    return true
  })

  const totalPages = Math.max(1, Math.ceil(total / perPage))

  function toggleExpand(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const categoriasUnicas = Array.from(new Set(transacoes.map((t) => t.categoria).filter(Boolean))) as string[]

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Input
          placeholder="Busca por titular ou descricao"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          className="max-w-sm"
        />
        <Select value={filtroStatus} onValueChange={(v) => setFiltroStatus(v ?? "ALL")}>
          <SelectTrigger className="w-[240px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((s) => (
              <SelectItem key={s} value={s}>
                {s === "ALL" ? "Todos os status" : STATUS_LABELS[s as StatusConciliacao]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={filtroCategoria || "ALL"} onValueChange={(v) => setFiltroCategoria(v === "ALL" || !v ? "" : v)}>
          <SelectTrigger className="w-[240px]">
            <SelectValue placeholder="Categoria" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">Todas as categorias</SelectItem>
            {categoriasUnicas.map((c) => (
              <SelectItem key={c} value={c}>{c}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="ml-auto text-sm text-muted-foreground tabular-nums">
          {filtradas.length} / {total} (pagina {page} de {totalPages})
        </div>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10" />
              <TableHead>Data</TableHead>
              <TableHead className="text-right">Valor</TableHead>
              <TableHead>Titular</TableHead>
              <TableHead>Descricao</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Categoria</TableHead>
              <TableHead>Prestador PP</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtradas.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} className="text-center text-muted-foreground py-10">
                  Nenhuma transacao nesta pagina com os filtros atuais.
                </TableCell>
              </TableRow>
            )}
            {filtradas.map((t) => {
              const isExpanded = expanded.has(t.id)
              const variant = STATUS_VARIANTS[t.status_conciliacao as StatusConciliacao] || "outline"
              return (
                <Fragment key={t.id}>
                  <TableRow className="cursor-pointer" onClick={() => toggleExpand(t.id)}>
                    <TableCell>
                      {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                    </TableCell>
                    <TableCell className="tabular-nums">{formatDate(t.data_extrato)}</TableCell>
                    <TableCell className={`text-right tabular-nums ${t.valor < 0 ? "text-destructive" : ""}`}>
                      {formatBRL(t.valor)}
                    </TableCell>
                    <TableCell className="max-w-[200px] truncate">{t.titular_pix || "—"}</TableCell>
                    <TableCell className="max-w-[260px] truncate text-muted-foreground">{t.descricao || "—"}</TableCell>
                    <TableCell><Badge variant={variant}>{STATUS_LABELS[t.status_conciliacao as StatusConciliacao] || t.status_conciliacao}</Badge></TableCell>
                    <TableCell className="text-xs">{t.categoria || "—"}</TableCell>
                    <TableCell className="max-w-[220px] truncate">{t.registro_pp?.prestador_nome || "—"}</TableCell>
                  </TableRow>
                  {isExpanded && t.registro_pp && (
                    <TableRow className="bg-muted/40">
                      <TableCell />
                      <TableCell colSpan={7}>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm py-2">
                          <div>
                            <div className="text-xs text-muted-foreground">Prestador</div>
                            <div>{t.registro_pp.prestador_nome || "—"}</div>
                          </div>
                          <div>
                            <div className="text-xs text-muted-foreground">Contrato</div>
                            <div className="truncate">{t.registro_pp.contrato_nome || "—"}</div>
                          </div>
                          <div>
                            <div className="text-xs text-muted-foreground">Competencia</div>
                            <div className="tabular-nums">{t.registro_pp.mes_competencia}</div>
                          </div>
                          <div>
                            <div className="text-xs text-muted-foreground">Saldo PP</div>
                            <div className="tabular-nums">{formatBRL(t.registro_pp.saldo_pp)}</div>
                          </div>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </Fragment>
              )
            })}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">Total: {total} transacoes</div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
            Anterior
          </Button>
          <div className="text-sm tabular-nums">
            {page} / {totalPages}
          </div>
          <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>
            Proxima
          </Button>
        </div>
      </div>
    </div>
  )
}
