export function formatBRL(valor: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(valor)
}

export function formatPct(valor: number, digits = 2): string {
  return `${valor.toFixed(digits)}%`
}

export function formatDate(iso: string): string {
  if (!iso) return "—"
  // Backend retorna 'YYYY-MM-DD' (coluna DATE do Postgres) e tambem 'YYYY-MM-DDTHH:MM:SS...'
  // (colunas TIMESTAMPTZ criado_em). Para datas puras, new Date('2026-04-01')
  // interpreta como UTC 00:00:00 -> BRT (UTC-3) vira 2026-03-31 21:00. Bug de 1 dia.
  // Fix: quando a string for puramente YYYY-MM-DD, parseamos manualmente e formatamos
  // sem criar Date (evita qualquer conversao de timezone).
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso)
  if (dateOnly) {
    const [, y, m, d] = dateOnly
    return `${d}/${m}/${y}`
  }
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" })
}

export function formatDateTime(iso: string): string {
  if (!iso) return "—"
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  return d.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export function formatPeriodo(inicio: string, fim: string): string {
  return `${formatDate(inicio)} — ${formatDate(fim)}`
}

export function formatDataBR(iso: string): string {
  const [y, m, d] = iso.split("-")
  return `${d}/${m}/${y.slice(2)}`
}
