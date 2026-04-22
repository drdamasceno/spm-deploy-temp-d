"use client"
import { formatBRL } from "@/lib/format"

interface Props {
  liquidezTotal: number
  disponivelAgora: number
  reservaTravada: number
}

export function LiquidezBanner({ liquidezTotal, disponivelAgora, reservaTravada }: Props) {
  return (
    <div
      className="px-5 py-4 flex items-center gap-4 text-white"
      style={{ background: "linear-gradient(135deg,#0f172a 0%,#1e293b 100%)" }}
    >
      <div className="flex-1 min-w-0">
        <div className="text-[11px] uppercase text-slate-400 tracking-wide mb-0.5">Liquidez total</div>
        <div className="text-2xl font-extrabold tabular-nums">{formatBRL(liquidezTotal)}</div>
      </div>
      <div className="flex gap-4 text-xs items-stretch">
        <div className="text-right">
          <div className="uppercase tracking-wide text-[10px] text-emerald-400">Disponível agora</div>
          <div className="font-bold text-white text-[15px] mt-0.5 tabular-nums">{formatBRL(disponivelAgora)}</div>
          <div className="text-[10px] text-slate-400 mt-0.5">Contas + apl. automáticas</div>
        </div>
        <div className="w-px bg-slate-600" />
        <div className="text-right">
          <div className="uppercase tracking-wide text-[10px] text-purple-300">Reserva travada</div>
          <div className="font-bold text-white text-[15px] mt-0.5 tabular-nums">{formatBRL(reservaTravada)}</div>
          <div className="text-[10px] text-slate-400 mt-0.5">Apl. manuais</div>
        </div>
      </div>
    </div>
  )
}
