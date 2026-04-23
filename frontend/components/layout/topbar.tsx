"use client";
import { FilterEmpresa } from "./filter-empresa";
import { FilterCompetencia } from "./filter-competencia";
import { logout } from "@/lib/auth";

export function Topbar() {
  return (
    <header className="h-12 bg-slate-900 text-white px-4 flex items-center justify-between text-sm">
      <div className="font-semibold tracking-wide">⚕ SPM Financeiro</div>
      <div className="flex gap-2 items-center">
        <FilterEmpresa />
        <FilterCompetencia />
        <span className="text-xs text-slate-300 ml-2">Hugo</span>
        <button
          type="button"
          onClick={logout}
          className="ml-1 px-2 py-1 text-xs text-slate-400 hover:text-white hover:bg-slate-800 rounded transition"
          aria-label="Sair"
          title="Sair"
        >
          Sair
        </button>
      </div>
    </header>
  );
}
