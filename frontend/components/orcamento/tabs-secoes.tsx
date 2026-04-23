"use client";
import type { NaturezaOrcamento } from "@/types/v2";
import { cn } from "@/lib/utils";

const TABS: { natureza: NaturezaOrcamento; label: string }[] = [
  { natureza: "DESPESA_FIXA", label: "Despesas Fixas" },
  { natureza: "TRIBUTO", label: "Tributos" },
  { natureza: "SALARIO_VARIAVEL", label: "Variáveis · Salários" },
  { natureza: "COMISSAO", label: "Comissões" },
  { natureza: "VALOR_VARIAVEL", label: "Variáveis · Outros" },
  { natureza: "DESPESA_PROFISSIONAIS", label: "Profissionais (PP)" },
  { natureza: "FATURAMENTO", label: "Faturamento" },
];

export function TabsSecoes({
  active,
  contagens,
  onChange,
}: {
  active: NaturezaOrcamento;
  contagens: Record<NaturezaOrcamento, number>;
  onChange: (n: NaturezaOrcamento) => void;
}) {
  return (
    <div className="bg-white border-b border-slate-200 flex gap-0 overflow-x-auto">
      {TABS.map((t) => (
        <button
          key={t.natureza}
          onClick={() => onChange(t.natureza)}
          className={cn(
            "px-4 py-3 text-sm font-medium border-b-2 border-transparent whitespace-nowrap",
            active === t.natureza
              ? "text-slate-900 border-blue-500"
              : "text-slate-500 hover:text-slate-700"
          )}
        >
          {t.label}{" "}
          <span className="text-xs text-slate-400 ml-1">
            {contagens[t.natureza] ?? 0}
          </span>
        </button>
      ))}
    </div>
  );
}
