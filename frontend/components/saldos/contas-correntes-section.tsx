"use client"
import { useState } from "react"
import type { ContaLiquidezItem } from "@/types/v2"
import { formatBRL } from "@/lib/format"
import { registrarSaldoManual } from "@/lib/api/saldos"
import { InputDinheiro } from "@/components/ui/input-dinheiro"
import { toast } from "sonner"

interface Props {
  contas: ContaLiquidezItem[]
  onUpdated: () => void
}

export function ContasCorrentesSection({ contas, onUpdated }: Props) {
  const [editando, setEditando] = useState<string | null>(null)
  const [valor, setValor] = useState<number>(0)
  const [data, setData] = useState("")
  const [saving, setSaving] = useState(false)

  async function handleSalvar(conta: ContaLiquidezItem) {
    setSaving(true)
    try {
      if (!Number.isFinite(valor)) {
        toast.error("Valor inválido")
        setSaving(false)
        return
      }
      await registrarSaldoManual({
        conta_bancaria_id: conta.conta_id,
        saldo_valor: valor,
        data_referencia: data || new Date().toISOString().slice(0, 10),
      })
      toast.success("Saldo atualizado")
      setEditando(null)
      setValor(0)
      setData("")
      onUpdated()
    } catch (e) {
      toast.error("Falha: " + (e instanceof Error ? e.message : "erro"))
    } finally {
      setSaving(false)
    }
  }

  const temDesatualizada = contas.some(c => c.dias_desatualizado !== null && c.dias_desatualizado > 7)

  return (
    <div className="bg-white p-4 space-y-2">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-[3px] h-4 rounded" style={{ background: "#0ea5e9" }} />
        <h3 className="text-xs font-bold uppercase tracking-wide text-slate-900">Contas correntes</h3>
        <span className="ml-auto text-[10px] text-slate-500">auto via extrato</span>
      </div>

      {contas.length === 0 ? (
        <div className="text-xs text-slate-500 py-4 text-center">Nenhuma conta cadastrada.</div>
      ) : (
        contas.map(c => (
          <div key={c.conta_id} className="p-2.5 border border-slate-200 rounded flex items-center gap-2.5">
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold text-slate-900">
                {c.banco} · Ag {c.agencia} / CC {c.conta}
              </div>
              <div className="text-[11px] mt-0.5">
                <span className="text-slate-500">{c.finalidade}</span>
                {" · "}
                {c.dias_desatualizado === null ? (
                  <span className="text-amber-700">Sem histórico ainda</span>
                ) : c.dias_desatualizado > 7 ? (
                  <span className="text-amber-700 font-medium">
                    ⚠ atualizado em {formatDataCurta(c.data_referencia)} ({c.dias_desatualizado} dias atrás)
                  </span>
                ) : (
                  <span className="text-emerald-700 font-medium">
                    ● atualizado em {formatDataCurta(c.data_referencia)} ({c.dias_desatualizado} {c.dias_desatualizado === 1 ? "dia" : "dias"} atrás)
                  </span>
                )}
              </div>
            </div>
            <div className="text-[15px] font-bold tabular-nums text-slate-900">{formatBRL(c.saldo_valor)}</div>
            <button
              onClick={() => {
                setEditando(c.conta_id)
                setValor(c.saldo_valor)
                setData(new Date().toISOString().slice(0, 10))
              }}
              className="text-[11px] text-sky-600 hover:text-sky-800 bg-transparent border-0 cursor-pointer font-medium"
            >
              Atualizar
            </button>
          </div>
        ))
      )}

      {editando && (
        <div className="mt-3 p-3 border-2 border-sky-300 rounded bg-sky-50 space-y-2">
          <div className="text-xs font-semibold text-sky-900 uppercase tracking-wide">Atualizar saldo manualmente</div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-slate-600 block">Novo saldo</label>
              <InputDinheiro value={valor} onChange={setValor} />
            </div>
            <div>
              <label className="text-[10px] text-slate-600 block">Data de referência</label>
              <input
                type="date"
                value={data}
                onChange={e => setData(e.target.value)}
                className="w-full border border-slate-300 rounded px-2 py-1 text-sm"
              />
            </div>
          </div>
          <div className="flex gap-2 justify-end">
            <button
              onClick={() => setEditando(null)}
              className="text-xs px-3 py-1 border border-slate-300 rounded bg-white"
            >
              Cancelar
            </button>
            <button
              onClick={() => {
                const conta = contas.find(c => c.conta_id === editando)
                if (conta) handleSalvar(conta)
              }}
              disabled={saving}
              className="text-xs px-3 py-1 bg-sky-600 text-white rounded disabled:opacity-50"
            >
              {saving ? "Salvando…" : "Salvar"}
            </button>
          </div>
        </div>
      )}

      {temDesatualizada && !editando && (
        <div className="mt-2 p-2 bg-amber-100 rounded text-[11px] text-amber-900 flex items-start gap-1.5">
          <span>⚠</span>
          <span>Uma ou mais contas estão desatualizadas há mais de 7 dias. Clica "Atualizar" ou sobe extrato novo.</span>
        </div>
      )}
    </div>
  )
}

function formatDataCurta(s: string | null): string {
  if (!s) return "—"
  const [y, m, d] = s.split("-")
  return `${d}/${m}/${y.slice(2)}`
}
