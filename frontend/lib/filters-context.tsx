"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { EmpresaCodigo } from "@/types/v2";

interface FiltersContextType {
  empresa: EmpresaCodigo;
  setEmpresa: (e: EmpresaCodigo) => void;
  competencia: string;
  setCompetencia: (c: string) => void;
}

const FiltersContext = createContext<FiltersContextType | null>(null);

export function FiltersProvider({ children }: { children: ReactNode }) {
  const [empresa, setEmpresa] = useState<EmpresaCodigo>("SPM");
  const [competencia, setCompetencia] = useState<string>(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
  });

  useEffect(() => {
    const savedE = localStorage.getItem("spm_filter_empresa");
    if (savedE === "SPM" || savedE === "FD" || savedE === "TODAS") setEmpresa(savedE);
    const savedC = localStorage.getItem("spm_filter_competencia");
    if (savedC && /^\d{4}-\d{2}$/.test(savedC)) setCompetencia(savedC);
  }, []);

  useEffect(() => {
    localStorage.setItem("spm_filter_empresa", empresa);
  }, [empresa]);
  useEffect(() => {
    localStorage.setItem("spm_filter_competencia", competencia);
  }, [competencia]);

  return (
    <FiltersContext.Provider value={{ empresa, setEmpresa, competencia, setCompetencia }}>
      {children}
    </FiltersContext.Provider>
  );
}

export function useFilters() {
  const ctx = useContext(FiltersContext);
  if (!ctx) throw new Error("useFilters fora do FiltersProvider");
  return ctx;
}
