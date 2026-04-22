"use client"
import { useEffect, useState } from "react"
import {
  listarContasBancarias,
  criarContaBancaria,
  editarContaBancaria,
  desativarContaBancaria,
  type ContaBancariaOut,
  type FinalidadeConta,
} from "@/lib/api/catalogos"
import { toast } from "sonner"

const BANCOS_COMUNS = ["UNICRED", "BRADESCO", "ITAU", "SISPRIME", "BB"] as const
const FINALIDADES: FinalidadeConta[] = [
  "RECEBIMENTOS",
  "REMESSAS",
  "AVISTA",
  "FIXAS",
  "TRIBUTOS",
]

export function ContasPanel() {
  const [items, setItems] = useState<ContaBancariaOut[]>([])
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState<string | null>(null)
  const [modo, setModo] = useState<"lista" | "nova" | "editar">("lista")
  const [editingId, setEditingId] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const [bancoSelect, setBancoSelect] = useState<string>("BRADESCO")
  const [bancoCustom, setBancoCustom] = useState("")
  const [agencia, setAgencia] = useState("")
  const [conta, setConta] = useState("")
  const [finalidades, setFinalidades] = useState<FinalidadeConta[]>(["RECEBIMENTOS"])

  async function recarregar() {
    setLoading(true)
    setErro(null)
    try {
      const data = await listarContasBancarias()
      setItems(data)
    } catch (e) {
      setErro(e instanceof Error ? e.message : "erro desconhecido")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    recarregar()
  }, [])

  function resetForm() {
    setBancoSelect("BRADESCO")
    setBancoCustom("")
    setAgencia("")
    setConta("")
    setFinalidades(["RECEBIMENTOS"])
    setEditingId(null)
  }

  function toggleFinalidade(f: FinalidadeConta) {
    setFinalidades((atual) =>
      atual.includes(f) ? atual.filter((x) => x !== f) : [...atual, f]
    )
  }

  function startEdit(c: ContaBancariaOut) {
    const bancoInList = BANCOS_COMUNS.some((b) => b === c.banco)
    setBancoSelect(bancoInList ? c.banco : "Outro")
    setBancoCustom(bancoInList ? "" : c.banco)
    setAgencia(c.agencia)
    setConta(c.conta)
    const fins = (c.finalidades && c.finalidades.length > 0
      ? c.finalidades
      : [c.finalidade]) as FinalidadeConta[]
    setFinalidades(fins)
    setEditingId(c.id)
    setModo("editar")
  }

  async function handleSubmit(ev: React.FormEvent) {
    ev.preventDefault()
    const banco = bancoSelect === "Outro" ? bancoCustom.trim() : bancoSelect
    if (!banco || !agencia.trim() || !conta.trim()) {
      toast.error("Preencha banco, agência e conta")
      return
    }
    if (finalidades.length === 0) {
      toast.error("Selecione pelo menos uma finalidade")
      return
    }
    setSubmitting(true)
    try {
      if (modo === "editar" && editingId) {
        await editarContaBancaria(editingId, {
          banco,
          agencia: agencia.trim(),
          conta: conta.trim(),
          finalidades,
        })
        toast.success("Conta atualizada")
      } else {
        await criarContaBancaria({
          banco,
          agencia: agencia.trim(),
          conta: conta.trim(),
          finalidades,
        })
        toast.success("Conta bancária cadastrada")
      }
      resetForm()
      setModo("lista")
      recarregar()
    } catch (e) {
      const msg = e instanceof Error ? e.message : "erro"
      toast.error("Falha: " + msg)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDesativar(c: ContaBancariaOut) {
    const fins = (c.finalidades && c.finalidades.length > 0 ? c.finalidades : [c.finalidade]).join(", ")
    if (!confirm(`Desativar conta ${c.banco} ${c.agencia}/${c.conta} (${fins})?`)) return
    try {
      await desativarContaBancaria(c.id)
      toast.success("Conta desativada")
      recarregar()
    } catch (e) {
      toast.error("Falha: " + (e instanceof Error ? e.message : "erro"))
    }
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500 mb-3">
        Contas que o sistema reconhece ao fazer upload de extratos. Uma conta pode ter múltiplas finalidades (ex: Remessas + Recebimentos + À vista).
      </p>
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">
          {items.length} conta(s) bancária(s)
        </h2>
        <button
          onClick={() => {
            if (modo === "lista") {
              resetForm()
              setModo("nova")
            } else {
              resetForm()
              setModo("lista")
            }
          }}
          className="text-xs px-3 py-1 rounded bg-slate-900 text-white"
        >
          {modo === "lista" ? "+ Nova conta" : "Cancelar"}
        </button>
      </div>

      {(modo === "nova" || modo === "editar") && (
        <form
          onSubmit={handleSubmit}
          className="bg-white border border-slate-200 rounded-lg p-4 space-y-3"
        >
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <label className="text-[10px] text-slate-500 uppercase block mb-1">Banco</label>
              <select
                value={bancoSelect}
                onChange={(e) => setBancoSelect(e.target.value)}
                className="w-full border border-slate-300 rounded px-2 py-1 text-sm"
              >
                {BANCOS_COMUNS.map((b) => (
                  <option key={b} value={b}>{b}</option>
                ))}
                <option value="Outro">Outro…</option>
              </select>
            </div>
            {bancoSelect === "Outro" && (
              <div>
                <label className="text-[10px] text-slate-500 uppercase block mb-1">Banco (nome)</label>
                <input
                  value={bancoCustom}
                  onChange={(e) => setBancoCustom(e.target.value)}
                  placeholder="Ex: SANTANDER"
                  className="w-full border border-slate-300 rounded px-2 py-1 text-sm uppercase"
                />
              </div>
            )}
            <div>
              <label className="text-[10px] text-slate-500 uppercase block mb-1">Agência</label>
              <input
                value={agencia}
                onChange={(e) => setAgencia(e.target.value)}
                placeholder="0560"
                className="w-full border border-slate-300 rounded px-2 py-1 text-sm tabular-nums"
              />
            </div>
            <div>
              <label className="text-[10px] text-slate-500 uppercase block mb-1">Conta</label>
              <input
                value={conta}
                onChange={(e) => setConta(e.target.value)}
                placeholder="22982"
                className="w-full border border-slate-300 rounded px-2 py-1 text-sm tabular-nums"
              />
            </div>
          </div>

          <div>
            <label className="text-[10px] text-slate-500 uppercase block mb-1">Finalidades (selecione uma ou mais)</label>
            <div className="flex flex-wrap gap-2">
              {FINALIDADES.map((f) => {
                const selected = finalidades.includes(f)
                return (
                  <label
                    key={f}
                    className={`cursor-pointer text-xs font-semibold uppercase px-2.5 py-1 rounded-full border-2 transition ${
                      selected
                        ? "bg-emerald-600 border-emerald-600 text-white"
                        : "bg-white border-slate-300 text-slate-600 hover:border-slate-400"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selected}
                      onChange={() => toggleFinalidade(f)}
                      className="hidden"
                    />
                    {f}
                  </label>
                )
              })}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">
              Clique nas tags para selecionar. Obrigatório pelo menos 1.
            </p>
          </div>

          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={() => { resetForm(); setModo("lista") }}
              className="px-3 py-1 text-sm rounded border border-slate-300"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-3 py-1 text-sm rounded bg-emerald-600 text-white disabled:opacity-50"
            >
              {submitting ? "Salvando…" : modo === "editar" ? "Salvar" : "Criar"}
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="text-sm text-slate-500">Carregando…</p>
      ) : erro ? (
        <p className="text-sm text-red-600">Erro: {erro}</p>
      ) : (
        <div className="bg-white border border-slate-200 rounded-lg overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-100">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 uppercase">Banco</th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 uppercase">Agência</th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 uppercase">Conta</th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 uppercase">Finalidades</th>
                <th className="px-3 py-2 text-center text-xs font-semibold text-slate-600 uppercase">Ativo</th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-slate-600 uppercase">Ação</th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => {
                const fins = c.finalidades && c.finalidades.length > 0 ? c.finalidades : [c.finalidade]
                return (
                  <tr key={c.id} className="border-t border-slate-100">
                    <td className="px-3 py-2 text-slate-900 font-medium">{c.banco}</td>
                    <td className="px-3 py-2 text-slate-700 tabular-nums">{c.agencia}</td>
                    <td className="px-3 py-2 text-slate-700 tabular-nums">{c.conta}</td>
                    <td className="px-3 py-2 text-slate-700">
                      <div className="flex flex-wrap gap-1">
                        {fins.map((f) => (
                          <span key={f} className="inline-block text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-semibold uppercase">
                            {f}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-center">
                      <span className={`text-[10px] px-2 py-0.5 rounded font-semibold uppercase ${c.ativo ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-500"}`}>
                        {c.ativo ? "Sim" : "Não"}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right space-x-3">
                      <button
                        onClick={() => startEdit(c)}
                        className="text-xs text-sky-600 hover:underline"
                        title="Editar"
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => handleDesativar(c)}
                        className="text-xs text-red-600 hover:underline"
                        title="Desativar (soft delete)"
                      >
                        Desativar
                      </button>
                    </td>
                  </tr>
                )
              })}
              {items.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 py-6 text-center text-sm text-slate-500">
                    Nenhuma conta bancária cadastrada.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
