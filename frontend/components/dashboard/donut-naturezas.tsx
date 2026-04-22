import { formatBRL } from "@/lib/format";

interface DonutNaturezasProps {
  saidas: Record<string, number>;
}

// Cores por natureza — tailwind class + hex equivalente (para stroke SVG).
// Mantido aqui porque SVG stroke não aceita classes Tailwind JIT de forma
// confiável em runtime.
const NATUREZA_CONFIG: Record<string, { label: string; color: string; dotClass: string }> = {
  DESPESA_FIXA: { label: "Despesa fixa", color: "#10b981", dotClass: "bg-emerald-500" },
  TRIBUTO: { label: "Tributo", color: "#f59e0b", dotClass: "bg-amber-500" },
  SALARIO_VARIAVEL: { label: "Salário variável", color: "#3b82f6", dotClass: "bg-blue-500" },
  COMISSAO: { label: "Comissão", color: "#d946ef", dotClass: "bg-fuchsia-500" },
  VALOR_VARIAVEL: { label: "Valor variável", color: "#0ea5e9", dotClass: "bg-sky-500" },
  DESPESA_PROFISSIONAIS: { label: "Despesa profissionais", color: "#f43f5e", dotClass: "bg-rose-500" },
};

const FALLBACK = { label: "Outros", color: "#64748b", dotClass: "bg-slate-500" };

export function DonutNaturezas({ saidas }: DonutNaturezasProps) {
  const entries = Object.entries(saidas).filter(([, v]) => v !== 0);
  const total = entries.reduce((acc, [, v]) => acc + v, 0);

  if (total === 0 || entries.length === 0) {
    return (
      <div className="text-sm text-slate-500 py-6 text-center">
        Sem saídas no período.
      </div>
    );
  }

  // stroke-dasharray em viewBox 42 — circunferência ~= 100 (2*pi*15.915).
  // Para cada natureza: dash = pct; gap = 100 - pct; dashoffset acumulado.
  let offset = 25; // offset inicial para começar no topo (12h)
  const arcs = entries.map(([natureza, valor]) => {
    const pct = (valor / total) * 100;
    const cfg = NATUREZA_CONFIG[natureza] ?? FALLBACK;
    const arc = {
      natureza,
      label: cfg.label,
      color: cfg.color,
      dotClass: cfg.dotClass,
      valor,
      pct,
      dasharray: `${pct} ${100 - pct}`,
      dashoffset: offset,
    };
    offset = offset - pct; // stroke-dashoffset negativo avança no sentido horário
    return arc;
  });

  return (
    <div className="flex items-center gap-4">
      <svg viewBox="0 0 42 42" className="w-40 h-40 shrink-0">
        <circle
          cx="21"
          cy="21"
          r="15.915"
          fill="none"
          stroke="#f1f5f9"
          strokeWidth="6"
        />
        {arcs.map((a) => (
          <circle
            key={a.natureza}
            cx="21"
            cy="21"
            r="15.915"
            fill="none"
            stroke={a.color}
            strokeWidth="6"
            strokeDasharray={a.dasharray}
            strokeDashoffset={a.dashoffset}
            transform="rotate(-90 21 21)"
          />
        ))}
      </svg>
      <ul className="flex flex-col gap-1.5 text-xs flex-1 min-w-0">
        {arcs.map((a) => (
          <li key={a.natureza} className="flex items-center gap-2">
            <span
              className={`inline-block w-2.5 h-2.5 rounded-sm shrink-0 ${a.dotClass}`}
            />
            <span className="text-slate-700 truncate">{a.label}</span>
            <span className="ml-auto text-slate-500 tabular-nums shrink-0">
              {formatBRL(a.valor)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
