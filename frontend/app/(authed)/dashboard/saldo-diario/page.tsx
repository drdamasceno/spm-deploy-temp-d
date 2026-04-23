import { StubEmConstrucao } from "@/components/ui/stub-em-construcao"

export default function SaldoDiarioPage() {
  return (
    <StubEmConstrucao
      titulo="Saldos diários"
      descricao="Evolução diária do saldo de caixa (contas correntes + aplicações) com tabela dia-a-dia — abertura, entradas, saídas, rendimento, fechamento — e gráfico de série temporal. Depende do worker de recálculo de saldo diário que popula a tabela saldo_caixa_diario a partir dos uploads de extrato."
      planoFuturo="Plano 05 (Fase F — parser ampliado + worker de saldo diário)"
    />
  )
}
