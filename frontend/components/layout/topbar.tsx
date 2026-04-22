"use client";
import { FilterEmpresa } from "./filter-empresa";
import { FilterCompetencia } from "./filter-competencia";

export function Topbar() {
  return (
    <header className="h-12 bg-slate-900 text-white px-4 flex items-center justify-between text-sm">
      <div className="font-semibold tracking-wide">⚕ SPM Financeiro</div>
      <div className="flex gap-2 items-center">
        <FilterEmpresa />
        <FilterCompetencia />
        {/* Perfil do usuário — por agora apenas "Hugo" */}
        <span className="text-xs text-slate-300">Hugo</span>
      </div>
    </header>
  );
}
