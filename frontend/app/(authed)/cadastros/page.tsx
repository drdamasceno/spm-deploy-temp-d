"use client";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { ProjetosPanel } from "@/components/cadastros/projetos-panel";
import { CategoriasPanel } from "@/components/cadastros/categorias-panel";
import { ContasPanel } from "@/components/cadastros/contas-panel";
import { RegrasPanel } from "@/components/cadastros/regras-panel";
import { TabsEntidades } from "@/components/cadastros/tabs-entidades";

type TabKey = "projetos" | "categorias" | "contas" | "regras";

const TABS: { key: TabKey; label: string }[] = [
  { key: "projetos", label: "Projetos" },
  { key: "categorias", label: "Categorias" },
  { key: "contas", label: "Contas Bancarias" },
  { key: "regras", label: "Regras de Classificacao" },
];

function isTabKey(v: string | null): v is TabKey {
  return v === "projetos" || v === "categorias" || v === "contas" || v === "regras";
}

function CadastrosInner() {
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab");
  const initialTab: TabKey = isTabKey(tabParam) ? tabParam : "projetos";
  const [tab, setTab] = useState<TabKey>(initialTab);

  return (
    <div className="flex flex-col">
      <div className="bg-white border-b border-slate-200 px-4 pt-4">
        <h1 className="text-lg font-semibold text-slate-900 mb-3">Cadastros</h1>
        <p className="text-sm text-slate-600 mb-3 max-w-3xl">
          Metadados do sistema que outras telas referenciam. Raramente voce vai aqui —
          acesse quando precisar cadastrar um novo projeto para o orcamento usar,
          adicionar uma conta bancaria antes de fazer upload de extrato,
          ou desativar uma regra de classificacao que esta sugerindo match errado.
        </p>
        <TabsEntidades tabs={TABS} atual={tab} onChange={setTab} />
      </div>

      <div className="p-6">
        {tab === "projetos" && <ProjetosPanel />}
        {tab === "categorias" && <CategoriasPanel />}
        {tab === "contas" && <ContasPanel />}
        {tab === "regras" && <RegrasPanel />}
      </div>
    </div>
  );
}

export default function CadastrosPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-slate-500">Carregando...</div>}>
      <CadastrosInner />
    </Suspense>
  );
}
