import { Badge } from "@/components/ui/badge"

const STATUS_MAP: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  CRIADA: { label: "Criada", variant: "outline" },
  PROCESSANDO: { label: "Processando", variant: "secondary" },
  CONCILIADA: { label: "Conciliada", variant: "default" },
  VALIDADA: { label: "Validada", variant: "default" },
  CANCELADA: { label: "Cancelada", variant: "destructive" },
}

export function RodadaStatusBadge({ status }: { status: string }) {
  const info = STATUS_MAP[status] || { label: status, variant: "outline" as const }
  return <Badge variant={info.variant}>{info.label}</Badge>
}
