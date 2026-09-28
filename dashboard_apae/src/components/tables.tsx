import Link from "next/link";
import { ArrowUpRight, MessageCircle, UserRound } from "lucide-react";
import { dateTime, number, statusLabel } from "@/lib/format";
import type { Contact, Note } from "@/lib/types";
import { ConsentBadge, EmptyState, StatusBadge } from "./ui";

export function NotesTable({ items }: { items: Note[] }) {
  if (!items.length)
    return (
      <EmptyState
        title="Nenhuma nota encontrada"
        description="Ajuste os filtros ou aguarde novos recebimentos para acompanhar a operação."
      />
    );
  return (
    <div
      className="table-scroll"
      tabIndex={0}
      role="region"
      aria-label="Notas recebidas"
    >
      <table>
        <thead>
          <tr>
            <th>Recebimento</th>
            <th>Contato</th>
            <th>Chave de acesso</th>
            <th>Submissão</th>
            <th>Cadastro fiscal</th>
            <th>Origem</th>
            <th>
              <span className="sr-only">Ações</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td className="nowrap">{dateTime(item.data_recebimento)}</td>
              <td>
                <div className="person-cell">
                  <span className="person-avatar">
                    <UserRound size={15} />
                  </span>
                  <div>
                    <span className="person-name">
                      {item.nome || "Sem nome informado"}
                    </span>
                    <small>{item.telefone || "Não informado"}</small>
                  </div>
                </div>
              </td>
              <td className="mono nowrap">{item.chave || "Não extraída"}</td>
              <td>
                <StatusBadge value={item.status} />
              </td>
              <td>
                <StatusBadge value={item.cadastro} />
              </td>
              <td>
                <span className="origin">
                  {item.origem === "WHATSAPP" && <MessageCircle size={13} />}
                  {statusLabel(item.origem)}
                </span>
              </td>
              <td>
                <Link
                  className="row-action"
                  href={`/dashboard/notas/${item.id}`}
                  prefetch={false}
                  aria-label={`Detalhes da nota recebida em ${dateTime(item.data_recebimento)}`}
                >
                  <ArrowUpRight size={17} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ContactsTable({ items }: { items: Contact[] }) {
  if (!items.length)
    return (
      <EmptyState
        title="Nenhum contato encontrado"
        description="Ajuste os filtros para encontrar contatos registrados na operação."
      />
    );
  return (
    <div
      className="table-scroll"
      tabIndex={0}
      role="region"
      aria-label="Contatos captados"
    >
      <table>
        <thead>
          <tr>
            <th>Contato</th>
            <th>Criado em</th>
            <th>Último envio</th>
            <th>Envios / notas únicas</th>
            <th>WhatsApp</th>
            <th>Ligações</th>
            <th>
              <span className="sr-only">Ações</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>
                <div className="person-cell">
                  <span className="person-avatar">
                    <UserRound size={16} />
                  </span>
                  <div>
                    <span className="person-name">
                      {item.nome || "Sem nome informado"}
                    </span>
                    <small>{item.telefone}</small>
                  </div>
                </div>
              </td>
              <td className="nowrap">{dateTime(item.criado_em)}</td>
              <td className="nowrap">{dateTime(item.ultimo_envio)}</td>
              <td>
                <strong>{number(item.envios)}</strong>
                <span className="muted"> / {number(item.notas)}</span>
              </td>
              <td>
                <ConsentBadge value={item.comunicacao} />
              </td>
              <td>
                <ConsentBadge value={item.ligacao} />
              </td>
              <td>
                <Link
                  href={`/dashboard/contatos/${item.id}`}
                  className="row-action"
                  prefetch={false}
                  aria-label={`Detalhes de ${item.nome || "contato"}`}
                >
                  <ArrowUpRight size={17} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
