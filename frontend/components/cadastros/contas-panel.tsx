"use client";
import { useEffect, useState } from "react";
import {
  listarContasBancarias,
  criarContaBancaria,
  desativarContaBancaria,
  type ContaBancariaOut,
  type FinalidadeConta,
} from "@/lib/api/catalogos";
import { toast } from "sonner";

const BANCOS_COMUNS = ["UNICRED", "BRADESCO", "ITAU", "SISPRIME", "BB"] as const;
const FINALIDADES: FinalidadeConta[] = [
  "RECEBIMENTOS",
  "REMESSAS",
  "AVISTA",
  "FIXAS",
  "TRIBUTOS",
];

export function ContasPanel() {
  const [items, setItems] = useState<ContaBancariaOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [mostrarForm, setMostrarForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [bancoSelect, setBancoSelect] = useState<string>("UNICRED");
  const [bancoCustom, setBancoCustom] = useState("");
  const [agencia, setAgencia] = useState("");
  const [conta, setConta] = useState("");
  const [finalidade, setFinalidade] = useState<FinalidadeConta>("RECEBIMENTOS");

  async function recarregar() {
    setLoading(true);
    setErro(null);
    try {
      const data = await listarContasBancarias();
      setItems(data);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "erro desconhecido");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    recarregar();
  }, []);

  function resetForm() {
    setBancoSelect("UNICRED");
    setBancoCustom("");
    setAgencia("");
    setConta("");
    setFinalidade("RECEBIMENTOS");
  }

  async function handleCriar(ev: React.FormEvent) {
    ev.preventDefault();
    const banco = bancoSelect === "Outro" ? bancoCustom.trim() : bancoSelect;
    if (!banco || !agencia.trim() || !conta.trim()) {
      toast.error("Preencha banco, agencia e conta");
      return;
    }
    setSubmitting(true);
    try {
      await criarContaBancaria({
        banco,
        agencia: agencia.trim(),
        conta: conta.trim(),
        finalidade,
      });
      toast.success("Conta bancaria cadastrada");
      resetForm();
      setMostrarForm(false);
      recarregar();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "erro";
      toast.error("Falha: " + msg);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDesativar(c: ContaBancariaOut) {
    if (
      !confirm(
        `Desativar conta ${c.banco} ${c.agencia}/${c.conta} (${c.finalidade})?`,
      )
    )
      return;
    try {
      await desativarContaBancaria(c.id);
      toast.success("Conta desativada");
      recarregar();
    } catch (e) {
      toast.error("Falha: " + (e instanceof Error ? e.message : "erro"));
    }
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500 mb-3">
        Contas que o sistema reconhece ao fazer upload de extratos. Precisa cadastrar antes de subir Unicred PDF ou Bradesco OFX.
      </p>
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">
          {items.length} conta(s) bancaria(s)
        </h2>
        <button
          onClick={() => setMostrarForm(!mostrarForm)}
          className="text-xs px-3 py-1 rounded bg-slate-900 text-white"
        >
          {mostrarForm ? "Cancelar" : "+ Nova conta"}
        </button>
      </div>
      {mostrarForm && (
        <form
          onSubmit={handleCriar}
          className="bg-white border border-slate-200 rounded-lg p-3 space-y-2 flex flex-wrap gap-2 items-end"
        >
          <div className="flex-1 min-w-[160px]">
            <label className="text-[10px] text-slate-500 uppercase block">
              Banco
            </label>
            <select
              value={bancoSelect}
              onChange={(e) => setBancoSelect(e.target.value)}
              className="w-full border border-slate-300 rounded px-2 py-1 text-sm"
            >
              {BANCOS_COMUNS.map((b) => (
                <option key={b} value={b}>
                  {b}
                </option>
              ))}
              <option value="Outro">Outro...</option>
            </select>
          </div>
          {bancoSelect === "Outro" && (
            <div className="flex-1 min-w-[160px]">
              <label className="text-[10px] text-slate-500 uppercase block">
                Banco (nome)
              </label>
              <input
                value={bancoCustom}
                onChange={(e) => setBancoCustom(e.target.value)}
                placeholder="Ex: SANTANDER"
                className="w-full border border-slate-300 rounded px-2 py-1 text-sm uppercase"
              />
            </div>
          )}
          <div className="flex-1 min-w-[100px]">
            <label className="text-[10px] text-slate-500 uppercase block">
              Agencia
            </label>
            <input
              value={agencia}
              onChange={(e) => setAgencia(e.target.value)}
              placeholder="0001"
              className="w-full border border-slate-300 rounded px-2 py-1 text-sm tabular-nums"
            />
          </div>
          <div className="flex-1 min-w-[120px]">
            <label className="text-[10px] text-slate-500 uppercase block">
              Conta
            </label>
            <input
              value={conta}
              onChange={(e) => setConta(e.target.value)}
              placeholder="12345-6"
              className="w-full border border-slate-300 rounded px-2 py-1 text-sm tabular-nums"
            />
          </div>
          <div className="flex-1 min-w-[150px]">
            <label className="text-[10px] text-slate-500 uppercase block">
              Finalidade
            </label>
            <select
              value={finalidade}
              onChange={(e) =>
                setFinalidade(e.target.value as FinalidadeConta)
              }
              className="w-full border border-slate-300 rounded px-2 py-1 text-sm"
            >
              {FINALIDADES.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="px-3 py-1 text-sm rounded bg-emerald-600 text-white disabled:opacity-50"
          >
            {submitting ? "Criando..." : "Criar"}
          </button>
        </form>
      )}
      {loading ? (
        <p className="text-sm text-slate-500">Carregando...</p>
      ) : erro ? (
        <p className="text-sm text-red-600">Erro: {erro}</p>
      ) : (
        <div className="bg-white border border-slate-200 rounded-lg overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-100">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 uppercase">
                  Banco
                </th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 uppercase">
                  Agencia
                </th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 uppercase">
                  Conta
                </th>
                <th className="px-3 py-2 text-left text-xs font-semibold text-slate-600 uppercase">
                  Finalidade
                </th>
                <th className="px-3 py-2 text-center text-xs font-semibold text-slate-600 uppercase">
                  Ativo
                </th>
                <th className="px-3 py-2 text-right text-xs font-semibold text-slate-600 uppercase">
                  Acao
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((c) => (
                <tr key={c.id} className="border-t border-slate-100">
                  <td className="px-3 py-2 text-slate-900 font-medium">
                    {c.banco}
                  </td>
                  <td className="px-3 py-2 text-slate-700 tabular-nums">
                    {c.agencia}
                  </td>
                  <td className="px-3 py-2 text-slate-700 tabular-nums">
                    {c.conta}
                  </td>
                  <td className="px-3 py-2 text-slate-700">{c.finalidade}</td>
                  <td className="px-3 py-2 text-center">
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-semibold uppercase ${
                        c.ativo
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {c.ativo ? "Sim" : "Nao"}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      onClick={() => handleDesativar(c)}
                      className="text-xs text-red-600 hover:underline"
                      title="Desativar (soft delete)"
                    >
                      Desativar
                    </button>
                  </td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-3 py-6 text-center text-sm text-slate-500"
                  >
                    Nenhuma conta bancaria cadastrada.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
