"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

// Re-arquitetura 2026-05-06: aba Orçamento foi desmembrada em 3 abas
// (Faturamento, Despesas Fixas, Despesas Variáveis). Ordem do nav segue o
// fluxo Receita → Despesas → Detalhe por Contrato → Pagamentos antecipados
// → Operação interna → Cadastros.
const ITEMS = [
  { href: "/", label: "Dashboard" },
  { href: "/faturamento", label: "Faturamento" },
  { href: "/despesas-fixas", label: "Despesas Fixas" },
  { href: "/despesas-variaveis", label: "Despesas Variáveis" },
  { href: "/contratos", label: "Contratos" },
  { href: "/adiantamentos", label: "Adiantamentos" },
  { href: "/rodadas", label: "Rodadas PP" },
  { href: "/conciliacao", label: "Conciliação" },
  { href: "/extratos", label: "Extratos" },
  { href: "/cadastros", label: "Cadastros" },
];

export function Nav() {
  const pathname = usePathname();
  return (
    <nav className="h-10 bg-slate-800 text-slate-300 px-4 flex gap-1 text-sm overflow-x-auto">
      {ITEMS.map((it) => {
        const active = pathname === it.href || (it.href !== "/" && pathname.startsWith(it.href));
        return (
          <Link
            key={it.href}
            href={it.href}
            className={cn(
              "px-3 py-2 whitespace-nowrap border-b-2 border-transparent",
              active && "text-white font-medium border-blue-500 bg-slate-900"
            )}
          >
            {it.label}
          </Link>
        );
      })}
    </nav>
  );
}
