import type { Alerta } from "@/types/v2";

interface AlertasListProps {
  alertas: Alerta[];
}

const TIPO_CONFIG: Record<Alerta["tipo"], { border: string; label: string }> = {
  NAO_CONCILIADO: { border: "border-red-500", label: "Não conciliado" },
  VENCIDO: { border: "border-amber-500", label: "Vencido" },
  PAGO_A_MAIOR: { border: "border-red-600", label: "Pago a maior" },
  ESTORNO: { border: "border-blue-500", label: "Estorno" },
};

export function AlertasList({ alertas }: AlertasListProps) {
  if (!alertas || alertas.length === 0) {
    return (
      <div className="text-sm text-slate-500 py-2">
        Nenhum alerta no período.
      </div>
    );
  }

  return (
    <ul className="flex flex-col">
      {alertas.map((a, idx) => {
        const cfg = TIPO_CONFIG[a.tipo];
        return (
          <li
            key={`${a.tipo}-${a.ref_id ?? idx}`}
            className={`border-l-4 pl-3 py-2 mb-1 bg-slate-50 rounded-sm text-sm ${cfg.border}`}
          >
            <span className="font-semibold text-slate-800 mr-2">
              {cfg.label}
            </span>
            <span className="text-slate-700">{a.mensagem}</span>
          </li>
        );
      })}
    </ul>
  );
}
