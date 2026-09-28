import type { Metadata } from "next";
import { dashboardApi } from "@/lib/api";
import type { Note, Options, Page, SearchParams } from "@/lib/types";
import { cleanQuery } from "@/lib/query";
import { Filters } from "@/components/filters";
import { NotesTable } from "@/components/tables";
import { ErrorState, PageHeading, Pagination, Panel } from "@/components/ui";

export const metadata: Metadata = { title: "Notas fiscais" };

export default async function NotesPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const query = cleanQuery(await searchParams);
  const [result, options] = await Promise.all([
    dashboardApi<Page<Note>>("notas", query),
    dashboardApi<Options>("opcoes"),
  ]);
  return (
    <>
      <PageHeading
        title="Notas fiscais"
        description="Consulte o histórico de recebimentos e o andamento do cadastro fiscal."
      />
      {options.ok && (
        <Filters kind="notas" query={query} options={options.data} />
      )}
      {!result.ok ? (
        <ErrorState error={result.error} />
      ) : (
        <Panel
          title="Histórico de recebimentos"
          subtitle="Chaves e telefones protegidos na listagem."
        >
          <NotesTable items={result.data.items} />
          <Pagination
            result={result.data}
            path="/dashboard/notas"
            query={query}
          />
        </Panel>
      )}
    </>
  );
}
