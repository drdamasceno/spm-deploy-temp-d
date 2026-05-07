"use client";
import { cn } from "@/lib/utils";

// Tabs internas de /despesas-fixas. FATURAMENTO e DESPESA_PROFISSIONAIS
// foram extraídas pra abas top-level (/faturamento e /despesas-variaveis)
// na re-arquitetura de 2026-05-06 — não cabem aqui.
// Ordem: Tributos primeiro porque é o maior número (top of mind).
// PENDENTE é tab virtual — filtra linhas com categoria_id NULL em qualquer natureza.
const TABS: { natureza: string; label: string; pendente?: boolean }[] = [
  { natureza: "TRIBUTO", label: "Tributos" },
  { natureza: "DESPESA_FIXA", label: "Despesas Fixas" },
  { natureza: "SALARIO_VARIAVEL", label: "Variáveis · Salários" },
  { natureza: "COMISSAO", label: "Comissões" },
  { natureza: "VALOR_VARIAVEL", label: "Variáveis · Outros" },
  { natureza: "PENDENTE", label: "Pendente Identificar", pendente: true },
];

export function TabsSecoes({
  active,
  contagens,
  onChange,
}: {
  active: string;
  contagens: Record<string, number>;
  onChange: (n: string) => void;
}) {
  return (
    <div className="bg-white border-b border-slate-200 flex gap-0 overflow-x-auto">
      {TABS.map((t) => {
        const count = contagens[t.natureza] ?? 0;
        const isPendente = t.pendente === true;
        const corContagem = isPendente && count > 0 ? "text-amber-600 font-semibold" : "text-slate-400";
        return (
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
            <span className={cn("text-xs ml-1", corContagem)}>
              {isPendente && count > 0 ? `⚠ ${count}` : count}
            </span>
          </button>
        );
      })}
    </div>
  );
}
