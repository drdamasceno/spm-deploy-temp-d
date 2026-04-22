"use client";
import { useMemo } from "react";
import { useFilters } from "@/lib/filters-context";

const MESES_PT = [
  "Jan",
  "Fev",
  "Mar",
  "Abr",
  "Mai",
  "Jun",
  "Jul",
  "Ago",
  "Set",
  "Out",
  "Nov",
  "Dez",
];

export function FilterCompetencia() {
  const { competencia, setCompetencia } = useFilters();

  const opcoes = useMemo(() => {
    const hoje = new Date();
    const lista: { value: string; label: string }[] = [];
    // 6 meses atrás -> mês atual -> 5 meses à frente (total 12)
    for (let delta = -6; delta <= 5; delta++) {
      const d = new Date(hoje.getFullYear(), hoje.getMonth() + delta, 1);
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, "0");
      lista.push({
        value: `${y}-${m}`,
        label: `${MESES_PT[d.getMonth()]}/${String(y).slice(-2)}`,
      });
    }
    return lista;
  }, []);

  // Se a competência persistida no contexto não estiver na lista (ex: mês muito antigo
  // salvo em localStorage), garante que ela apareça como primeira opção para não sumir.
  const opcoesFinal = useMemo(() => {
    if (competencia && !opcoes.some((o) => o.value === competencia)) {
      const [y, m] = competencia.split("-");
      const idx = Math.max(0, Math.min(11, Number(m) - 1));
      return [
        { value: competencia, label: `${MESES_PT[idx]}/${y.slice(-2)}` },
        ...opcoes,
      ];
    }
    return opcoes;
  }, [competencia, opcoes]);

  return (
    <select
      value={competencia}
      onChange={(e) => setCompetencia(e.target.value)}
      className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs text-white"
    >
      {opcoesFinal.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}
