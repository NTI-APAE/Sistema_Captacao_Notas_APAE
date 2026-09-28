import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { dashboardApi } from "@/lib/api";
import type { ContactDetail, SearchParams } from "@/lib/types";
import { cleanQuery, isUuid } from "@/lib/query";
import { dateTime, number, statusLabel } from "@/lib/format";
import { NotesTable } from "@/components/tables";
import {
  ConsentBadge,
  DetailGrid,
  EmptyState,
  ErrorState,
  Notice,
  PageHeading,
  Pagination,
  Panel,
} from "@/components/ui";

export const metadata: Metadata = { title: "Detalhes do contato" };

export default async function ContactPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<SearchParams>;
}) {
  const { id } = await params;
  if (!isUuid(id)) notFound();
  const query = cleanQuery(await searchParams);
  const result = await dashboardApi<ContactDetail>(`contatos/${id}`, query);
  if (!result.ok && result.error.code === "not_found") notFound();
  const heading = (
    <PageHeading
      title="Detalhes do contato"
      description="Dados de contato, consentimentos e histórico de notas enviadas."
      back={{ href: "/dashboard/contatos", label: "Contatos" }}
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
    contato: contact,
    consentimentos: consents,
    result: notes,
  } = result.data;
  return (
    <>
      {heading}
      <Panel
        title={contact.nome || "Contato sem nome informado"}
        action={
          <span className="period-chip">
            {contact.ativo ? "Contato ativo" : "Contato inativo"}
          </span>
        }
      >
        <DetailGrid
          items={[
            ["Telefone", contact.telefone],
            ["Criado em", dateTime(contact.criado_em)],
            ["Primeiro envio de nota", dateTime(contact.primeiro_envio)],
            ["Último envio de nota", dateTime(contact.ultimo_envio)],
            [
              "Envios / notas únicas",
              `${number(contact.envios)} / ${number(contact.notas)}`,
            ],
            [
              "Aceita WhatsApp",
              <ConsentBadge key="whatsapp" value={contact.comunicacao} />,
            ],
            [
              "Aceita ligações",
              <ConsentBadge key="ligacao" value={contact.ligacao} />,
            ],
          ]}
        />
      </Panel>
      <Panel
        title="Histórico de consentimentos"
        subtitle="Respostas preservadas, da mais recente para a mais antiga."
      >
        {consents.items.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Tipo</th>
                  <th>Resposta</th>
                  <th>Data da resposta</th>
                  <th>Origem</th>
                </tr>
              </thead>
              <tbody>
                {consents.items.map((item, i) => (
                  <tr key={`${item.tipo}-${item.data_resposta}-${i}`}>
                    <td>{statusLabel(item.tipo)}</td>
                    <td>
                      <ConsentBadge value={item.aceito} />
                    </td>
                    <td>{dateTime(item.data_resposta)}</td>
                    <td>{statusLabel(item.origem)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Nenhum consentimento nesta página"
            description="A ausência de resposta registrada não equivale a autorização."
          />
        )}
        <Pagination
          result={consents}
          path={`/dashboard/contatos/${id}`}
          query={query}
          parameter="consent_page"
        />
      </Panel>
      <Panel
        title="Histórico de notas enviadas"
        subtitle="Submissões associadas a este contato."
      >
        <NotesTable items={notes.items} />
        <Pagination
          result={notes}
          path={`/dashboard/contatos/${id}`}
          query={query}
        />
      </Panel>
      <Notice>
        Este painel é de consulta. As preferências de comunicação não são
        alteradas automaticamente.
      </Notice>
    </>
  );
}
