export const number = (value: number) =>
  new Intl.NumberFormat("pt-BR").format(value);

export function dateTime(value: string | null): string {
  if (!value) return "Não informado";
  const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(value);
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: dateOnly ? "UTC" : "America/Sao_Paulo",
    dateStyle: "short",
    ...(dateOnly ? {} : { timeStyle: "short" as const }),
  }).format(new Date(dateOnly ? `${value}T00:00:00Z` : value));
}

export function money(value: string | null): string {
  return value === null
    ? "Não informado"
    : new Intl.NumberFormat("pt-BR", {
        style: "currency",
        currency: "BRL",
      }).format(Number(value));
}

export function statusLabel(value: string): string {
  const labels: Record<string, string> = {
    RECEBIDA: "Recebida",
    PROCESSANDO: "Processando",
    CHAVE_EXTRAIDA: "Chave extraída",
    PENDENTE: "Pendente",
    DUPLICADA: "Duplicada",
    ERRO_LEITURA: "Erro de leitura",
    CADASTRANDO: "Cadastrando",
    AGUARDANDO_CAPTCHA: "Aguardando CAPTCHA",
    PAUSADA: "Pausada",
    CADASTRADA: "Cadastrada",
    IGNORADA: "Ignorada",
    ERRO_CADASTRO: "Erro no cadastro",
    WHATSAPP: "WhatsApp",
    MANUAL: "Manual",
    ARQUIVO_TXT: "Arquivo TXT",
    COMUNICACAO_WHATSAPP: "Comunicação pelo WhatsApp",
    LIGACAO: "Ligações",
    CAMPANHAS: "Campanhas",
  };
  return labels[value] ?? value;
}
