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
