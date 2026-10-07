export type SearchParams = Record<string, string | string[] | undefined>;
export type Query = Record<string, string>;

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Na listagem, telefone/chave já chegam mascarados pela API.
export interface Note {
  id: string;
  data_recebimento: string;
  status: string;
  origem: string;
  pessoa_id: string | null;
  nome: string | null;
  telefone: string | null;
  chave: string | null;
  cadastro: string | null;
  whatsapp_instance: string | null;
  whatsapp_timestamp: string | null;
  whatsapp_replays: number | null;
}

export interface WhatsAppMessage {
  submissao_id: string;
  status: string;
  data_recebimento: string;
  instance: string;
  message_id: string;
  remote_jid: string;
  message_type: string | null;
  timestamp: string | null;
  processed_at: string | null;
  push_name: string | null;
  mimetype: string | null;
  caption: string | null;
  reenvios: number;
  last_replay_at: string | null;
  atraso_processamento_segundos: number | null;
}

export interface NoteDetail extends Note {
  nota_fiscal_id: string | null;
  mensagem_whatsapp_id: string | null;
  erro_codigo: string | null;
  data_cadastro: string | null;
  valor: string | null;
  data_emissao: string | null;
  whatsapp_message_id: string | null;
  whatsapp_remote_jid: string | null;
  whatsapp_message_type: string | null;
  whatsapp_processed_at: string | null;
  whatsapp_push_name: string | null;
  whatsapp_mimetype: string | null;
  whatsapp_caption: string | null;
  whatsapp_last_replay_at: string | null;
  atraso_processamento_segundos: number | null;
  historico_mensagens: WhatsAppMessage[];
}

export interface Contact {
  id: string;
  nome: string | null;
  telefone: string;
  ativo: boolean;
  criado_em: string;
  primeiro_envio: string | null;
  ultimo_envio: string | null;
  envios: number;
  notas: number;
  comunicacao: boolean | null;
  ligacao: boolean | null;
}

export interface Consent {
  tipo: string;
  aceito: boolean;
  origem: string;
  data_resposta: string;
}

export interface ContactDetail {
  contato: Contact;
  result: Page<Note>;
  consentimentos: Page<Consent>;
}

export interface Summary {
  indicadores: {
    total: number;
    hoje: number;
    mes: number;
    duplicadas: number;
    falhas: number;
    notas: number;
    notas_leitor?: number;
    notas_whatsapp: number;
    notas_erros: number;
    notas_ignoradas: number;
    total_geral: number;
    cadastradas: number;
    valor_cadastradas: string;
    retorno_estimado: string;
    valor_fora_prazo: string;
    contatos: number;
    novos_contatos: number;
    imagens_sem_chave: number;
    reenvios_mensagens: number;
  };
  series: { dia: string; total: number }[];
  maximo: number;
  status_submissoes: [string, number][];
  status_notas: [string, number][];
  leitor: ReaderSummary;
  result: Page<Note>;
}

export interface ReaderSummary {
  operacoes: number;
  total_notas: number;
  tentadas: number;
  cadastradas: number;
  duplicadas: number;
  ignoradas: number;
  erros: number;
  valor_total: string;
  valor_cadastradas: string;
  valor_duplicadas: string;
  valor_ignoradas: string;
  valor_erros: string;
  tempo_total_segundos: string;
  tempo_notas_segundos: string;
  ultima_operacao_em: string | null;
}

export interface Options {
  status: string[];
  cadastros: string[];
}

export type ApiErrorCode =
  | "authentication_unavailable"
  | "authentication_required"
  | "forbidden"
  | "not_found"
  | "invalid_filters"
  | "database_unavailable"
  | "unavailable"
  | "invalid_response";
export interface ApiError {
  code: ApiErrorCode;
  status: number;
}
export type ApiResult<T> =
  { ok: true; data: T } | { ok: false; error: ApiError };
