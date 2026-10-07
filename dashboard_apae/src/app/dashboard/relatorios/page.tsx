import type { Metadata } from "next";
import {
  CircleDollarSign,
  Clock3,
  Copy,
  FileBarChart,
  FileInput,
  MessageCircle,
  ReceiptText,
  ShieldCheck,
  Table2,
  TriangleAlert,
  TrendingUp,
} from "lucide-react";
import { dashboardApi } from "@/lib/api";
import { cleanQuery } from "@/lib/query";
import { money, number } from "@/lib/format";
import type { Note, Options, Page, SearchParams, Summary } from "@/lib/types";
import { Filters } from "@/components/filters";
import { NotesTable } from "@/components/tables";
import { ReportActions } from "@/components/report-actions";
import {
  ErrorState,
  Notice,
  PageHeading,
  Pagination,
  Panel,
} from "@/components/ui";

export const metadata: Metadata = { title: "Relatórios de notas" };

export default async function ReportsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const query = cleanQuery(await searchParams);
  const reportQuery = { ...query, size: "100" };
  const [result, options, summary] = await Promise.all([
    dashboardApi<Page<Note>>("notas", reportQuery),
    dashboardApi<Options>("opcoes"),
    dashboardApi<Summary>("resumo"),
  ]);
  const heading = (
    <PageHeading
      title="Relatórios de notas"
      description="Gere uma visão filtrada dos recebimentos e acompanhe as informações fiscais da operação."
    />
  );

  return (
    <>
      {heading}
      {options.ok && (
        <Filters
          kind="notas"
          query={query}
          options={options.data}
          path="/dashboard/relatorios"
        />
      )}
      {!result.ok ? (
        <ErrorState error={result.error} />
      ) : (
        <>
          {summary.ok && (
            <section
              className="metric-grid report-metrics"
              aria-label="Resumo do relatório"
            >
              <article className="metric-card">
                <div className="metric-label">
                  <span>Registros encontrados</span>
                  <span className="metric-icon blue">
                    <FileBarChart size={17} strokeWidth={1.6} />
                  </span>
                </div>
                <strong>{number(result.data.total)}</strong>
                <p>Resultado para os filtros aplicados</p>
              </article>
              <article className="metric-card">
                <div className="metric-label">
                  <span>Nesta página</span>
                  <span className="metric-icon green">
                    <Table2 size={17} strokeWidth={1.6} />
                  </span>
                </div>
                <strong>{number(result.data.items.length)}</strong>
                <p>Linhas disponíveis para impressão ou CSV</p>
              </article>
              <article className="metric-card">
                <div className="metric-label">
                  <span>Com chave identificada</span>
                  <span className="metric-icon green">
                    <ReceiptText size={17} strokeWidth={1.6} />
                  </span>
                </div>
                <strong>
                  {number(
                    result.data.items.filter((item) => item.chave).length,
                  )}
                </strong>
                <p>Entre os registros desta página</p>
              </article>
              <article className="metric-card">
                <div className="metric-label">
                  <span>Cadastradas</span>
                  <span className="metric-icon blue">
                    <ShieldCheck size={17} strokeWidth={1.6} />
                  </span>
                </div>
                <strong>
                  {number(
                    result.data.items.filter(
                      (item) => item.cadastro === "CADASTRADA",
                    ).length,
                  )}
                </strong>
                <p>Cadastro concluído nesta página</p>
              </article>
              <article className="metric-card">
                <div className="metric-label">
                  <span>Total geral</span>
                  <span className="metric-icon blue">
                    <FileBarChart size={17} strokeWidth={1.6} />
                  </span>
                </div>
                <strong>{number(summary.data.indicadores.total_geral)}</strong>
                <p>Total geral de notas fiscais</p>
              </article>
              <article className="metric-card">
                <div className="metric-label">
                  <span>Via leitor</span>
                  <span className="metric-icon blue">
                    <FileInput size={17} strokeWidth={1.6} />
                  </span>
                </div>
                <strong>
                  {number(summary.data.indicadores.notas_leitor ?? 0)}
                </strong>
                <p>Notas importadas pelo leitor</p>
              </article>
              <article className="metric-card">
                <div className="metric-label">
                  <span>Via WhatsApp</span>
                  <span className="metric-icon green">
                    <MessageCircle size={17} strokeWidth={1.6} />
                  </span>
                </div>
                <strong>
                  {number(summary.data.indicadores.notas_whatsapp)}
                </strong>
                <p>Notas fiscais únicas recebidas</p>
              </article>
              <article className="metric-card">
                <div className="metric-label">
                  <span>Valor cadastrado</span>
                  <span className="metric-icon green">
                    <CircleDollarSign size={17} strokeWidth={1.6} />
                  </span>
                </div>
                <strong>
                  {money(summary.data.indicadores.valor_cadastradas)}
                </strong>
                <p>Soma das notas cadastradas</p>
              </article>
              <article className="metric-card">
                <div className="metric-label">
                  <span>Retorno estimado</span>
                  <span className="metric-icon green">
                    <TrendingUp size={17} strokeWidth={1.6} />
                  </span>
                </div>
                <strong>
                  {money(summary.data.indicadores.retorno_estimado)}
                </strong>
                <p>Estimativa de 1% do valor cadastrado</p>
              </article>
              <article className="metric-card">
                <div className="metric-label">
                  <span>Valor fora do prazo</span>
                  <span className="metric-icon amber">
                    <Clock3 size={17} strokeWidth={1.6} />
                  </span>
                </div>
                <strong>
                  {money(summary.data.indicadores.valor_fora_prazo)}
                </strong>
                <p>Notas com emissão anterior ao prazo</p>
              </article>
              <article className="metric-card">
                <div className="metric-label">
                  <span>Duplicadas</span>
                  <span className="metric-icon amber">
                    <Copy size={17} strokeWidth={1.6} />
                  </span>
                </div>
                <strong>{number(summary.data.indicadores.duplicadas)}</strong>
                <p>Submissões repetidas no histórico</p>
              </article>
              <article className="metric-card">
                <div className="metric-label">
                  <span>Com erros</span>
                  <span className="metric-icon rose">
                    <TriangleAlert size={17} strokeWidth={1.6} />
                  </span>
                </div>
                <strong>
                  {number(
                    summary.data.indicadores.falhas +
                      summary.data.indicadores.notas_erros,
                  )}
                </strong>
                <p>Falhas de leitura ou cadastro</p>
              </article>
            </section>
          )}
          <Panel
            title="Relatório de recebimentos"
            subtitle="Os dados da listagem permanecem protegidos e mascarados."
            action={<ReportActions items={result.data.items} />}
            className="report-panel"
          >
            <NotesTable items={result.data.items} />
            <Pagination
              result={result.data}
              path="/dashboard/relatorios"
              query={reportQuery}
            />
          </Panel>
          <Notice>
            O CSV exporta somente os registros da página atual e mantém telefone
            e chave de acesso mascarados. Use os filtros e a paginação para
            gerar outros recortes do relatório.
          </Notice>
        </>
      )}
    </>
  );
}
