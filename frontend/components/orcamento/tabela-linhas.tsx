"use client";
import { memo } from "react";
import type { OrcamentoLinhaOut, CategoriaOut, ProjetoOut } from "@/types/v2";
import { BOLSO_LABELS, BOLSO_CORES } from "@/types/v2";
import { formatBRL } from "@/lib/format";

// Status derivado de valor_previsto vs soma de conciliacoes — nesta tela, por
// simplicidade, mostramos PREV sempre (o backend nao retorna o pago/saldo por
// linha ainda; refinar depois via conciliacao_orcamento.valor_aplicado).
interface Props {
  linhas: OrcamentoLinhaOut[];
  categoriaPorId?: Record<string, CategoriaOut>;
  projetoPorId?: Record<string, ProjetoOut>;
  onRowClick?: (linha: OrcamentoLinhaOut) => void;
  /** Mapa empresa_id → codigo (ex: "FD", "SPM"). Usado pra renderizar badge. */
  empresaCodigoPorId?: Record<string, string>;
  /** Empresa do orçamento atual. Se empresa_pagadora = essa, badge é redundante e some. */
  empresaOrcamentoId?: string;
  /** Mapa contrato_id → rótulo curto (ex: "PR-BANDEIRANTES"). Usado na coluna Contrato. */
  contratoRotuloPorId?: Record<string, string>;
}

function TabelaLinhasImpl({
  linhas,
  categoriaPorId,
  projetoPorId,
  onRowClick,
  empresaCodigoPorId,
  empresaOrcamentoId,
  contratoRotuloPorId,
}: Props) {
  if (!linhas.length) {
    return (
      <div className="p-6 text-slate-500 text-sm bg-white">
        Nenhuma linha nesta seção.
      </div>
    );
  }

  return (
    <div className="bg-white overflow-x-auto">
      <table className="w-full text-xs">
        <thead className="bg-slate-100">
          <tr>
            <th className="px-3 py-2 text-left font-semibold text-slate-600 uppercase">
              Razão Social / Descrição
            </th>
            <th className="px-3 py-2 text-left font-semibold text-slate-600 uppercase">
              Bolso
            </th>
            <th className="px-3 py-2 text-left font-semibold text-slate-600 uppercase">
              Categoria
            </th>
            <th className="px-3 py-2 text-left font-semibold text-slate-600 uppercase">
              Projeto
            </th>
            <th className="px-3 py-2 text-left font-semibold text-slate-600 uppercase">
              Contrato
            </th>
            <th className="px-3 py-2 text-right font-semibold text-slate-600 uppercase">
              Previsto
            </th>
            <th className="px-3 py-2 text-right font-semibold text-slate-600 uppercase">
              Pago
            </th>
            <th className="px-3 py-2 text-right font-semibold text-slate-600 uppercase">
              Saldo
            </th>
            <th className="px-3 py-2 text-left font-semibold text-slate-600 uppercase">
              Data PIX
            </th>
            <th className="px-3 py-2 text-center font-semibold text-slate-600 uppercase">
              Status
            </th>
            <th className="px-3 py-2 text-left font-semibold text-slate-600 uppercase">
              Obs.
            </th>
          </tr>
        </thead>
        <tbody>
          {linhas.map((l) => {
            const cat = l.categoria_id ? categoriaPorId?.[l.categoria_id] : null;
            const proj = l.projeto_id ? projetoPorId?.[l.projeto_id] : null;
            return (
              <tr
                key={l.id}
                className={
                  "border-t border-slate-100 hover:bg-slate-50" +
                  (onRowClick ? " cursor-pointer" : "")
                }
                onClick={onRowClick ? () => onRowClick(l) : undefined}
                title={onRowClick ? "Clique para editar" : undefined}
              >
                <td className="px-3 py-2 font-medium text-slate-900">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span>{l.titular_razao_social}</span>
                    {l.empresa_pagadora_id &&
                      l.empresa_pagadora_id !== empresaOrcamentoId && (
                        <span
                          className="inline-block px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-100 text-amber-800"
                          title={`Pago via ${empresaCodigoPorId?.[l.empresa_pagadora_id] ?? "empresa do grupo"} (empresa pagadora distinta)`}
                        >
                          {empresaCodigoPorId?.[l.empresa_pagadora_id] ?? "?"}
                        </span>
                      )}
                  </div>
                  {l.titular_cpf_cnpj && (
                    <div className="text-[10px] text-slate-500">
                      {l.titular_cpf_cnpj}
                    </div>
                  )}
                </td>
                <td className="px-3 py-2">
                  {l.bolso ? (
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold ${BOLSO_CORES[l.bolso]}`}
                    >
                      {BOLSO_LABELS[l.bolso]}
                    </span>
                  ) : (
                    <span className="text-slate-400 text-[10px]">—</span>
                  )}
                </td>
                <td className="px-3 py-2 text-slate-700">
                  {cat ? cat.nome : "—"}
                </td>
                <td className="px-3 py-2 text-slate-700">
                  {proj ? proj.codigo : "—"}
                </td>
                <td className="px-3 py-2 text-slate-700">
                  {l.contrato_id && contratoRotuloPorId?.[l.contrato_id] ? (
                    <span
                      className="inline-block px-1.5 py-0.5 rounded text-[10px] bg-sky-100 text-sky-800 font-medium"
                      title="Contrato vinculado — despesa atrelada a este contrato"
                    >
                      {contratoRotuloPorId[l.contrato_id]}
                    </span>
                  ) : (
                    <span className="text-slate-400 text-[10px]">—</span>
                  )}
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-slate-900">
                  {formatBRL(l.valor_previsto)}
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-slate-500">
                  —
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-slate-900">
                  {formatBRL(l.valor_previsto)}
                </td>
                <td className="px-3 py-2 text-slate-600 text-xs">
                  {l.data_previsao ?? "—"}
                </td>
                <td className="px-3 py-2 text-center">
                  <span className="text-[10px] px-2 py-0.5 rounded font-semibold uppercase bg-slate-100 text-slate-600">
                    PREV
                  </span>
                </td>
                <td
                  className="px-3 py-2 text-slate-500 text-xs max-w-[200px] truncate"
                  title={l.observacao ?? ""}
                >
                  {l.observacao ?? ""}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// Memoizado para nao re-renderizar quando estados externos (ex.: uploadOpen)
// mudam na page.tsx. Evita "trava" ao abrir o dialog de upload com muitas linhas.
export const TabelaLinhas = memo(TabelaLinhasImpl);
