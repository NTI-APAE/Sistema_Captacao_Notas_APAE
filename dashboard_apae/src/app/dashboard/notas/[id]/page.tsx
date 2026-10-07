import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { dashboardApi } from "@/lib/api";
import { dateTime, money, statusLabel } from "@/lib/format";
import { isUuid } from "@/lib/query";
import type { NoteDetail } from "@/lib/types";
import {
  DetailGrid,
  ErrorState,
  Notice,
  PageHeading,
  Panel,
  StatusBadge,
} from "@/components/ui";

export const metadata: Metadata = { title: "Detalhes da nota" };

export default async function NotePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  if (!isUuid(id)) notFound();
  const result = await dashboardApi<NoteDetail>(`notas/${id}`);
  if (!result.ok && result.error.code === "not_found") notFound();
  const heading = (
    <PageHeading
      title="Detalhes do recebimento"
      description="Informações da submissão e da nota fiscal vinculada."
      back={{ href: "/dashboard/notas", label: "Notas fiscais" }}
    />
  );
  if (!result.ok)
    return (
      <>
        {heading}
        <ErrorState error={result.error} />
      </>
    );
  const item = result.data;
  return (
    <>
      {heading}
      <Panel title="Recebimento" action={<StatusBadge value={item.status} />}>
        <DetailGrid
          items={[
            [
              "ID da submissão",
              <span className="mono" key="id">
                {item.id}
              </span>,
            ],
            ["Recebida em", dateTime(item.data_recebimento)],
            ["Origem", statusLabel(item.origem)],
            [
              "Contato",
              item.pessoa_id ? (
                <Link
                  key="contato"
                  href={`/dashboard/contatos/${item.pessoa_id}`}
                  prefetch={false}
                >
                  {item.nome || "Sem nome informado"}
                </Link>
              ) : (
                "Não vinculado"
              ),
            ],
            ["Telefone", item.telefone],
            [
              "Referência interna da mensagem",
              item.mensagem_whatsapp_id || "Não vinculada",
            ],
            ["Código de erro", item.erro_codigo || "Não registrado"],
          ]}
        />
      </Panel>
      {item.whatsapp_message_id && (
        <Panel
          title="Mensagem WhatsApp"
          subtitle="Metadados recebidos da Evolution e tempo de processamento."
        >
          <DetailGrid
            items={[
              [
                "ID da mensagem",
                <span className="mono" key="message-id">
                  {item.whatsapp_message_id}
                </span>,
              ],
              ["Instância", item.whatsapp_instance],
              [
                "JID de origem",
                <span className="mono" key="remote-jid">
                  {item.whatsapp_remote_jid}
                </span>,
              ],
              ["Data/hora no WhatsApp", dateTime(item.whatsapp_timestamp)],
              ["Processada em", dateTime(item.whatsapp_processed_at)],
              [
                "Atraso até o processamento",
                item.atraso_processamento_segundos === null
                  ? "Não informado"
                  : `${item.atraso_processamento_segundos}s`,
              ],
              ["Nome exibido", item.whatsapp_push_name],
              ["Tipo da mensagem", item.whatsapp_message_type],
              ["MIME da imagem", item.whatsapp_mimetype],
              ["Legenda", item.whatsapp_caption],
              ["Reenvios do mesmo evento", String(item.whatsapp_replays ?? 0)],
              ["Último reenvio", dateTime(item.whatsapp_last_replay_at)],
            ]}
          />
        </Panel>
      )}
      {item.historico_mensagens.length > 0 && (
        <Panel
          title="Histórico de mensagens da nota"
          subtitle="Mensagens diferentes com a mesma chave permanecem distintas dos reenvios do mesmo evento."
        >
          <div
            className="table-scroll"
            tabIndex={0}
            role="region"
            aria-label="Histórico de mensagens da nota"
          >
            <table>
              <thead>
                <tr>
                  <th>Mensagem</th>
                  <th>Instância</th>
                  <th>Recebida</th>
                  <th>Status</th>
                  <th>Reenvios</th>
                  <th>Atraso</th>
                </tr>
              </thead>
              <tbody>
                {item.historico_mensagens.map((message) => (
                  <tr key={message.submissao_id}>
                    <td className="mono">{message.message_id}</td>
                    <td>{message.instance}</td>
                    <td className="nowrap">
                      {dateTime(message.timestamp || message.data_recebimento)}
                    </td>
                    <td>
                      <StatusBadge value={message.status} />
                    </td>
                    <td>{message.reenvios}</td>
                    <td>
                      {message.atraso_processamento_segundos === null
                        ? "Não informado"
                        : `${message.atraso_processamento_segundos}s`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}
      <Panel
        title="Nota fiscal vinculada"
        action={<StatusBadge value={item.cadastro} />}
      >
        <DetailGrid
          items={[
            [
              "Chave de acesso",
              <span className="mono" key="chave">
                {item.chave || "Não extraída"}
              </span>,
            ],
            ["ID da nota fiscal", item.nota_fiscal_id || "Não vinculada"],
            ["Data do cadastro", dateTime(item.data_cadastro)],
            ["Data de emissão", dateTime(item.data_emissao)],
            ["Valor fiscal", money(item.valor)],
          ]}
        />
      </Panel>
      <Notice>
        Dados completos disponíveis apenas nesta consulta administrativa.
        Imagens e mensagens técnicas livres não são exibidas.
      </Notice>
    </>
  );
}
