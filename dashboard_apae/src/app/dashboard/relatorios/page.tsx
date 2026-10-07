import type { Metadata } from "next";
import { FileBarChart, ReceiptText, ShieldCheck, Table2 } from "lucide-react";
import { dashboardApi } from "@/lib/api";
import { cleanQuery } from "@/lib/query";
import { number } from "@/lib/format";
import type { Note, Options, Page, SearchParams } from "@/lib/types";
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
  const [result, options] = await Promise.all([
    dashboardApi<Page<Note>>("notas", reportQuery),
    dashboardApi<Options>("opcoes"),
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
                {number(result.data.items.filter((item) => item.chave).length)}
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
          </section>
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
