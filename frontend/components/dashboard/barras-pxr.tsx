import type { BarraPxR } from "@/types/v2";

interface BarrasPxRProps {
  barras: BarraPxR[];
}

function formatShort(valor: number): string {
  // Abbrevia para "161k" / "1.2M" estilo mockup.
  const abs = Math.abs(valor);
  if (abs >= 1_000_000) return `${(valor / 1_000_000).toFixed(1).replace(".", ",")}M`;
  if (abs >= 1_000) return `${Math.round(valor / 1_000)}k`;
  return Math.round(valor).toString();
}

function fillColor(pct: number): string {
  if (pct >= 80) return "bg-emerald-500";
  if (pct >= 40) return "bg-amber-500";
  return "bg-red-500";
}

export function BarrasPxR({ barras }: BarrasPxRProps) {
  if (!barras || barras.length === 0) {
    return (
      <div className="text-sm text-slate-500 py-6 text-center">
        Sem dados de previsto × realizado.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2.5">
      {barras.map((b) => {
        const pctClamped = Math.max(0, Math.min(100, b.pct));
        return (
          <div
            key={b.categoria}
            className="grid grid-cols-[110px_1fr_90px] gap-2.5 items-center text-xs"
          >
            <span className="text-slate-700 truncate">{b.categoria}</span>
            <div className="bg-slate-200 h-5 rounded overflow-hidden">
              <div
                className={`${fillColor(b.pct)} h-full rounded`}
                style={{ width: `${pctClamped}%` }}
              />
            </div>
            <span className="text-xs text-slate-500 tabular-nums text-right">
              {Math.round(b.pct)}% · {formatShort(b.realizado)} / {formatShort(b.previsto)}
            </span>
          </div>
        );
      })}
    </div>
  );
}
