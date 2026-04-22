"use client";
import { useFilters } from "@/lib/filters-context";
import { EmpresaCodigo } from "@/types/v2";

export function FilterEmpresa() {
  const { empresa, setEmpresa } = useFilters();
  return (
    <select
      value={empresa}
      onChange={(e) => setEmpresa(e.target.value as EmpresaCodigo)}
      className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs"
    >
      <option value="SPM">SPM</option>
      <option value="FD">FD</option>
      <option value="TODAS">SPM+FD</option>
    </select>
  );
}
