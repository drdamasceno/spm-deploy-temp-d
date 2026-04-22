"use client";
import Link from "next/link";
import { formatBRL } from "@/lib/format";
import type { ContratoCompetenciaOut } from "@/types/v2";

interface Props {
  contrato: ContratoCompetenciaOut;
}

export function ContratoCard({ contrato }: Props) {
  const pct = contrato.percentual_pago;
  let pctColor = "bg-red-500";
  if (pct >= 80) pctColor = "bg-emerald-500";
  else if (pct >= 40) pctColor = "bg-blue-500";
  else if (pct >= 10) pctColor = "bg-amber-500";

  let statusLabel = "Pendente";
  let statusBg = "bg-red-100 text-red-900";
  if (pct >= 100) {
    statusLabel = "Pago";
    statusBg = "bg-emerald-100 text-emerald-900";
  } else if (pct > 0) {
    statusLabel = "Parcial";
    statusBg = "bg-blue-100 text-blue-900";
  }

  const qtdPrestadores = contrato.prestadores.length;
  const qtdPagos = contrato.prestadores.filter((p) => p.status === "PAGO").length;
  const qtdPendentes = contrato.prestadores.filter(
    (p) => p.status === "PENDENTE"
  ).length;

  return (
    <Link
      href={`/contratos/${contrato.contrato_id}/${contrato.competencia}`}
      className="block bg-white border border-slate-200 rounded-lg p-4 hover:border-blue-400 hover:shadow-sm transition"
    >
      <div className="grid grid-cols-1 lg:grid-cols-[2fr_3fr_1fr] gap-4 items-center">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-sm font-semibold text-slate-900">
              {contrato.nome_contrato}
            </h3>
            <span
              className={`text-[10px] px-1.5 py-0.5 rounded font-semibold uppercase ${statusBg}`}
            >
              {pct.toFixed(0)}% {statusLabel}
            </span>
          </div>
          <div className="text-xs text-slate-500">
            Comp. {contrato.competencia} · {qtdPrestadores} prestadores ·{" "}
            {qtdPagos} pagos · {qtdPendentes} pendentes
          </div>
        </div>

        <div className="grid grid-cols-4 gap-2 text-xs">
          <Stat
            label="Receita prev."
            value={
              contrato.receita_prevista !== null
                ? formatBRL(contrato.receita_prevista)
                : "—"
            }
          />
          <Stat label="Despesa prev." value="—" />
          <Stat label="Despesa real" value={formatBRL(contrato.total_pago)} />
          <Stat
            label="Margem proj."
            value={
              contrato.margem_projetada !== null
                ? `${contrato.margem_projetada.toFixed(1)}%`
                : "—"
            }
            color="text-emerald-600"
          />
        </div>

        <div className="text-right">
          <div className="text-[10px] uppercase text-slate-500 mb-1">
            conciliado
          </div>
          <div className="text-lg font-bold text-slate-900 tabular-nums">
            {pct.toFixed(0)}%
          </div>
          <div className="h-1.5 bg-slate-200 rounded overflow-hidden">
            <div
              className={`h-full ${pctColor}`}
              style={{ width: `${Math.min(100, pct)}%` }}
            />
          </div>
        </div>
      </div>
    </Link>
  );
}

function Stat({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div>
      <div className="text-[10px] text-slate-500 uppercase tracking-wide">
        {label}
      </div>
      <div
        className={`text-xs font-semibold tabular-nums ${color ?? "text-slate-900"}`}
      >
        {value}
      </div>
    </div>
  );
}
