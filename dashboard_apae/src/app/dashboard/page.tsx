import {
  CalendarDays,
  CheckCheck,
  Copy,
  Ban,
  FileText,
  RefreshCw,
  ReceiptText,
  TriangleAlert,
  UsersRound,
  UserRoundPlus,
} from "lucide-react";
import { dashboardApi } from "@/lib/api";
import type { Summary } from "@/lib/types";
import { money, number } from "@/lib/format";
import {
  ErrorState,
  Notice,
  PageHeading,
  Panel,
  ViewAll,
} from "@/components/ui";
import { NotesTable } from "@/components/tables";
import { ReceiptsChart, StatusChart } from "@/components/charts";

export default async function DashboardPage() {
  const result = await dashboardApi<Summary>("resumo");
  const heading = (
    <PageHeading
      title="Visão geral"
      description="Acompanhe as notas recebidas e as pessoas que apoiam a APAE."
    />
  );
  if (!result.ok)
    return (
      <>
        {heading}
        <ErrorState error={result.error} />
      </>
    );
  const {
    indicadores: totals,
    series,
    status_notas,
    status_submissoes,
    leitor,
    result: recent,
  } = result.data;
  const cards = [
    {
      label: "Recebidas hoje",
      value: totals.hoje,
      hint: "Submissões do dia",
      icon: ReceiptText,
      tone: "green",
    },
    {
      label: "Recebidas no mês",
      value: totals.mes,
      hint: "Do início do mês até hoje",
      icon: CalendarDays,
      tone: "blue",
    },
    {
      label: "Notas cadastradas",
      value: totals.cadastradas,
      hint: "Cadastro concluído · histórico",
      icon: CheckCheck,
      tone: "green",
    },
    {
      label: "Notas via arquivos",
      value: totals.notas_leitor ?? 0,
      hint: "Importadas pelo leitor",
      icon: FileText,
      tone: "blue",
    },
    {
      label: "Duplicadas",
      value: totals.duplicadas,
      hint: "Submissões repetidas · histórico",
      icon: Copy,
      tone: "amber",
    },
    {
      label: "Reenvios de mensagens",
      value: totals.reenvios_mensagens,
      hint: "Mesmo evento reapresentado",
      icon: RefreshCw,
      tone: "amber",
    },
    {
      label: "Notas com erro",
      value: totals.falhas + totals.notas_erros,
      hint: "Falha de leitura ou cadastro",
      icon: TriangleAlert,
      tone: "rose",
    },
    {
      label: "Notas ignoradas",
      value: totals.notas_ignoradas,
      hint: "Ignoradas no cadastro",
      icon: Ban,
      tone: "amber",
    },
  ];
  return (
    <>
      {heading}
      <section className="metric-grid" aria-label="Indicadores operacionais">
        {cards.map(({ label, value, hint, icon: Icon, tone }) => (
          <article className="metric-card" key={label}>
            <div className="metric-label">
              <span>{label}</span>
              <span className={`metric-icon ${tone}`}>
                <Icon size={17} strokeWidth={1.6} />
              </span>
            </div>
            <strong>{number(value)}</strong>
            <p>{hint}</p>
          </article>
        ))}
      </section>
      <Panel
        title="Resumo das operações do leitor"
        subtitle="Valores enviados pelo leitor de notas e consolidados pela API."
      >
        <section className="summary-strip" aria-label="Valores do leitor">
          {[
            ["Operações", number(leitor.operacoes)],
            ["Notas processadas", number(leitor.total_notas)],
            ["Valor total", money(leitor.valor_total)],
            ["Cadastradas", money(leitor.valor_cadastradas)],
            ["Duplicadas", money(leitor.valor_duplicadas)],
            ["Ignoradas", money(leitor.valor_ignoradas)],
            ["Erros", money(leitor.valor_erros)],
          ].map(([label, value]) => (
            <div key={label}>
              <div>
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
            </div>
          ))}
        </section>
      </Panel>
      <div className="overview-charts">
        <Panel
          title="Notas recebidas por dia"
          subtitle="Um retrato do volume de recebimentos da operação."
        >
          <ReceiptsChart series={series} />
        </Panel>
        <Panel
          title="Distribuição por status"
          subtitle="Acompanhe cada etapa do processamento."
        >
          <StatusChart submissions={status_submissoes} notes={status_notas} />
        </Panel>
      </div>
      <section className="summary-strip" aria-label="Resumo do histórico">
        {[
          {
            label: "Notas fiscais únicas",
            value: totals.notas,
            icon: ReceiptText,
          },
          {
            label: "Contatos registrados",
            value: totals.contatos,
            icon: UsersRound,
          },
          {
            label: "Novos contatos no mês",
            value: totals.novos_contatos,
            icon: UserRoundPlus,
          },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label}>
            <span className="summary-icon">
              <Icon size={19} strokeWidth={1.6} />
            </span>
            <div>
              <span>{label}</span>
              <strong>{number(value)}</strong>
            </div>
          </div>
        ))}
      </section>
      <Panel
        title="Últimas notas recebidas"
        subtitle="Recebimentos mais recentes, incluindo duplicidades."
        action={<ViewAll href="/dashboard/notas">Ver todas as notas</ViewAll>}
      >
        <NotesTable items={recent.items} />
      </Panel>
      <Notice>
        Recebimentos contam submissões; uma imagem pode gerar mais de uma nota.
        Falhas: {number(totals.falhas)} submissão(ões) com erro de leitura e{" "}
        {number(totals.imagens_sem_chave)} imagem(ns) sem chave válida. Imagens
        sem chave não possuem contato vinculado e não aparecem na listagem.
      </Notice>
    </>
  );
}
