"""Consultas de leitura: agregações e paginação executadas no banco."""

from datetime import timedelta

from sqlalchemy import exists, func, literal, null, or_, select, union_all

from app.models.consentimento_model import ConsentimentoModel as C
from app.models.evento_imagem import EventoImagem as E
from app.models.nota_fiscal_model import NotaFiscalModel as N
from app.models.pessoa_model import PessoaModel as P
from app.models.submissao_nota_model import SubmissaoNotaModel as S
from app.schemas.admin_reporting_filters import inicio_dia


class AdminReportingRepository:
    def __init__(self, session):
        self.session = session

    def count(self, model, *conditions):
        return (
            self.session.scalar(
                select(func.count()).select_from(model).where(*conditions)
            )
            or 0
        )

    def indicadores(self, hoje):
        inicio = inicio_dia(hoje)
        fim = inicio_dia(hoje + timedelta(days=1))
        mes = inicio_dia(hoje.replace(day=1))
        counts = (
            self.session.execute(
                select(
                    func.count().label("total"),
                    func.count()
                    .filter(S.data_recebimento >= inicio, S.data_recebimento < fim)
                    .label("hoje"),
                    func.count()
                    .filter(S.data_recebimento >= mes, S.data_recebimento < fim)
                    .label("mes"),
                    func.count().filter(S.status == "DUPLICADA").label("duplicadas"),
                    func.count().filter(S.status == "ERRO_LEITURA").label("falhas"),
                ).select_from(S)
            )
            .mappings()
            .one()
        )
        result = dict(counts)
        result.update(
            notas=self.count(N),
            notas_leitor=self.count(
                N,
                ~exists().where(S.nota_fiscal_id == N.id),
            ),
            cadastradas=self.count(N, N.status == "CADASTRADA"),
            contatos=self.count(P),
            novos_contatos=self.count(P, P.criado_em >= mes, P.criado_em < fim),
            imagens_sem_chave=self.count(
                E, E.resultado["saved"].as_boolean().is_(False)
            ),
            reenvios_mensagens=(
                self.session.scalar(select(func.coalesce(func.sum(E.reenvios), 0)))
                or 0
            ),
        )
        return result

    def recebimentos_por_dia(self, inicio, fim):
        # timezone() mantém o agrupamento consistente com filtros e cards no PG.
        timestamp = S.data_recebimento
        if self.session.get_bind().dialect.name == "postgresql":
            day = func.date(func.timezone("America/Sao_Paulo", timestamp))
        else:
            day = func.date(timestamp, "-3 hours")
        return dict(
            self.session.execute(
                select(day, func.count())
                .where(
                    timestamp >= inicio_dia(inicio),
                    timestamp < inicio_dia(fim + timedelta(days=1)),
                )
                .group_by(day)
            ).all()
        )

    def por_status(self, model):
        return self.session.execute(
            select(model.status, func.count())
            .group_by(model.status)
            .order_by(model.status)
        ).all()

    def _notas(self, filtro, pessoa_id=None):
        submissao = (
            select(
                S.id,
                S.data_recebimento,
                S.status,
                S.origem,
                S.pessoa_id,
                S.nota_fiscal_id,
                S.mensagem_whatsapp_id,
                S.erro_codigo,
                func.coalesce(S.chave_extraida, N.chave).label("chave"),
                P.nome,
                P.telefone,
                N.status.label("cadastro"),
                N.data_cadastro,
                N.valor,
                N.data_emissao,
                E.instancia.label("whatsapp_instance"),
                E.evento_id.label("whatsapp_message_id"),
                E.remote_jid.label("whatsapp_remote_jid"),
                E.message_type.label("whatsapp_message_type"),
                E.data_mensagem.label("whatsapp_timestamp"),
                E.criado_em.label("whatsapp_processed_at"),
                E.push_name.label("whatsapp_push_name"),
                E.mimetype.label("whatsapp_mimetype"),
                E.caption.label("whatsapp_caption"),
                E.reenvios.label("whatsapp_replays"),
                E.ultimo_reenvio_em.label("whatsapp_last_replay_at"),
            )
            .outerjoin(P, S.pessoa_id == P.id)
            .outerjoin(N, S.nota_fiscal_id == N.id)
            .outerjoin(
                E,
                (S.origem == E.origem)
                & (S.evento_instancia == E.instancia)
                & (S.evento_id == E.evento_id),
            )
        )
        nota_importada = select(
            N.id.label("id"),
            N.criado_em.label("data_recebimento"),
            literal("IMPORTADO").label("status"),
            literal("LEITOR_NOTA_FISCAL").label("origem"),
            null().label("pessoa_id"),
            N.id.label("nota_fiscal_id"),
            null().label("mensagem_whatsapp_id"),
            null().label("erro_codigo"),
            N.chave.label("chave"),
            null().label("nome"),
            null().label("telefone"),
            N.status.label("cadastro"),
            N.data_cadastro,
            N.valor,
            N.data_emissao,
            null().label("whatsapp_instance"),
            null().label("whatsapp_message_id"),
            null().label("whatsapp_remote_jid"),
            null().label("whatsapp_message_type"),
            null().label("whatsapp_timestamp"),
            null().label("whatsapp_processed_at"),
            null().label("whatsapp_push_name"),
            null().label("whatsapp_mimetype"),
            null().label("whatsapp_caption"),
            null().label("whatsapp_replays"),
            null().label("whatsapp_last_replay_at"),
        ).where(~exists().where(S.nota_fiscal_id == N.id))
        registros = union_all(submissao, nota_importada).subquery("notas_admin")
        query = select(registros)
        if pessoa_id:
            query = query.where(registros.c.pessoa_id == pessoa_id)
        if filtro.inicio:
            query = query.where(registros.c.data_recebimento >= filtro.inicio)
        if filtro.fim:
            query = query.where(registros.c.data_recebimento < filtro.fim)
        if filtro.status:
            query = query.where(registros.c.status == filtro.status.value)
        if filtro.cadastro:
            query = query.where(registros.c.cadastro == filtro.cadastro.value)
        if filtro.duplicada is not None:
            condition = registros.c.status == "DUPLICADA"
            query = query.where(condition if filtro.duplicada else ~condition)
        if filtro.telefone:
            digits = "".join(c for c in filtro.telefone if c.isdigit())
            query = query.where(
                registros.c.telefone.contains(digits or "invalid", autoescape=True)
            )
        if filtro.chave:
            query = query.where(
                registros.c.chave.contains(filtro.chave, autoescape=True)
            )
        if filtro.q:
            query = query.where(
                or_(
                    registros.c.nome.icontains(filtro.q, autoescape=True),
                    registros.c.telefone.contains(filtro.q, autoescape=True),
                    registros.c.chave.contains(filtro.q, autoescape=True),
                )
            )
        return query

    def pagina(self, query, filtro, *ordering):
        total = self.session.scalar(select(func.count()).select_from(query.subquery()))
        rows = self.session.execute(
            query.order_by(*ordering)
            .limit(filtro.size)
            .offset((filtro.page - 1) * filtro.size)
        ).mappings()
        return {
            "items": [dict(row) for row in rows],
            "total": total,
            "page": filtro.page,
            "size": filtro.size,
            "pages": max(1, (total + filtro.size - 1) // filtro.size),
        }

    def notas(self, filtro, pessoa_id=None):
        registros = self._notas(filtro, pessoa_id).subquery("notas_filtradas")
        return self.pagina(
            select(registros),
            filtro,
            registros.c.data_recebimento.desc(),
            registros.c.id.desc(),
        )

    def nota(self, submissao_id, filtro):
        registros = self._notas(filtro).subquery("notas_filtradas")
        row = self.session.execute(
            select(registros).where(registros.c.id == submissao_id)
        )
        result = row.mappings().first()
        if result is None:
            return None
        result = dict(result)
        result["historico_mensagens"] = (
            self.mensagens_da_nota(result["nota_fiscal_id"])
            if result["nota_fiscal_id"]
            else []
        )
        return result

    def mensagens_da_nota(self, nota_fiscal_id):
        query = (
            select(
                S.id.label("submissao_id"),
                S.status,
                S.data_recebimento,
                E.instancia.label("instance"),
                E.evento_id.label("message_id"),
                E.remote_jid,
                E.message_type,
                E.data_mensagem.label("timestamp"),
                E.criado_em.label("processed_at"),
                E.push_name,
                E.mimetype,
                E.caption,
                E.reenvios,
                E.ultimo_reenvio_em.label("last_replay_at"),
            )
            .join(
                E,
                (S.origem == E.origem)
                & (S.evento_instancia == E.instancia)
                & (S.evento_id == E.evento_id),
            )
            .where(S.nota_fiscal_id == nota_fiscal_id)
            .order_by(E.data_mensagem.desc().nullslast(), S.data_recebimento.desc())
        )
        return [dict(row) for row in self.session.execute(query).mappings()]

    def _contatos(self):
        totals = (
            select(
                S.pessoa_id,
                func.count().label("envios"),
                func.count(func.distinct(S.nota_fiscal_id)).label("notas"),
                func.min(S.data_recebimento).label("primeiro_envio"),
                func.max(S.data_recebimento).label("ultimo_envio"),
            )
            .group_by(S.pessoa_id)
            .subquery()
        )
        ranked = select(
            C.pessoa_id,
            C.tipo,
            C.aceito,
            func.row_number()
            .over(
                partition_by=(C.pessoa_id, C.tipo),
                order_by=(C.data_resposta.desc(), C.id.desc()),
            )
            .label("posicao"),
        ).subquery()
        comunicacao = ranked.alias("comunicacao")
        ligacao = ranked.alias("ligacao")
        return (
            select(
                P.id,
                P.nome,
                P.telefone,
                P.ativo,
                P.criado_em,
                totals.c.primeiro_envio,
                totals.c.ultimo_envio,
                func.coalesce(totals.c.envios, 0).label("envios"),
                func.coalesce(totals.c.notas, 0).label("notas"),
                comunicacao.c.aceito.label("comunicacao"),
                ligacao.c.aceito.label("ligacao"),
            )
            .outerjoin(totals, totals.c.pessoa_id == P.id)
            .outerjoin(
                comunicacao,
                (comunicacao.c.pessoa_id == P.id)
                & (comunicacao.c.tipo == "COMUNICACAO_WHATSAPP")
                & (comunicacao.c.posicao == 1),
            )
            .outerjoin(
                ligacao,
                (ligacao.c.pessoa_id == P.id)
                & (ligacao.c.tipo == "LIGACAO")
                & (ligacao.c.posicao == 1),
            )
        )

    def contatos(self, filtro):
        base = self._contatos().subquery()
        query = select(base)
        if filtro.q:
            query = query.where(
                or_(
                    base.c.nome.icontains(filtro.q, autoescape=True),
                    base.c.telefone.contains(filtro.q, autoescape=True),
                )
            )
        for field in ("ativo", "comunicacao", "ligacao"):
            value = getattr(filtro, field)
            if value is not None:
                query = query.where(base.c[field] == value)
        if filtro.inicio:
            query = query.where(base.c.criado_em >= filtro.inicio)
        if filtro.fim:
            query = query.where(base.c.criado_em < filtro.fim)
        return self.pagina(query, filtro, base.c.criado_em.desc(), base.c.id.desc())

    def contato(self, pessoa_id):
        row = self.session.execute(self._contatos().where(P.id == pessoa_id))
        result = row.mappings().first()
        return dict(result) if result else None

    def consentimentos(self, pessoa_id, filtro):
        query = select(C.tipo, C.aceito, C.origem, C.data_resposta).where(
            C.pessoa_id == pessoa_id
        )
        return self.pagina(query, filtro, C.data_resposta.desc(), C.id.desc())
