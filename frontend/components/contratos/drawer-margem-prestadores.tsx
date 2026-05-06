"use client";
import { useEffect, useState } from "react";
import {
  getMargemPorProfissional,
  type MargemPorProfissional,
} from "@/lib/api/margem";
import { formatBRL, formatDataBR } from "@/lib/format";

interface Props {
  contratoId: string | null; // null = drawer fechado
  rotuloContrato: string | null;
  competencia: string;
  onClose: () => void;
}

/**
 * Drawer slide-over que mostra margem de cada profissional dentro de um
 * contrato + competência. Cruza:
 *   - registro_pp.valor_bonificado (filtrado pela rodada mais recente)
 *   - orcamento_linha FATURAMENTO da chave (contrato, competência)
 *   - retorno_pix CNAB-240 matched ao prestador (CONFIRMADO)
 *
 * Receita do contrato é rateada proporcional ao valor_bonificado de cada
 * prestador (share = bonif / total_bonif). Margem = receita_atribuída − bonif.
 */
export function DrawerMargemPrestadores({
  contratoId,
  rotuloContrato,
  competencia,
  onClose,
}: Props) {
  const [linhas, setLinhas] = useState<MargemPorProfissional[]>([]);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!contratoId) return;
    setLoading(true);
    setErro(null);
    getMargemPorProfissional(contratoId, competencia)
      .then(setLinhas)
      .catch((e: unknown) => setErro(e instanceof Error ? e.message : "erro"))
      .finally(() => setLoading(false));
  }, [contratoId, competencia]);

  const aberto = contratoId !== null;

  const totalBonif = linhas.reduce((s, l) => s + l.bonificacao, 0);
  const totalReceita = linhas.reduce((s, l) => s + l.receita_atribuida, 0);
  const totalMargem = linhas.reduce((s, l) => s + l.margem_absoluta, 0);
  const totalPix = linhas.reduce((s, l) => s + l.pix_confirmado, 0);
  const margemPctTotal = totalReceita > 0 ? (totalMargem / totalReceita) * 100 : null;

  return (
    <>
      {/* overlay */}
      <div
        onClick={onClose}
        className={
          "fixed inset-0 bg-black/30 z-40 transition-opacity " +
          (aberto ? "opacity-100" : "opacity-0 pointer-events-none")
        }
      />
      {/* drawer */}
      <div
        className={
          "fixed inset-y-0 right-0 w-[640px] bg-white border-l border-slate-200 shadow-2xl z-50 flex flex-col transition-transform duration-200 " +
          (aberto ? "translate-x-0" : "translate-x-full")
        }
      >
        <div className="bg-slate-900 text-white px-4 py-3 flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-sm">
              Margem por profissional
            </h3>
            <div className="text-[11px] text-slate-400 mt-0.5">
              {rotuloContrato ?? ""} · {formatCompetencia(competencia)}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white text-xl leading-none"
            aria-label="Fechar"
          >
            ×
          </button>
        </div>

        {/* resumo */}
        <div className="bg-slate-50 border-b border-slate-200 px-4 py-3 grid grid-cols-4 gap-2 text-[11px]">
          <Mini label="Bonificação" value={formatBRL(totalBonif)} />
          <Mini label="Receita atribuída" value={formatBRL(totalReceita)} />
          <Mini
            label="Margem"
            value={
              margemPctTotal !== null
                ? `${formatBRL(totalMargem)} (${margemPctTotal.toFixed(1)}%)`
                : formatBRL(totalMargem)
            }
            cor={totalMargem >= 0 ? "text-emerald-700" : "text-red-700"}
          />
          <Mini
            label="PIX confirmado (CNAB)"
            value={formatBRL(totalPix)}
            cor="text-slate-700"
          />
        </div>

        {/* lista */}
        <div className="flex-1 overflow-y-auto">
          {loading && (
            <div className="p-6 text-slate-500 text-sm">Carregando…</div>
          )}
          {erro && (
            <div className="p-6 text-red-700 text-sm">Falha: {erro}</div>
          )}
          {!loading && !erro && linhas.length === 0 && (
            <div className="p-6 text-slate-500 text-sm">
              Nenhum profissional com bonificação prevista nesta competência.
            </div>
          )}
          {!loading && !erro && linhas.length > 0 && (
            <table className="w-full text-xs">
              <thead className="bg-slate-100 sticky top-0">
                <tr>
                  <th className="px-3 py-2 text-left font-semibold text-slate-600 uppercase">
                    Prestador
                  </th>
                  <th className="px-3 py-2 text-right font-semibold text-slate-600 uppercase">
                    Bonificação
                  </th>
                  <th className="px-3 py-2 text-right font-semibold text-slate-600 uppercase">
                    Receita atrib.
                  </th>
                  <th className="px-3 py-2 text-right font-semibold text-slate-600 uppercase">
                    Margem
                  </th>
                  <th className="px-3 py-2 text-right font-semibold text-slate-600 uppercase">
                    PIX (CNAB)
                  </th>
                  <th className="px-3 py-2 text-left font-semibold text-slate-600 uppercase">
                    Última conf.
                  </th>
                </tr>
              </thead>
              <tbody className="tabular-nums">
                {linhas.map((l) => {
                  const corMargem =
                    l.margem_absoluta >= 0
                      ? "text-emerald-700"
                      : "text-red-700";
                  const pctTxt =
                    l.margem_pct !== null
                      ? ` (${(l.margem_pct * 100).toFixed(1)}%)`
                      : "";
                  return (
                    <tr
                      key={l.prestador_id}
                      className="border-t border-slate-100 hover:bg-slate-50"
                    >
                      <td className="px-3 py-2 font-medium text-slate-900">
                        {l.prestador_nome}
                        <div className="text-[10px] text-slate-500">
                          share {(l.share * 100).toFixed(1)}%
                        </div>
                      </td>
                      <td className="px-3 py-2 text-right text-slate-900">
                        {formatBRL(l.bonificacao)}
                      </td>
                      <td className="px-3 py-2 text-right text-slate-700">
                        {formatBRL(l.receita_atribuida)}
                      </td>
                      <td
                        className={`px-3 py-2 text-right font-semibold ${corMargem}`}
                      >
                        {formatBRL(l.margem_absoluta)}
                        <span className="text-[10px] font-normal opacity-80">
                          {pctTxt}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right text-slate-700">
                        {l.pix_confirmado > 0 ? formatBRL(l.pix_confirmado) : "—"}
                      </td>
                      <td className="px-3 py-2 text-slate-600 text-[11px]">
                        {l.data_ultimo_pix
                          ? formatDataBR(l.data_ultimo_pix)
                          : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}

function Mini({
  label,
  value,
  cor,
}: {
  label: string;
  value: string;
  cor?: string;
}) {
  return (
    <div>
      <div className="text-[9px] uppercase text-slate-500 font-semibold tracking-wide">
        {label}
      </div>
      <div className={`font-bold tabular-nums text-slate-900 ${cor ?? ""}`}>
        {value}
      </div>
    </div>
  );
}

function formatCompetencia(c: string): string {
  const [y, m] = c.split("-");
  return `${m}/${y}`;
}
