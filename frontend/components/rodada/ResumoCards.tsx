import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { ResumoTransacoes, ResumoRegistrosPP } from "@/lib/types"
import { STATUS_LABELS } from "@/lib/types"

type Props = {
  resumoTransacoes: ResumoTransacoes
  resumoRegistrosPP: ResumoRegistrosPP
  valorTotalPP: number
  valorTotalConciliado: number
  percentualConciliado: number
}

function Card1({ title, value, hint }: { title: string; value: string; hint?: string }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="text-2xl font-semibold tabular-nums">{value}</div>
        {hint && <div className="text-xs text-muted-foreground mt-1">{hint}</div>}
      </CardContent>
    </Card>
  )
}

export function ResumoCards({ resumoTransacoes: rtx, resumoRegistrosPP: rpp }: Props) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      <Card1 title={STATUS_LABELS.MATCH_AUTOMATICO} value={String(rtx.match_automatico)} />
      <Card1 title={STATUS_LABELS.FRACIONADO} value={String(rtx.fracionado)} />
      <Card1 title={STATUS_LABELS.CONCILIADO_POR_CATEGORIA} value={String(rtx.conciliado_categoria)} />
      <Card1 title={STATUS_LABELS.MANUAL_PENDENTE} value={String(rtx.manual_pendente)} />
      <Card1 title={STATUS_LABELS.NAO_CLASSIFICADO} value={String(rtx.nao_classificado)} />
      <Card1 title="PP elegivel" value={String(rpp.total_elegivel)} />
      <Card1 title="Sem movimento" value={String(rpp.sem_movimento)} />
      <Card1 title="Saldo negativo" value={String(rpp.saldo_negativo)} />
    </div>
  )
}
