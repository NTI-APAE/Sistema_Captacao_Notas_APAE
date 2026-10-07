import Form from "next/form";
import Link from "next/link";
import { Search, SlidersHorizontal } from "lucide-react";
import type { Options, Query } from "@/lib/types";
import { statusLabel } from "@/lib/format";

function Select({
  name,
  label,
  values,
  query,
}: {
  name: string;
  label: string;
  values: [string, string][];
  query: Query;
}) {
  return (
    <label>
      {label}
      <select name={name} defaultValue={query[name] || ""}>
        <option value="">Todos</option>
        {values.map(([value, text]) => (
          <option key={value} value={value}>
            {text}
          </option>
        ))}
      </select>
    </label>
  );
}
const booleanOptions: [string, string][] = [
  ["true", "Sim"],
  ["false", "Não"],
];

export function Filters({
  kind,
  query,
  options,
  path = `/dashboard/${kind}`,
}: {
  kind: "notas" | "contatos";
  query: Query;
  options?: Options;
  path?: string;
}) {
  const notes = kind === "notas";
  // Reinicializa os campos quando uma navegação GET muda a consulta.
  return (
    <Form action={path} key={JSON.stringify(query)} className="filters-panel">
      <div className="filters-top">
        <div className="filters-label">
          <SlidersHorizontal size={16} />
          <h2>Filtrar {notes ? "recebimentos" : "contatos"}</h2>
        </div>
        <Link href={path} className="clear-filters" prefetch={false}>
          Limpar filtros
        </Link>
      </div>
      <div className="filters-grid">
        <label className="search-field">
          Pesquisar
          <span>
            <Search size={16} />
            <input
              name="q"
              defaultValue={query.q}
              placeholder={
                notes ? "Nome, telefone ou chave" : "Nome ou telefone"
              }
              maxLength={100}
            />
          </span>
        </label>
        <label>
          Data inicial
          <input
            type="date"
            name="data_inicial"
            defaultValue={query.data_inicial}
          />
        </label>
        <label>
          Data final
          <input
            type="date"
            name="data_final"
            defaultValue={query.data_final}
          />
        </label>
        {notes ? (
          <>
            <Select
              name="status"
              label="Status da submissão"
              query={query}
              values={(options?.status ?? []).map((value) => [
                value,
                statusLabel(value),
              ])}
            />
            <Select
              name="cadastro"
              label="Cadastro fiscal"
              query={query}
              values={(options?.cadastros ?? []).map((value) => [
                value,
                statusLabel(value),
              ])}
            />
            <label>
              Telefone
              <input
                name="telefone"
                defaultValue={query.telefone}
                maxLength={30}
                placeholder="DDD + telefone"
              />
            </label>
            <label>
              Chave de acesso
              <input
                name="chave"
                defaultValue={query.chave}
                maxLength={44}
                placeholder="Chave ou parte dela"
              />
            </label>
            <Select
              name="duplicada"
              label="Duplicada"
              query={query}
              values={booleanOptions}
            />
          </>
        ) : (
          <>
            <Select
              name="ativo"
              label="Contato ativo"
              query={query}
              values={booleanOptions}
            />
            <Select
              name="comunicacao"
              label="Aceita WhatsApp"
              query={query}
              values={booleanOptions}
            />
            <Select
              name="ligacao"
              label="Aceita ligações"
              query={query}
              values={booleanOptions}
            />
          </>
        )}
        <button className="button primary" type="submit">
          <Search size={15} />
          Aplicar filtros
        </button>
      </div>
      <p className="filter-caption">
        Período aplicado à{" "}
        {notes
          ? "data de recebimento da submissão"
          : "data de criação do contato"}
        .
      </p>
    </Form>
  );
}
