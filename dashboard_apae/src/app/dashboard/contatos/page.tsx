import type { Metadata } from "next";
import { dashboardApi } from "@/lib/api";
import type { Contact, Page, SearchParams } from "@/lib/types";
import { cleanQuery } from "@/lib/query";
import { Filters } from "@/components/filters";
import { ContactsTable } from "@/components/tables";
import {
  ErrorState,
  Notice,
  PageHeading,
  Pagination,
  Panel,
} from "@/components/ui";

export const metadata: Metadata = { title: "Contatos e consentimentos" };

export default async function ContactsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const query = cleanQuery(await searchParams);
  const result = await dashboardApi<Page<Contact>>("contatos", query);
  return (
    <>
      <PageHeading
        title="Contatos"
        description="Conheça quem envia notas e consulte suas preferências de comunicação."
      />
      {(result.ok || result.error.code === "invalid_filters") && (
        <Filters kind="contatos" query={query} />
      )}
      {!result.ok ? (
        <ErrorState error={result.error} />
      ) : (
        <>
          <Panel
            title="Contatos e consentimentos"
            subtitle="Preferências conforme a resposta mais recente registrada."
          >
            <ContactsTable items={result.data.items} />
            <Pagination
              result={result.data}
              path="/dashboard/contatos"
              query={query}
            />
          </Panel>
          <Notice>
            “Não informado” indica ausência de resposta registrada e não
            equivale a autorização. O último envio se refere a notas fiscais,
            não a outras conversas.
          </Notice>
        </>
      )}
    </>
  );
}
