"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Upload, FileText, X } from "lucide-react"
import { toast } from "sonner"
import { AxiosError } from "axios"

import { criarRodada, conciliarRodada } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"

type Etapa = "idle" | "uploading" | "conciliating" | "done"

export function UploadForm() {
  const router = useRouter()
  const [ppArquivos, setPpArquivos] = useState<File[]>([])
  const [ofx, setOfx] = useState<File | null>(null)
  const [inicio, setInicio] = useState<string>("")
  const [fim, setFim] = useState<string>("")
  const [etapa, setEtapa] = useState<Etapa>("idle")

  function removePP(i: number) {
    setPpArquivos((prev) => prev.filter((_, idx) => idx !== i))
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (ppArquivos.length === 0) return toast.error("Selecione ao menos 1 arquivo PP (XLSX)")
    if (!ofx) return toast.error("Selecione o extrato OFX")
    if (!inicio || !fim) return toast.error("Informe o periodo do extrato")
    if (new Date(fim) < new Date(inicio)) return toast.error("Fim anterior ao inicio")

    try {
      setEtapa("uploading")
      const fd = new FormData()
      ppArquivos.forEach((f) => fd.append("pp_arquivos", f))
      fd.append("extrato_ofx", ofx)
      fd.append("periodo_extrato_inicio", inicio)
      fd.append("periodo_extrato_fim", fim)

      const upload = await criarRodada(fd)
      toast.success(`Rodada criada: ${upload.total_registros_pp} registros PP + ${upload.total_transacoes} transacoes`)

      setEtapa("conciliating")
      const conc = await conciliarRodada(upload.rodada_id)
      toast.success(`Conciliacao: ${conc.percentual_conciliado.toFixed(2)}% endereçado`)

      setEtapa("done")
      router.push(`/rodadas/${upload.rodada_id}`)
    } catch (err) {
      const ax = err as AxiosError<{ error?: string }>
      const msg = ax.response?.data?.error || ax.message || "Falha no processo"
      toast.error(msg)
      setEtapa("idle")
    }
  }

  const processando = etapa === "uploading" || etapa === "conciliating"
  const mensagemEtapa =
    etapa === "uploading" ? "Enviando arquivos e parseando..."
      : etapa === "conciliating" ? "Rodando motor de conciliacao..."
      : ""

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Arquivos da rodada</CardTitle>
          <CardDescription>
            PP XLSX (1 ou mais, mesmo competencia ou competencias diferentes) + OFX Bradesco.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="pp">PP XLSX (multiplo)</Label>
            <Input
              id="pp"
              type="file"
              accept=".xlsx"
              multiple
              disabled={processando}
              onChange={(e) => {
                const files = Array.from(e.target.files || [])
                setPpArquivos((prev) => [...prev, ...files])
              }}
            />
            {ppArquivos.length > 0 && (
              <div className="text-sm space-y-1 mt-2">
                {ppArquivos.map((f, i) => (
                  <div key={i} className="flex items-center justify-between gap-2 rounded border px-3 py-1.5">
                    <div className="flex items-center gap-2 min-w-0">
                      <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                      <span className="truncate">{f.name}</span>
                      <span className="text-xs text-muted-foreground">({(f.size / 1024).toFixed(0)} KB)</span>
                    </div>
                    <button
                      type="button"
                      className="text-muted-foreground hover:text-foreground"
                      onClick={() => removePP(i)}
                      disabled={processando}
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="ofx">Extrato OFX (Bradesco)</Label>
            <Input
              id="ofx"
              type="file"
              accept=".ofx"
              disabled={processando}
              onChange={(e) => setOfx(e.target.files?.[0] || null)}
            />
            {ofx && <div className="text-sm text-muted-foreground">{ofx.name} ({(ofx.size / 1024).toFixed(0)} KB)</div>}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="inicio">Inicio do extrato</Label>
              <Input id="inicio" type="date" value={inicio} disabled={processando} onChange={(e) => setInicio(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="fim">Fim do extrato</Label>
              <Input id="fim" type="date" value={fim} disabled={processando} onChange={(e) => setFim(e.target.value)} />
            </div>
          </div>
        </CardContent>
      </Card>

      {processando && (
        <Alert>
          <Upload className="h-4 w-4" />
          <AlertDescription>
            {mensagemEtapa} Pode levar 2-3 minutos. Nao feche a aba.
          </AlertDescription>
        </Alert>
      )}

      <div className="flex gap-2">
        <Button type="submit" disabled={processando}>
          {etapa === "uploading" ? "Enviando..." : etapa === "conciliating" ? "Conciliando..." : "Enviar e conciliar"}
        </Button>
        <Button type="button" variant="outline" disabled={processando} onClick={() => router.push("/rodadas")}>
          Cancelar
        </Button>
      </div>
    </form>
  )
}
