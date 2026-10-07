import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import config
from models import Nota, RelatorioDia, ResultadoImportacao


class ApiNotasError(RuntimeError):
    pass


class ApiNotasClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or config.NOTAS_API_URL).rstrip("/")

    def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, Any]:
        request_headers = {"Accept": "application/json"}
        if headers:
            request_headers.update(headers)
        body = None
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            headers=request_headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=config.NOTAS_API_TIMEOUT_SEGUNDOS) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else None
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(raw).get("detail", raw)
            except json.JSONDecodeError:
                detail = raw
            raise ApiNotasError(f"API {exc.code}: {detail}") from exc
        except URLError as exc:
            raise ApiNotasError(f"Não foi possível acessar a API de notas: {exc.reason}") from exc

    def _internal_headers(self) -> dict[str, str]:
        if not config.NOTAS_API_INTERNAL_KEY:
            raise ApiNotasError("Configure NOTAS_API_INTERNAL_KEY para importar TXT.")
        return {"X-Internal-API-Key": config.NOTAS_API_INTERNAL_KEY}

    def _worker_headers(self) -> dict[str, str]:
        if not config.NOTAS_API_WORKER_KEY:
            raise ApiNotasError("Configure WORKER_API_KEY para executar os cadastros.")
        return {"X-Worker-API-Key": config.NOTAS_API_WORKER_KEY}

    def importar_chaves(
        self,
        *,
        caminho_arquivo: str | Path,
        chaves: list[str],
        total_linhas: int,
        total_invalidas: int,
        total_duplicadas_txt: int,
    ) -> ResultadoImportacao:
        data = self._request(
            "POST",
            "/integracao/notas/importar-txt",
            payload={
                "nome_arquivo": Path(caminho_arquivo).name,
                "total_linhas": total_linhas,
                "total_invalidas": total_invalidas,
                "total_duplicadas_txt": total_duplicadas_txt,
                "chaves": chaves,
            },
            headers=self._internal_headers(),
        )[1]
        return ResultadoImportacao(
            arquivo_id=0,
            total_linhas=data["total_linhas"],
            total_validas=data["total_validas"],
            total_invalidas=data["total_invalidas"],
            total_duplicadas=data["total_duplicadas"],
            total_inseridas=data["total_inseridas"],
            total_reativadas=data["total_reativadas"],
            total_ja_existentes=data["total_ja_existentes"],
        )

    def obter_proxima_nota(self) -> Nota | None:
        status, data = self._request("POST", "/worker/notas/proxima", headers=self._worker_headers())
        if status == 204 or data is None:
            return None
        return Nota(
            id=data["nota_id"],
            chave=data["chave"],
            status="PROCESSANDO",
            mensagem="Reservada pela API para processamento",
            arquivo_origem="API",
            data_importacao=None,
            data_cadastro=None,
            tentativa=int(data["tentativa"]),
            criado_em=None,
            atualizado_em=None,
            execucao_id=data["execucao_id"],
        )

    def registrar_resultado(
        self,
        nota: Nota,
        status: str,
        mensagem: str | None = None,
        *,
        valor: float | None = None,
        data_emissao: date | None = None,
        tempo_segundos: float | None = None,
    ) -> None:
        if not nota.execucao_id:
            raise ApiNotasError("A nota não possui execução da API para receber resultado.")
        status_api = {
            "CADASTRADA": "SUCESSO",
            "DUPLICADA": "DUPLICADA",
            "IGNORADA": "IGNORADA",
            "ERRO": "ERRO",
            "AGUARDANDO_CAPTCHA": "AGUARDANDO_CAPTCHA",
            "PAUSADA": "PAUSADA",
        }.get(status, status)
        self._request(
            "POST",
            f"/worker/execucoes/{nota.execucao_id}/resultado",
            payload={
                "status": status_api,
                "mensagem": mensagem,
                "valor": str(Decimal(str(valor))) if valor is not None else None,
                "data_emissao": data_emissao.isoformat() if data_emissao else None,
                "tempo_segundos": str(Decimal(str(tempo_segundos))) if tempo_segundos is not None else None,
            },
            headers=self._worker_headers(),
        )

    def obter_nota(self, nota_id: str | int) -> Nota | None:
        try:
            data = self._request(
                "GET",
                f"/notas/{nota_id}",
                headers=self._worker_headers(),
            )[1]
        except ApiNotasError:
            return None
        return self._nota_from_api(data)

    def listar_notas(self, *, data_inicial: str | None = None, data_final: str | None = None) -> list[Nota]:
        notas: list[Nota] = []
        page = 1
        while True:
            params: dict[str, Any] = {"page": page, "size": 100}
            if data_inicial:
                params["data_inicial"] = data_inicial
            if data_final:
                params["data_final"] = data_final
            data = self._request(
                "GET",
                f"/notas?{urlencode(params)}",
                headers=self._worker_headers(),
            )[1]
            notas.extend(self._nota_from_api(item) for item in data.get("items", []))
            if len(notas) >= data.get("total", len(notas)) or not data.get("items"):
                break
            page += 1
        return notas

    def listar_notas_operacao(self) -> list[Nota]:
        hoje = date.today().isoformat()
        notas = self.listar_notas()
        fila = {"PENDENTE", "PROCESSANDO", "CADASTRANDO", "AGUARDANDO_CAPTCHA", "PAUSADA", "ERRO"}
        return [
            nota for nota in notas
            if nota.status in fila or (nota.criado_em and str(nota.criado_em)[:10] == hoje)
        ]

    def contadores_operacao(self) -> dict[str, int]:
        notas = self.listar_notas()
        fila = {"PENDENTE", "PROCESSANDO", "CADASTRANDO", "AGUARDANDO_CAPTCHA", "PAUSADA", "ERRO"}
        hoje = date.today().isoformat()
        return {
            "fila_pendente": sum(nota.status in fila for nota in notas),
            "cadastradas_hoje": sum(nota.status == "CADASTRADA" and str(nota.data_cadastro or "")[:10] == hoje for nota in notas),
            "cadastradas_total": sum(nota.status == "CADASTRADA" for nota in notas),
        }

    def relatorio_por_dia(self, data_inicial: str, data_final: str) -> list[RelatorioDia]:
        # A API filtra por data de emissão, enquanto o relatório do leitor
        # agrupa pelo cadastro/criação. Buscamos a lista central completa para
        # não perder notas pendentes que ainda não têm data de emissão.
        notas = self.listar_notas()
        por_dia: dict[str, list[Nota]] = {}
        for nota in notas:
            dia = str(nota.data_cadastro or nota.data_emissao_nota or nota.criado_em or "")[:10]
            if data_inicial <= dia <= data_final:
                por_dia.setdefault(dia, []).append(nota)
        linhas: list[RelatorioDia] = []
        for dia, itens in sorted(por_dia.items()):
            cadastradas = [item for item in itens if item.status == "CADASTRADA"]
            duplicadas = [item for item in itens if item.status == "DUPLICADA"]
            erros = [item for item in itens if item.status in {"ERRO", "ERRO_CADASTRO"}]
            ignoradas = [item for item in itens if item.status == "IGNORADA"]
            pendentes = [item for item in itens if item.status in {"PENDENTE", "CADASTRANDO", "PROCESSANDO", "AGUARDANDO_CAPTCHA", "PAUSADA"}]
            linhas.append(RelatorioDia(
                data=dia,
                cadastradas=len(cadastradas),
                valor_cadastradas=sum(float(item.valor or 0) for item in cadastradas),
                tempo_total_segundos=0.0,
                fora_prazo=0,
                valor_fora_prazo=0.0,
                duplicadas=len(duplicadas),
                erros=len(erros),
                valor_erros=sum(float(item.valor or 0) for item in erros),
                ignoradas=len(ignoradas),
                pendentes=len(pendentes),
                total=len(itens),
            ))
        return linhas

    def detalhamento_relatorio(self, data_inicial: str, data_final: str, statuses: tuple[str, ...]) -> list[dict[str, Any]]:
        return [
            {
                "chave": nota.chave,
                "valor": nota.valor,
                "data_emissao_nota": nota.data_emissao_nota,
                "tempo_cadastro_segundos": None,
                "status": nota.status,
                "mensagem": nota.mensagem,
                "arquivo_origem": nota.arquivo_origem,
                "data_importacao": nota.criado_em,
                "data_cadastro": nota.data_cadastro,
                "tentativa": nota.tentativa,
            }
            for nota in self.listar_notas()
            if data_inicial
            <= str(nota.data_cadastro or nota.criado_em or "")[:10]
            <= data_final
            if nota.status in statuses
        ]

    def _nota_from_api(self, data: dict[str, Any]) -> Nota:
        status = {
            "CADASTRANDO": "PROCESSANDO",
            "ERRO_CADASTRO": "ERRO",
        }.get(data.get("status"), data.get("status", ""))
        return Nota(
            id=data["id"],
            chave=data["chave"],
            status=status,
            mensagem=data.get("mensagem_status") or "",
            arquivo_origem="API",
            data_importacao=data.get("criado_em"),
            data_cadastro=data.get("data_cadastro"),
            tentativa=0,
            criado_em=data.get("criado_em"),
            atualizado_em=data.get("atualizado_em"),
            valor=float(data["valor"]) if data.get("valor") is not None else None,
            data_emissao_nota=data.get("data_emissao"),
        )
