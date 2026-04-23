import type { KPIs } from "@/types/v2";
import { formatBRL } from "@/lib/format";

interface KpisGridProps {
  kpis: KPIs;
}

interface KpiCardProps {
  label: string;
  value: number;
}

function KpiCard({ label, value }: KpiCardProps) {
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="text-xs text-slate-500 uppercase tracking-wide mb-1">
        {label}
      </div>
      <div className="text-xl font-bold text-slate-900 tabular-nums">
        {formatBRL(value)}
      </div>
    </div>
  );
}

export function KpisGrid({ kpis }: KpisGridProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      <KpiCard label="Entradas do mês" value={kpis.entradas_do_mes} />
      <KpiCard label="Saídas do mês" value={kpis.saidas_mes} />
      <KpiCard label="Previsto a pagar" value={kpis.previsto_a_pagar} />
      <KpiCard label="Saldo atual" value={kpis.saldo_atual} />
    </div>
  );
}
