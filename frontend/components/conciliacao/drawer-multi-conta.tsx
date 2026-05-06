"use client";
import { useEffect, useState, useMemo } from "react";
import {
  getConciliacoesDaLinha,
  type ConciliacaoDetalhe,
} from "@/lib/api/margem";
import type { OrcamentoLinhaOut } from "@/types/v2";
import { formatBRL, formatDataBR } from "@/lib/format";

/**
 * Drawer multi-conta de conciliação. Mostra todas as transações conciliadas
 * a uma linha de orçamento, com chips por conta (Bradesco/Unicred) e filtro
 * client-side. Substitui o clique direto no LinhaEditorModal — modal de
 * edição de campos da linha vira ação secundária dentro do drawer.
 *
 * Premissa de Hugo (2026-05-06): todas as saídas migram pra Unicred.
 * Bradesco-Recebimentos continua sendo fonte de receita pra aba Faturamento.
 */
interface Props {
  linha: OrcamentoLinhaOut | null; // null = drawer fechado
  onClose: () => void;
  /** Callback opcional pra abrir o modal de edição (ação secundária). */
  onEditar?: (linha: OrcamentoLinhaOut) => void;
}

const BANCO_LABELS: Record<string, string> = {
  BRADESCO: "Bradesco",
  UNICRED: "Unicred",
};
const BANCO_CORES: Record<string, string> = {
  BRADESCO: "bg-emerald-100 text-emerald-800",
  UNICRED: "bg-slate-200 text-slate-800",
};

export function DrawerMultiConta({ linha, onClose, onEditar }: Props) {
  const [conciliacoes, setConciliacoes] = useState<ConciliacaoDetalhe[]>([]);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [filtroBanco, setFiltroBanco] = useState<string>("TODOS");

  useEffect(() => {
    if (!linha) {
      setConciliacoes([]);
      setFiltroBanco("TODOS");
      return;
    }
    setLoading(true);
    setErro(null);
    getConciliacoesDaLinha(linha.id)
      .then(setConciliacoes)
      .catch((e: unknown) =>
        setErro(e instanceof Error ? e.message : "erro ao carregar conciliações")
      )
      .finally(() => setLoading(false));
  }, [linha]);

  const aberto = linha !== null;

  const bancosPresentes = useMemo(() => {
    const set = new Set<string>();
    for (const c of conciliacoes) set.add(c.origem_banco);
    return Array.from(set).sort();
  }, [conciliacoes]);

  const conciliacoesFiltradas = useMemo(() => {
    if (filtroBanco === "TODOS") return conciliacoes;
    return conciliacoes.filter((c) => c.origem_banco === filtroBanco);
  }, [conciliacoes, filtroBanco]);

  const totalAplicado = conciliacoesFiltradas.reduce(
    (s, c) => s + c.valor_aplicado,
    0
  );

  const previsto = linha?.valor_previsto ?? 0;
  const saldoLinha = previsto - totalAplicado;

  return (
    <>
      <div
        onClick={onClose}
        className={
          "fixed inset-0 bg-black/30 z-40 transition-opacity " +
          (aberto ? "opacity-100" : "opacity-0 pointer-events-none")
        }
      />
      <div
        className={
          "fixed inset-y-0 right-0 w-[600px] bg-white border-l border-slate-200 shadow-2xl z-50 flex flex-col transition-transform duration-200 " +
          (aberto ? "translate-x-0" : "translate-x-full")
        }
      >
        <div className="bg-slate-900 text-white px-4 py-3 flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-sm">
              Conciliação · {linha?.titular_razao_social ?? ""}
            </h3>
            <div className="text-[11px] text-slate-400 mt-0.5">
              {linha?.natureza ?? ""}
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

        {/* resumo da linha */}
        <div className="bg-slate-50 border-b border-slate-200 px-4 py-3 grid grid-cols-3 gap-2 text-[11px]">
          <Mini label="Previsto" value={formatBRL(previsto)} />
          <Mini label="Conciliado" value={formatBRL(totalAplicado)} />
          <Mini
            label="Saldo"
            value={formatBRL(saldoLinha)}
            cor={saldoLinha >= -0.01 ? "text-emerald-700" : "text-red-700"}
          />
        </div>

        {/* chips de banco + ação editar */}
        <div className="bg-white border-b border-slate-200 px-3 py-2 flex items-center justify-between gap-2 text-xs">
          <div className="flex gap-1">
            <ChipFiltro
              label={`Todos (${conciliacoes.length})`}
              ativo={filtroBanco === "TODOS"}
              onClick={() => setFiltroBanco("TODOS")}
            />
            {bancosPresentes.map((b) => (
              <ChipFiltro
                key={b}
                label={`${BANCO_LABELS[b] ?? b} (${conciliacoes.filter((c) => c.origem_banco === b).length})`}
                ativo={filtroBanco === b}
                onClick={() => setFiltroBanco(b)}
                cor={BANCO_CORES[b]}
              />
            ))}
          </div>
          {linha && onEditar && (
            <button
              onClick={() => onEditar(linha)}
              className="px-2 py-1 text-[10px] rounded border border-slate-300 bg-white hover:bg-slate-50"
              title="Abrir modal de edição da linha"
            >
              Editar dados da linha
            </button>
          )}
        </div>

        {/* lista de conciliações */}
        <div className="flex-1 overflow-y-auto">
          {loading && (
            <div className="p-6 text-slate-500 text-sm">Carregando…</div>
          )}
          {erro && (
            <div className="p-6 text-red-700 text-sm">Falha: {erro}</div>
          )}
          {!loading && !erro && conciliacoes.length === 0 && (
            <div className="p-6 text-slate-500 text-sm">
              Nenhuma transação conciliada com esta linha ainda.
            </div>
          )}
          {!loading && !erro && conciliacoesFiltradas.length === 0 && conciliacoes.length > 0 && (
            <div className="p-6 text-slate-500 text-sm">
              Nenhuma conciliação no banco selecionado.
            </div>
          )}
          {!loading && !erro && conciliacoesFiltradas.length > 0 && (
            <div>
              <div className="px-3 py-1.5 bg-slate-100 text-[9px] uppercase tracking-wide text-slate-600 font-semibold flex justify-between border-b border-slate-200">
                <span>Lançamento</span>
                <span>Banco · Origem</span>
              </div>
              {conciliacoesFiltradas.map((c) => (
                <div
                  key={c.conciliacao_id}
                  className="px-3 py-2.5 border-b border-slate-100 hover:bg-slate-50 flex items-start gap-2.5"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="text-xs font-medium text-slate-900 truncate">
                        {c.titular_pix ?? c.descricao_tx ?? "(sem descrição)"}
                      </span>
                      <span className="text-xs tabular-nums font-semibold text-slate-900">
                        {formatBRL(c.valor_aplicado)}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                      <span className="text-[10px] text-slate-500">
                        {formatDataBR(c.data_extrato)}
                      </span>
                      <span
                        className={
                          "text-[9px] px-1.5 py-0.5 rounded font-semibold " +
                          (BANCO_CORES[c.origem_banco] ?? "bg-slate-100 text-slate-700")
                        }
                      >
                        {BANCO_LABELS[c.origem_banco] ?? c.origem_banco}
                      </span>
                      {c.origem && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded font-semibold bg-slate-100 text-slate-600">
                          {c.origem}
                        </span>
                      )}
                      {c.natureza_lancamento && (
                        <span className="text-[10px] text-slate-400">
                          {c.natureza_lancamento}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
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

function ChipFiltro({
  label,
  ativo,
  onClick,
  cor,
}: {
  label: string;
  ativo: boolean;
  onClick: () => void;
  cor?: string;
}) {
  if (ativo) {
    return (
      <button
        onClick={onClick}
        className="px-2 py-0.5 rounded font-medium bg-slate-900 text-white text-[10px]"
      >
        {label}
      </button>
    );
  }
  return (
    <button
      onClick={onClick}
      className={
        "px-2 py-0.5 rounded font-medium border border-slate-200 text-[10px] hover:bg-slate-50 " +
        (cor ?? "bg-white text-slate-700")
      }
    >
      {label}
    </button>
  );
}
