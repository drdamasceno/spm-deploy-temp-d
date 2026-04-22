"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const ITEMS = [
  { href: "/", label: "Dashboard" },
  { href: "/conciliacao", label: "Conciliação" },
  { href: "/contratos", label: "Contratos" },
  { href: "/rodadas", label: "Rodadas PP" },
  { href: "/orcamento", label: "Orçamento" },
  { href: "/adiantamentos", label: "Adiantamentos" },
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
