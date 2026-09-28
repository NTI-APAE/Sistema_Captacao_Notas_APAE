import Link from "next/link";
import type { ReactNode } from "react";
import {
  ArrowLeft,
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  Inbox,
  Info,
  LockKeyhole,
  ShieldAlert,
  Unplug,
} from "lucide-react";
import { RefreshButton } from "./refresh-button";
import { number, statusLabel } from "@/lib/format";
import { pageHref } from "@/lib/query";
import type { ApiError, Page, Query } from "@/lib/types";

export function PageHeading({
  title,
  description,
  back,
}: {
  title: string;
  description: string;
  back?: { href: string; label: string };
}) {
  return (
    <div className="page-heading">
      <div>
        {back && (
          <Link className="back-link" href={back.href}>
            <ArrowLeft size={14} />
            {back.label}
          </Link>
        )}
        <p className="eyebrow">CAPTAÇÃO DE RECURSOS</p>
        <h1>{title}</h1>
        <p className="page-description">{description}</p>
      </div>
      <RefreshButton />
    </div>
  );
}

export function Panel({
  title,
  subtitle,
  action,
  children,
  className = "",
}: {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      {title && (
        <div className="panel-header">
          <div>
            <h2>{title}</h2>
            {subtitle && <p>{subtitle}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function StatusBadge({ value }: { value: string | null }) {
  if (!value) return <span className="muted">—</span>;
  const tone = ["CADASTRADA", "CHAVE_EXTRAIDA"].includes(value)
    ? "success"
    : value.startsWith("ERRO")
      ? "danger"
      : ["DUPLICADA", "PAUSADA", "AGUARDANDO_CAPTCHA"].includes(value)
        ? "warning"
        : "neutral";
  return (
    <span className={`status-badge ${tone}`} title={value}>
      <i />
      {statusLabel(value)}
    </span>
  );
}

export function ConsentBadge({ value }: { value: boolean | null }) {
  return (
    <span
      className={`consent ${value === null ? "unknown" : value ? "yes" : "no"}`}
    >
      {value === null ? "Não informado" : value ? "Sim" : "Não"}
    </span>
  );
}

export function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="empty-state">
      <span className="empty-icon">
        <Inbox size={25} />
      </span>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}

export function Notice({ children }: { children: ReactNode }) {
  return (
    <div className="notice">
      <Info size={16} />
      <p>{children}</p>
    </div>
  );
}

export function Pagination<T>({
  result,
  path,
  query,
  parameter = "page",
}: {
  result: Page<T>;
  path: string;
  query: Query;
  parameter?: string;
}) {
  const start = result.items.length ? (result.page - 1) * result.size + 1 : 0;
  const end = start ? start + result.items.length - 1 : 0;
  return (
    <nav
      className="pagination"
      aria-label={
        parameter === "page"
          ? "Paginação de registros"
          : "Paginação de consentimentos"
      }
    >
      <span>
        {start ? `${number(start)}–${number(end)} de ` : ""}
        <strong>{number(result.total)}</strong> registros
      </span>
      <div>
        {result.page > 1 ? (
          <Link
            href={pageHref(path, query, result.page - 1, parameter)}
            prefetch={false}
            aria-label="Página anterior"
          >
            <ChevronLeft size={16} />
          </Link>
        ) : (
          <span className="disabled">
            <ChevronLeft size={16} />
          </span>
        )}
        <span>
          Página <strong>{result.page}</strong> de {result.pages}
        </span>
        {result.page < result.pages ? (
          <Link
            href={pageHref(path, query, result.page + 1, parameter)}
            prefetch={false}
            aria-label="Próxima página"
          >
            <ChevronRight size={16} />
          </Link>
        ) : (
          <span className="disabled">
            <ChevronRight size={16} />
          </span>
        )}
      </div>
    </nav>
  );
}

export function DetailGrid({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="detail-grid">
      {items.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value ?? "Não informado"}</dd>
        </div>
      ))}
    </dl>
  );
}

export function ErrorState({ error }: { error: ApiError }) {
  const auth = [
    "authentication_unavailable",
    "authentication_required",
    "forbidden",
  ].includes(error.code);
  const messages: Record<string, [string, string]> = {
    authentication_unavailable: [
      "Acesso administrativo pendente",
      "O painel está pronto para consulta. A autenticação administrativa precisa ser conectada à API para liberar os dados da operação.",
    ],
    authentication_required: [
      "Autenticação necessária",
      "Sua sessão não está ativa. Entre pelo acesso administrativo da organização para consultar os dados.",
    ],
    forbidden: [
      "Acesso não autorizado",
      "Sua conta não tem permissão para consultar este painel. Solicite acesso ao responsável pelo sistema.",
    ],
    invalid_filters: [
      "Confira os filtros",
      "Verifique as datas, os valores e a paginação. A data final deve ser igual ou posterior à data inicial.",
    ],
    not_found: [
      "Registro não encontrado",
      "Este registro não está disponível. Volte à listagem para continuar a consulta.",
    ],
  };
  const [title, description] = messages[error.code] ?? [
    "Não foi possível carregar os dados",
    "A conexão com o serviço de notas está indisponível no momento. Tente atualizar a página em alguns instantes.",
  ];
  const Icon = auth
    ? LockKeyhole
    : error.code === "invalid_filters"
      ? ShieldAlert
      : Unplug;
  return (
    <section className="error-state" role="status">
      <span className="error-icon">
        <Icon size={31} strokeWidth={1.5} />
      </span>
      <span className="section-kicker">
        {auth ? "ACESSO PROTEGIDO" : "CONSULTA INDISPONÍVEL"}
      </span>
      <h2>{title}</h2>
      <p>{description}</p>
      <RefreshButton label="Tentar novamente" />
      {auth && (
        <div className="error-footnote">
          <ShieldAlert size={14} />
          Nenhum dado operacional é exibido sem autorização.
        </div>
      )}
    </section>
  );
}

export function ViewAll({
  href,
  children = "Ver todos",
}: {
  href: string;
  children?: ReactNode;
}) {
  return (
    <Link className="text-link" href={href} prefetch={false}>
      {children}
      <ArrowRight size={14} />
    </Link>
  );
}
