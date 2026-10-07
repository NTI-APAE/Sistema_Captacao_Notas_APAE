import logging
import json
import random
import sys
import threading
import time
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

import config
from api_client import ApiNotasClient
from models import (
    Nota,
    STATUS_AGUARDANDO_CAPTCHA,
    STATUS_CADASTRADA,
    STATUS_DUPLICADA,
    STATUS_ERRO,
    STATUS_IGNORADA,
    STATUS_PAUSADA,
    STATUS_PENDENTE,
)


LogCallback = Callable[[str], None]
NotaCallback = Callable[[Nota], None]
EstadoCallback = Callable[[str], None]
ConclusaoCallback = Callable[[dict[str, object]], None]


class ConfiguracaoAutomacaoIncompleta(RuntimeError):
    pass


class AutomacaoNotaLegal:
    """
    Automacao assistida do Nota Legal.

    O navegador sempre abre em modo visivel. Login, navegacao ate a tela correta
    e resolucao de CAPTCHA/validacoes manuais ficam sob responsabilidade do
    usuario.
    """

    def __init__(
        self,
        *,
        db_path: Path | None = None,
        log_callback: Optional[LogCallback] = None,
        nota_callback: Optional[NotaCallback] = None,
        estado_callback: Optional[EstadoCallback] = None,
        conclusao_callback: Optional[ConclusaoCallback] = None,
        api_client: ApiNotasClient | None = None,
    ) -> None:
        self.db_path = db_path
        self.api_client = api_client or ApiNotasClient()
        self.log_callback = log_callback
        self.nota_callback = nota_callback
        self.estado_callback = estado_callback
        self.conclusao_callback = conclusao_callback
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.clear()
        self._rodando = False
        self._logger = logging.getLogger(__name__)
        self._diagnostico_instalado = False
        self._diagnostico_contador = 0
        self._ultimo_cadastro_em = 0.0
        self._notas_processadas_lote = 0
        self._inicio_processamento_em: float | None = None
        self._conclusao_notificada = False
        self._notas_tentadas_sessao = 0
        self._notas_cadastradas_sessao = 0
        self._notas_duplicadas_sessao = 0
        self._notas_ignoradas_sessao = 0
        self._notas_erros_sessao = 0
        self._tempo_total_notas_segundos = 0.0
        self._nota_em_processamento: Nota | None = None

    @property
    def rodando(self) -> bool:
        return self._rodando

    @property
    def pausada(self) -> bool:
        return not self._pause_event.is_set()

    def iniciar(self) -> None:
        if self._thread and self._thread.is_alive():
            self._log("A automacao ja esta em execucao.")
            return

        self._stop_event.clear()
        self._pause_event.clear()
        self._thread = threading.Thread(target=self._executar, daemon=True)
        self._thread.start()

    def alternar_pausa(self) -> None:
        if self._pause_event.is_set():
            self.pausar()
        else:
            self.continuar()

    def pausar(self) -> None:
        if not self._rodando:
            self._log("Nao ha automacao em execucao para pausar.")
            return
        if not self._pause_event.is_set():
            self._log("A automacao ja esta pausada.")
            return
        self._pause_event.clear()
        self._estado("PAUSADA")
        self._log("Automacao pausada pelo usuario.")

    def continuar(self) -> None:
        if not self._rodando:
            self._log("Nao ha automacao em execucao para continuar.")
            return
        if self._pause_event.is_set():
            self._log("A automacao ja esta em execucao.")
            return
        self._pause_event.set()
        self._estado("EXECUTANDO")
        self._log("Automacao continuando.")

    def parar(self) -> None:
        self._stop_event.set()
        self._pause_event.set()
        self._log("Solicitada parada da automacao.")

    def _executar(self) -> None:
        self._rodando = True
        self._estado("INICIANDO")
        try:
            self._validar_configuracao_minima()
            self._validar_playwright_empacotado()
            with sync_playwright() as playwright:
                try:
                    browser = playwright.chromium.launch(
                        headless=False,
                        slow_mo=getattr(config, "SLOW_MO_MS", 0),
                    )
                except Exception as erro_chromium:
                    if not getattr(config, "USAR_CHROME_INSTALADO_FALLBACK", True):
                        raise
                    self._log(
                        "Chromium do Playwright não está disponível; "
                        "tentando usar o Google Chrome instalado."
                    )
                    try:
                        browser = playwright.chromium.launch(
                            channel=getattr(config, "PLAYWRIGHT_CHANNEL", "chrome"),
                            headless=False,
                            slow_mo=getattr(config, "SLOW_MO_MS", 0),
                        )
                    except Exception:
                        raise erro_chromium
                page = browser.new_page()
                page.set_default_timeout(config.TIMEOUT_PADRAO_MS)
                self._instalar_monitoramento_pagina(page)

                if config.URL_LOGIN:
                    page.goto(config.URL_LOGIN)
                    self._preparar_login_assistido(page)
                else:
                    page.goto("about:blank")

                self._estado("AGUARDANDO_LOGIN")
                self._log(
                    "Navegador aberto. Se o login foi preenchido, resolva o CAPTCHA, clique em "
                    "Acessar e depois clique em Continuar para iniciar os cadastros."
                )
                self._aguardar_continuacao()

                while not self._stop_event.is_set():
                    self._aguardar_continuacao()
                    nota = self.api_client.obter_proxima_nota()
                    if not nota:
                        self._estado("PROCESSO_CONCLUIDO")
                        self._log(
                            "Processo concluido: nao ha notas PENDENTE ou ERRO abaixo do limite de "
                            "tentativas para cadastrar. Importe novas notas ou confira a aba Relatorios."
                        )
                        self._notificar_conclusao()
                        self._pause_event.clear()
                        continue

                    self._conclusao_notificada = False
                    if self._inicio_processamento_em is None:
                        self._inicio_processamento_em = time.perf_counter()
                    self._estado("EXECUTANDO")
                    status_final, duracao_segundos = self._processar_nota(page, nota)
                    self._registrar_resultado_sessao(status_final, duracao_segundos)
                    self._notas_processadas_lote += 1
                    self._aplicar_pausa_entre_notas()

                try:
                    browser.close()
                except Exception:
                    pass
        except ConfiguracaoAutomacaoIncompleta as exc:
            self._log(str(exc), error=True)
            self._estado("CONFIGURACAO_INCOMPLETA")
        except Exception as exc:
            self._log(f"Falha geral na automacao: {exc}", error=True)
            self._estado("ERRO")
        finally:
            self._rodando = False
            self._estado("FINALIZADA")

    def _validar_configuracao_minima(self) -> None:
        faltando = []
        if not config.CAMPO_TIPO_NOTA:
            faltando.append("CAMPO_TIPO_NOTA")
        if not config.CAMPO_CHAVE:
            faltando.append("CAMPO_CHAVE")
        if not config.BOTAO_SALVAR:
            faltando.append("BOTAO_SALVAR")
        if faltando:
            raise ConfiguracaoAutomacaoIncompleta(
                "Configure os seletores em config.py antes de iniciar a automacao: "
                + ", ".join(faltando)
            )

    def _validar_playwright_empacotado(self) -> None:
        if not getattr(sys, "frozen", False):
            return

        browsers_dir = getattr(config, "PLAYWRIGHT_BROWSERS_DIR", None)
        if not browsers_dir or not Path(browsers_dir).exists():
            raise ConfiguracaoAutomacaoIncompleta(
                "A pasta ms-playwright nao foi encontrada ao lado do executavel. "
                "Extraia o ZIP completo antes de abrir o sistema e nao envie somente o arquivo .exe."
            )

        chrome_encontrado = any(Path(browsers_dir).glob("chromium-*/chrome-win*/chrome.exe"))
        if not chrome_encontrado:
            raise ConfiguracaoAutomacaoIncompleta(
                "O Chromium do Playwright nao foi encontrado dentro da pasta ms-playwright. "
                "Gere novamente o ZIP de distribuicao e copie a pasta inteira para a outra maquina."
            )

    def _preparar_login_assistido(self, page: Page) -> None:
        if not getattr(config, "PREENCHER_LOGIN_AUTOMATICO", False):
            return

        try:
            page.wait_for_load_state("domcontentloaded", timeout=5000)
        except PlaywrightTimeoutError:
            pass

        espera_ms = max(0, int(getattr(config, "ESPERA_ANTES_PREENCHER_LOGIN_MS", 0)))
        if espera_ms:
            self._log(f"Aguardando {espera_ms / 1000:.1f}s para a pagina de login carregar.")
            page.wait_for_timeout(espera_ms)

        cpf_ok = False
        senha_ok = False
        perfil_ok = False

        cpf_cnpj = getattr(config, "LOGIN_CPF_CNPJ", "").strip()
        if cpf_cnpj:
            cpf_ok = self._preencher_campo_login(
                page,
                self._seletores_login_cpf_cnpj(),
                cpf_cnpj,
                "CPF/CNPJ",
            )

        senha = getattr(config, "LOGIN_SENHA", "")
        if senha:
            senha_ok = self._preencher_campo_login(
                page,
                self._seletores_login_senha(),
                senha,
                "Senha de Acesso",
            )

        perfil_ok = self._selecionar_perfil_login(page)

        if any((cpf_ok, senha_ok, perfil_ok)):
            partes = []
            if cpf_ok:
                partes.append("CPF/CNPJ")
            if senha_ok:
                partes.append("senha")
            if perfil_ok:
                partes.append("perfil")
            self._log(
                "Login assistido preparado: "
                + ", ".join(partes)
                + ". Resolva o CAPTCHA e clique em Acessar manualmente."
            )
        else:
            self._log(
                "Nao consegui identificar automaticamente os campos de login. "
                "Preencha o login manualmente, resolva o CAPTCHA e clique em Acessar."
            )

    def _seletores_login_cpf_cnpj(self) -> list[str]:
        seletores = []
        if getattr(config, "CAMPO_LOGIN_CPF_CNPJ", ""):
            seletores.append(config.CAMPO_LOGIN_CPF_CNPJ)
        seletores.extend(
            [
                "xpath=//input[contains(translate(@id, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'cpf')]",
                "xpath=//input[contains(translate(@name, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'cpf')]",
                "xpath=//*[contains(normalize-space(.), 'Informe o CPF/CNPJ')]/following::input[not(translate(@type, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='hidden')][1]",
                "xpath=//*[contains(normalize-space(.), 'CPF/CNPJ')]/following::input[not(translate(@type, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='hidden')][1]",
                "xpath=(//input[not(translate(@type, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='hidden') and not(translate(@type, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='radio') and not(translate(@type, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='checkbox') and not(translate(@type, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='button') and not(translate(@type, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='submit')])[1]",
            ]
        )
        return seletores

    def _seletores_login_senha(self) -> list[str]:
        seletores = []
        if getattr(config, "CAMPO_LOGIN_SENHA", ""):
            seletores.append(config.CAMPO_LOGIN_SENHA)
        seletores.extend(
            [
                "xpath=//input[translate(@type, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='password']",
                "xpath=//input[contains(translate(@id, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'senha')]",
                "xpath=//input[contains(translate(@name, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'senha')]",
                "xpath=//*[contains(normalize-space(.), 'Senha de Acesso')]/following::input[not(translate(@type, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='hidden')][1]",
                "xpath=(//input[not(translate(@type, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='hidden') and not(translate(@type, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='radio') and not(translate(@type, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='checkbox') and not(translate(@type, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='button') and not(translate(@type, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='submit')])[2]",
            ]
        )
        return seletores

    def _preencher_campo_login(
        self,
        page: Page,
        seletores: list[str],
        valor: str,
        nome_campo: str,
    ) -> bool:
        timeout_campo = max(500, int(getattr(config, "TIMEOUT_CAMPO_LOGIN_MS", 3000)))
        for seletor in seletores:
            try:
                campo = page.locator(seletor).first
                campo.wait_for(state="visible", timeout=timeout_campo)
                if not campo.is_enabled(timeout=500):
                    continue
                campo.fill(valor, timeout=timeout_campo)
                self._disparar_eventos_campo(campo)
                self._log(f"{nome_campo} preenchido automaticamente.")
                return True
            except Exception:
                continue
        return False

    def _disparar_eventos_campo(self, campo) -> None:
        try:
            campo.evaluate(
                """
                (elemento) => {
                    elemento.dispatchEvent(new Event('input', { bubbles: true }));
                    elemento.dispatchEvent(new Event('change', { bubbles: true }));
                    elemento.dispatchEvent(new Event('blur', { bubbles: true }));
                }
                """
            )
        except Exception:
            pass

    def _selecionar_perfil_login(self, page: Page) -> bool:
        perfil = getattr(config, "LOGIN_PERFIL_TEXTO", "").strip()
        if not perfil:
            return False

        seletores = []
        if getattr(config, "RADIO_LOGIN_PERFIL", ""):
            seletores.append(config.RADIO_LOGIN_PERFIL)

        textos = [perfil, *getattr(config, "LOGIN_PERFIL_ALIASES", [])]
        for texto in textos:
            seletores.extend(
                [
                    f"xpath=//label[contains(normalize-space(.), '{texto}')]//input[@type='radio']",
                    f"xpath=//label[contains(normalize-space(.), '{texto}')]/preceding::input[@type='radio'][1]",
                    f"xpath=//*[normalize-space(.)='{texto}']/preceding::input[@type='radio'][1]",
                ]
            )

        for texto in textos:
            try:
                page.get_by_label(texto, exact=True).check(timeout=1200)
                self._log(f"Perfil de login selecionado: {texto}.")
                return True
            except Exception:
                pass

        for seletor in seletores:
            try:
                radio = page.locator(seletor).first
                radio.wait_for(state="attached", timeout=1200)
                try:
                    radio.check(timeout=1200, force=True)
                except Exception:
                    radio.click(timeout=1200, force=True)
                self._log(f"Perfil de login selecionado: {perfil}.")
                return True
            except Exception:
                continue

        try:
            selecionado = page.evaluate(
                """
                ({ perfil, aliases }) => {
                    const normalizar = (valor) => (valor || '')
                        .normalize('NFD')
                        .replace(/[\\u0300-\\u036f]/g, '')
                        .toLowerCase()
                        .replace(/\\s+/g, ' ')
                        .trim();
                    const alvos = [perfil, ...(aliases || [])].map(normalizar).filter(Boolean);
                    const contemAlvo = (texto) => {
                        const normalizado = normalizar(texto);
                        return alvos.some((alvo) => normalizado.includes(alvo));
                    };
                    const selecionar = (radio) => {
                        if (!radio || radio.disabled) {
                            return false;
                        }
                        radio.checked = true;
                        radio.click();
                        radio.dispatchEvent(new Event('input', { bubbles: true }));
                        radio.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    };

                    for (const label of Array.from(document.querySelectorAll('label'))) {
                        if (!contemAlvo(label.textContent)) {
                            continue;
                        }
                        const control = label.control || label.querySelector('input[type="radio"]');
                        if (selecionar(control)) {
                            return true;
                        }
                        const id = label.getAttribute('for');
                        if (id && selecionar(document.getElementById(id))) {
                            return true;
                        }
                    }

                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                    let node = walker.nextNode();
                    while (node) {
                        if (contemAlvo(node.textContent)) {
                            const elemento = node.parentElement;
                            const label = elemento?.closest?.('label');
                            if (label) {
                                const control = label.control || label.querySelector('input[type="radio"]');
                                if (selecionar(control)) {
                                    return true;
                                }
                            }

                            const radios = Array.from(document.querySelectorAll('input[type="radio"]'));
                            const anterior = radios
                                .filter((radio) => radio.compareDocumentPosition(elemento) & Node.DOCUMENT_POSITION_FOLLOWING)
                                .pop();
                            if (selecionar(anterior)) {
                                return true;
                            }
                        }
                        node = walker.nextNode();
                    }
                    return false;
                }
                """,
                {
                    "perfil": perfil,
                    "aliases": getattr(config, "LOGIN_PERFIL_ALIASES", []),
                },
            )
            if selecionado:
                self._log(f"Perfil de login selecionado: {perfil}.")
            return bool(selecionado)
        except Exception:
            return False

    def _processar_nota(self, page: Page, nota: Nota) -> tuple[str | None, float]:
        inicio_tentativa = time.perf_counter()
        data_emissao_nota: date | None = None
        self._nota_em_processamento = nota
        self._log(f"Processando nota {nota.chave}.")
        try:
            self._voltar_se_estiver_em_resultado(page)
            self._abrir_tela_cadastrar_notas(page)
            if self._captcha_presente(page):
                self._pausar_por_captcha(nota)

            self._aguardar_continuacao()
            self._atualizar_status_nota(
                nota.id,
                STATUS_PENDENTE,
                "Processando nota",
                db_path=self.db_path,
            )
            self._notificar_nota(nota.id)

            self._selecionar_tipo_nfce(page)
            page.wait_for_selector(config.CAMPO_CHAVE, state="visible")
            page.fill(config.CAMPO_CHAVE, nota.chave)
            page.locator(config.CAMPO_CHAVE).first.evaluate(
                """
                (campo) => {
                    campo.dispatchEvent(new Event('input', { bubbles: true }));
                    campo.dispatchEvent(new Event('change', { bubbles: true }));
                    campo.dispatchEvent(new Event('blur', { bubbles: true }));
                }
                """
            )

            if config.BOTAO_CONSULTAR:
                page.click(config.BOTAO_CONSULTAR)
                self._aguardar_carregamento_curto(page)
            else:
                page.wait_for_timeout(getattr(config, "ESPERA_APOS_DIGITAR_CHAVE_MS", 250))

            if self._captcha_presente(page):
                self._pausar_por_captcha(nota)

            if config.CAMPO_CONFIRMACAO_AUTOPREENCHIMENTO:
                try:
                    self._aguardar_campo_com_valor(
                        page,
                        config.CAMPO_CONFIRMACAO_AUTOPREENCHIMENTO,
                        "campo de confirmacao do autopreenchimento",
                    )
                except PlaywrightTimeoutError:
                    self._log("Nao foi possivel confirmar autopreenchimento antes de cadastrar.")

            espera_validacao = max(0, int(getattr(config, "ESPERA_APOS_AUTOPREENCHIMENTO_MS", 0)))
            if espera_validacao:
                page.wait_for_timeout(espera_validacao)

            valor_nota = self._ler_valor_nota(page)
            if valor_nota is not None:
                self._log(f"Valor da nota capturado: {self._formatar_valor(valor_nota)}")

            data_emissao_nota = self._ler_data_emissao_nota(page)
            if data_emissao_nota is not None:
                self._log(f"Data de emissao capturada: {self._formatar_data(data_emissao_nota)}")
            else:
                self._log("Data de emissao nao foi capturada; seguindo com o cadastro normal.")

            mensagem_validacao = self._ler_mensagem_validacao_formulario(page)
            if mensagem_validacao:
                if self._requisicoes_excessivas_detectadas(mensagem_validacao):
                    self._pausar_por_requisicoes_excessivas(nota, mensagem_validacao)
                    return None, self._duracao_tentativa(inicio_tentativa)

                status_validacao = self._classificar_retorno(mensagem_validacao)
                if status_validacao in {STATUS_DUPLICADA, STATUS_IGNORADA, STATUS_ERRO}:
                    duracao_segundos = self._duracao_tentativa(inicio_tentativa)
                    self._atualizar_status_nota(
                        nota.id,
                        status_validacao,
                        mensagem_validacao,
                        incrementar_tentativa=status_validacao == STATUS_ERRO,
                        valor=valor_nota,
                        data_emissao_nota=data_emissao_nota.isoformat() if data_emissao_nota else None,
                        tempo_cadastro_segundos=duracao_segundos,
                        db_path=self.db_path,
                    )
                    self._notificar_nota(nota.id)
                    self._log(
                        f"Mensagem do portal antes do cadastro: {self._resumir_mensagem(mensagem_validacao)}"
                    )
                    self._log(
                        f"Nota {nota.chave} finalizada com status {status_validacao} em "
                        f"{self._formatar_duracao(duracao_segundos)}."
                    )
                    self._voltar_se_estiver_em_resultado(page)
                    return status_validacao, duracao_segundos

            if data_emissao_nota is not None and self._data_emissao_fora_prazo(data_emissao_nota):
                duracao_segundos = self._duracao_tentativa(inicio_tentativa)
                mensagem_fora_prazo = self._mensagem_nota_fora_prazo(data_emissao_nota)
                self._atualizar_status_nota(
                    nota.id,
                    STATUS_IGNORADA,
                    mensagem_fora_prazo,
                    valor=valor_nota,
                    data_emissao_nota=data_emissao_nota.isoformat(),
                    tempo_cadastro_segundos=duracao_segundos,
                    db_path=self.db_path,
                )
                self._notificar_nota(nota.id)
                self._log(
                    f"Nota {nota.chave} ignorada em {self._formatar_duracao(duracao_segundos)}: "
                    f"{mensagem_fora_prazo}"
                )
                self._voltar_se_estiver_em_resultado(page)
                return STATUS_IGNORADA, duracao_segundos

            self._salvar_diagnostico_pagina(page, nota, "antes_cadastrar")
            self._acionar_cadastro_e_aguardar_resultado(page)
            self._salvar_diagnostico_pagina(page, nota, "apos_resultado")

            mensagem = self._ler_mensagem(page)
            if self._requisicoes_excessivas_detectadas(mensagem):
                self._pausar_por_requisicoes_excessivas(nota, mensagem)
                return None, self._duracao_tentativa(inicio_tentativa)

            status = self._classificar_retorno(mensagem)
            mensagem = self._mensagem_com_limite_se_necessario(nota, status, mensagem)
            duracao_segundos = self._duracao_tentativa(inicio_tentativa)
            self._log(f"Mensagem de retorno: {self._resumir_mensagem(mensagem)}")
            self._atualizar_status_nota(
                nota.id,
                status,
                mensagem or "Processada pela automacao",
                incrementar_tentativa=True,
                definir_data_cadastro=status == STATUS_CADASTRADA,
                valor=valor_nota,
                data_emissao_nota=data_emissao_nota.isoformat() if data_emissao_nota else None,
                tempo_cadastro_segundos=duracao_segundos,
                db_path=self.db_path,
            )
            self._notificar_nota(nota.id)
            self._log(
                f"Nota {nota.chave} finalizada com status {status} em "
                f"{self._formatar_duracao(duracao_segundos)}."
            )
            self._voltar_se_estiver_em_resultado(page)
            return status, duracao_segundos
        except Exception as exc:
            mensagem_tela = self._ler_texto_body(page)
            if self._requisicoes_excessivas_detectadas(mensagem_tela):
                self._pausar_por_requisicoes_excessivas(nota, mensagem_tela)
                return None, self._duracao_tentativa(inicio_tentativa)

            duracao_segundos = self._duracao_tentativa(inicio_tentativa)
            mensagem_erro = self._mensagem_com_limite_se_necessario(
                nota,
                STATUS_ERRO,
                f"Erro ao processar: {exc}",
            )
            self._atualizar_status_nota(
                nota.id,
                STATUS_ERRO,
                mensagem_erro,
                incrementar_tentativa=True,
                data_emissao_nota=data_emissao_nota.isoformat() if data_emissao_nota else None,
                tempo_cadastro_segundos=duracao_segundos,
                db_path=self.db_path,
            )
            self._notificar_nota(nota.id)
            self._log(
                f"Erro na nota {nota.chave} apos {self._formatar_duracao(duracao_segundos)}: {mensagem_erro}",
                error=True,
            )
            self._salvar_diagnostico_pagina(page, nota, "erro")
            self._voltar_se_estiver_em_resultado(page)
            return STATUS_ERRO, duracao_segundos

    def _duracao_tentativa(self, inicio_tentativa: float) -> float:
        return round(max(0.0, time.perf_counter() - inicio_tentativa), 2)

    def _registrar_resultado_sessao(self, status: str | None, duracao_segundos: float) -> None:
        if not status:
            return
        self._notas_tentadas_sessao += 1
        self._tempo_total_notas_segundos += duracao_segundos
        if status == STATUS_CADASTRADA:
            self._notas_cadastradas_sessao += 1
        elif status == STATUS_DUPLICADA:
            self._notas_duplicadas_sessao += 1
        elif status == STATUS_IGNORADA:
            self._notas_ignoradas_sessao += 1
        elif status == STATUS_ERRO:
            self._notas_erros_sessao += 1

    def _notificar_conclusao(self) -> None:
        if self._conclusao_notificada:
            return
        self._conclusao_notificada = True
        tempo_total = 0.0
        if self._inicio_processamento_em is not None:
            tempo_total = max(0.0, time.perf_counter() - self._inicio_processamento_em)
        resumo = {
            "tentadas": self._notas_tentadas_sessao,
            "cadastradas": self._notas_cadastradas_sessao,
            "duplicadas": self._notas_duplicadas_sessao,
            "ignoradas": self._notas_ignoradas_sessao,
            "erros": self._notas_erros_sessao,
            "tempo_total_segundos": round(tempo_total, 2),
            "tempo_notas_segundos": round(self._tempo_total_notas_segundos, 2),
        }
        self._log(
            "Resumo da automacao: "
            f"{resumo['tentadas']} tentativa(s), "
            f"{resumo['cadastradas']} cadastrada(s), "
            f"tempo total {self._formatar_duracao(float(resumo['tempo_total_segundos']))}."
        )
        if self.conclusao_callback:
            self.conclusao_callback(resumo)

    def _mensagem_com_limite_se_necessario(self, nota: Nota, status: str, mensagem: str) -> str:
        if status != STATUS_ERRO:
            return mensagem

        if not (mensagem or "").startswith("Erro ao processar:"):
            return mensagem

        tentativa_atual = nota.tentativa + 1
        if tentativa_atual < config.MAX_TENTATIVAS_CADASTRO:
            return mensagem

        sufixo = (
            f"Limite de {config.MAX_TENTATIVAS_CADASTRO} tentativas atingido. "
            "A automacao vai pular esta nota nas proximas verificacoes."
        )
        mensagem = mensagem or "Erro ao cadastrar nota."
        if sufixo in mensagem:
            return mensagem
        return f"{mensagem} | {sufixo}"

    def _acionar_cadastro_e_aguardar_resultado(self, page: Page) -> None:
        ultimo_erro: Exception | None = None
        seletores = [config.BOTAO_SALVAR, *getattr(config, "BOTAO_SALVAR_FALLBACKS", [])]
        timeout_clique = getattr(config, "TIMEOUT_CLIQUE_MS", 3000)

        if getattr(config, "USAR_A4J_DIRETO_CADASTRAR", False):
            try:
                self._log("Enviando cadastro diretamente pelo A4J do botao Cadastrar.")
                self._submeter_cadastro_a4j_direto(page)
                page.wait_for_timeout(getattr(config, "ESPERA_APOS_CLIQUE_CADASTRAR_MS", 1200))
                self._aguardar_resultado_cadastro(page)
                return
            except Exception as exc:
                ultimo_erro = exc
                self._log(f"Envio direto A4J nao retornou resultado; tentando clique normal: {exc}")

        for seletor in [item for item in seletores if item]:
            clicou = False
            try:
                botao = page.locator(seletor).first
                botao.wait_for(state="visible", timeout=timeout_clique)
                self._log(f"Clicando no botao Cadastrar usando seletor: {seletor}")
                botao.click(timeout=timeout_clique)
                clicou = True
                page.wait_for_timeout(getattr(config, "ESPERA_APOS_CLIQUE_CADASTRAR_MS", 1200))
                self._aguardar_resultado_cadastro(page)
                return
            except PlaywrightTimeoutError as exc:
                ultimo_erro = exc
                if clicou and self._formulario_ainda_visivel(page):
                    self._log(f"Cadastro sem resposta apos clique em {seletor}; seguindo sem repetir fallbacks lentos.")
                    raise
            except Exception as exc:
                ultimo_erro = exc
                self._log(f"Clique normal falhou: {exc}")

            clicou = False
            try:
                botao = page.locator(seletor).first
                self._log(f"Tentando clique forcado no botao Cadastrar: {seletor}")
                botao.click(timeout=timeout_clique, force=True)
                clicou = True
                page.wait_for_timeout(getattr(config, "ESPERA_APOS_CLIQUE_CADASTRAR_MS", 1200))
                self._aguardar_resultado_cadastro(page)
                return
            except PlaywrightTimeoutError as exc:
                ultimo_erro = exc
                if clicou and self._formulario_ainda_visivel(page):
                    self._log(f"Cadastro sem resposta apos clique forcado em {seletor}; seguindo sem repetir fallbacks lentos.")
                    raise
            except Exception as exc:
                ultimo_erro = exc
                self._log(f"Clique forcado falhou: {exc}")

            clicou = False
            try:
                botao = page.locator(seletor).first
                self._log(f"Tentando clique JavaScript no botao Cadastrar: {seletor}")
                botao.evaluate(
                    """
                    (elemento) => {
                        elemento.dispatchEvent(new MouseEvent('click', {
                            bubbles: true,
                            cancelable: true,
                            view: window
                        }));
                    }
                    """
                )
                clicou = True
                page.wait_for_timeout(getattr(config, "ESPERA_APOS_CLIQUE_CADASTRAR_MS", 1200))
                self._aguardar_resultado_cadastro(page)
                return
            except PlaywrightTimeoutError as exc:
                ultimo_erro = exc
                if clicou and self._formulario_ainda_visivel(page):
                    self._log(f"Cadastro sem resposta apos clique JavaScript em {seletor}; seguindo para proxima tentativa da nota.")
                    raise
            except Exception as exc:
                ultimo_erro = exc
                self._log(f"Clique JavaScript falhou: {exc}")

        raise RuntimeError(f"Nao foi possivel clicar no botao Cadastrar: {ultimo_erro}")

    def _submeter_cadastro_a4j_direto(self, page: Page) -> None:
        self._aguardar_intervalo_minimo_entre_cadastros()
        page.evaluate(
            """
            ({ formId, botaoId }) => {
                if (!window.A4J || !A4J.AJAX || typeof A4J.AJAX.Submit !== 'function') {
                    throw new Error('A4J.AJAX.Submit nao esta disponivel na pagina.');
                }
                const botao = document.getElementById(botaoId);
                if (!botao) {
                    throw new Error(`Botao nao encontrado: ${botaoId}`);
                }
                if (botao.disabled) {
                    throw new Error(`Botao desabilitado: ${botaoId}`);
                }
                const evento = new MouseEvent('click', {
                    bubbles: true,
                    cancelable: true,
                    view: window
                });
                Object.defineProperty(evento, 'target', { value: botao, enumerable: true });
                Object.defineProperty(evento, 'srcElement', { value: botao, enumerable: true });
                A4J.AJAX.Submit(formId, evento, {
                    similarityGroupingId: botaoId,
                    parameters: { [botaoId]: botaoId },
                    eventsQueue: '1'
                });
            }
            """,
            {
                "formId": getattr(config, "A4J_FORM_CADASTRAR", "form1"),
                "botaoId": getattr(config, "A4J_BOTAO_CADASTRAR", "form1:j_id97"),
            },
        )
        self._ultimo_cadastro_em = time.time()

    def _aguardar_intervalo_minimo_entre_cadastros(self) -> None:
        intervalo = getattr(config, "INTERVALO_MINIMO_ENTRE_CADASTROS_SEGUNDOS", 0)
        if intervalo <= 0 or self._ultimo_cadastro_em <= 0:
            return
        restante = intervalo - (time.time() - self._ultimo_cadastro_em)
        if restante > 0:
            self._log(f"Aguardando {restante:.1f}s para respeitar intervalo minimo entre cadastros.")
            self._dormir_respeitando_pausa(restante)

    def _aguardar_resultado_cadastro(self, page: Page) -> None:
        page.wait_for_function(
            """
            () => {
                const normalizar = (valor) => (valor || '')
                    .normalize('NFD')
                    .replace(/[\\u0300-\\u036f]/g, '')
                    .toLowerCase();
                const texto = normalizar(document.body?.innerText || '');
                const temMensagem = [
                    'nota cadastrada',
                    'operacao realizada com sucesso',
                    'numero da chave invalida',
                    'chave invalida',
                    'esta nota ja foi doada',
                    'nota ja foi doada',
                    'foi doada',
                    'verificar novamente',
                    'nao podem ter sido emitidas',
                    'nao pode ter sido emitida',
                    'mais de 2 meses'
                ].some(item => texto.includes(item));
                const carregando = texto.includes('carregando');
                return temMensagem && !carregando;
            }
            """,
            timeout=getattr(config, "TIMEOUT_RESULTADO_CADASTRO_MS", 30000),
        )

    def _formulario_ainda_visivel(self, page: Page) -> bool:
        try:
            return page.locator(config.BOTAO_SALVAR).first.is_visible(timeout=500)
        except Exception:
            return False

    def _aguardar_carregamento_curto(self, page: Page) -> None:
        try:
            page.wait_for_load_state("domcontentloaded", timeout=3000)
        except PlaywrightTimeoutError:
            return

    def _voltar_se_estiver_em_resultado(self, page: Page) -> None:
        seletor = getattr(config, "BOTAO_VOLTAR_RESULTADO", "")
        if not seletor:
            return
        try:
            texto = self._normalizar_texto(self._ler_texto_body(page))
            esta_em_resultado = any(
                trecho in texto
                for trecho in (
                    "nota cadastrada",
                    "operacao realizada com sucesso",
                    "numero da chave invalida",
                    "chave invalida",
                    "esta nota ja foi doada",
                    "nota ja foi doada",
                    "atencao",
                )
            )
            if not esta_em_resultado:
                return
            botao = page.locator(seletor).first
            if not botao.is_visible(timeout=1000):
                return
            botao.click()
            self._aguardar_carregamento_curto(page)
            self._log("Retornando da pagina de resultado para o formulario.")
        except Exception:
            return

    def _requisicoes_excessivas_detectadas(self, mensagem: str) -> bool:
        texto = self._normalizar_texto(mensagem)
        return (
            "requisicoes excessivas" in texto
            or "sessao encerrada" in texto
            or ("excessivas" in texto and "encerrada" in texto)
        )

    def _pausar_por_requisicoes_excessivas(self, nota: Nota, mensagem: str) -> None:
        mensagem = mensagem or "Requisicoes excessivas detectadas. Sessao encerrada."
        self._atualizar_status_nota(
            nota.id,
            STATUS_PAUSADA,
            self._resumir_mensagem(mensagem, 800),
            db_path=self.db_path,
        )
        self._notificar_nota(nota.id)

        pausa = getattr(config, "PAUSA_REQUISICOES_EXCESSIVAS_SEGUNDOS", 300)
        self._estado("SESSAO_ENCERRADA")
        self._log(
            "O portal detectou requisicoes excessivas e encerrou a sessao. "
            f"A automacao vai pausar por {pausa:.0f}s. Faca login novamente no navegador e "
            "clique em Continuar quando a tela de cadastro estiver pronta."
        )
        fim = time.time() + max(0, pausa)
        while not self._stop_event.is_set() and time.time() < fim:
            time.sleep(min(0.5, max(0.0, fim - time.time())))

        self._pause_event.clear()
        self._aguardar_continuacao()

        self._atualizar_status_nota(
            nota.id,
            STATUS_PENDENTE,
            "Retomando apos pausa por requisicoes excessivas.",
            db_path=self.db_path,
        )
        self._notificar_nota(nota.id)

    def _aplicar_pausa_entre_notas(self) -> None:
        if self._stop_event.is_set():
            return

        pausa_min = getattr(config, "PAUSA_ENTRE_NOTAS_MIN_SEGUNDOS", None)
        pausa_max = getattr(config, "PAUSA_ENTRE_NOTAS_MAX_SEGUNDOS", None)
        if pausa_min is None or pausa_max is None:
            pausa = getattr(config, "PAUSA_ENTRE_NOTAS_SEGUNDOS", 0)
        else:
            pausa = random.uniform(float(pausa_min), float(pausa_max))

        lote = getattr(config, "PAUSA_A_CADA_N_NOTAS", 0)
        if lote and self._notas_processadas_lote >= lote:
            pausa_lote = random.uniform(
                float(getattr(config, "PAUSA_LOTE_MIN_SEGUNDOS", 60)),
                float(getattr(config, "PAUSA_LOTE_MAX_SEGUNDOS", 120)),
            )
            self._notas_processadas_lote = 0
            self._log(f"Pausa de lote por {pausa_lote:.1f}s para reduzir requisicoes.")
            self._dormir_respeitando_pausa(pausa_lote)

        if pausa > 0:
            self._log(f"Aguardando {pausa:.1f}s antes da proxima nota.")
            self._dormir_respeitando_pausa(pausa)

    def _dormir_respeitando_pausa(self, segundos: float) -> None:
        fim = time.time() + max(0.0, segundos)
        while not self._stop_event.is_set() and time.time() < fim:
            if not self._pause_event.is_set():
                self._aguardar_continuacao()
            time.sleep(min(0.25, max(0.0, fim - time.time())))

    def _instalar_monitoramento_pagina(self, page: Page) -> None:
        if not getattr(config, "DIAGNOSTICO_ATIVO", False) or self._diagnostico_instalado:
            return
        self._diagnostico_instalado = True
        self._garantir_diretorio_diagnostico()

        page.on("console", lambda msg: self._registrar_diagnostico_evento("console", f"{msg.type}: {msg.text}"))
        page.on("pageerror", lambda exc: self._registrar_diagnostico_evento("pageerror", str(exc)))
        page.on(
            "requestfailed",
            lambda req: self._registrar_diagnostico_evento(
                "requestfailed",
                f"{req.method} {req.url} | {req.failure}",
            ),
        )
        page.on(
            "response",
            lambda resp: self._registrar_resposta_diagnostico(resp.url, resp.status),
        )

    def _registrar_resposta_diagnostico(self, url: str, status: int) -> None:
        if status >= 400 or any(trecho in url.lower() for trecho in ("doarnotas", "a4j", "ajax", "jsf")):
            self._registrar_diagnostico_evento("response", f"{status} {url}")

    def _salvar_diagnostico_pagina(self, page: Page, nota: Nota, etapa: str) -> None:
        if not getattr(config, "DIAGNOSTICO_ATIVO", False):
            return

        try:
            diretorio = self._garantir_diretorio_diagnostico()
            self._diagnostico_contador += 1
            prefixo = (
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_"
                f"{self._diagnostico_contador:03d}_nota_{nota.id}_{etapa}"
            )

            estado = page.evaluate(
                """
                () => {
                    const visivel = (elemento) => !!(
                        elemento &&
                        (elemento.offsetWidth || elemento.offsetHeight || elemento.getClientRects().length)
                    );
                    const controles = Array.from(document.querySelectorAll('input, select, button, textarea'))
                        .map((elemento) => ({
                            tag: elemento.tagName,
                            type: elemento.getAttribute('type') || '',
                            id: elemento.id || '',
                            name: elemento.getAttribute('name') || '',
                            value: elemento.value || elemento.textContent || '',
                            disabled: !!elemento.disabled,
                            visible: visivel(elemento),
                            classes: elemento.className || '',
                            onclick: elemento.getAttribute('onclick') || ''
                        }));
                    return {
                        url: location.href,
                        title: document.title,
                        readyState: document.readyState,
                        bodyText: (document.body?.innerText || '').slice(0, 5000),
                        cadastrar: controles.filter((item) => (item.value || '').trim() === 'Cadastrar'),
                        voltar: controles.filter((item) => (item.value || '').trim() === 'Voltar'),
                        controles
                    };
                }
                """
            )
            estado["nota_id"] = nota.id
            estado["chave"] = nota.chave
            estado["etapa"] = etapa

            caminho_json = diretorio / f"{prefixo}.json"
            caminho_json.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")

            if getattr(config, "DIAGNOSTICO_SALVAR_HTML", True):
                (diretorio / f"{prefixo}.html").write_text(page.content(), encoding="utf-8", errors="ignore")

            if getattr(config, "DIAGNOSTICO_SALVAR_SCREENSHOT", True):
                page.screenshot(path=diretorio / f"{prefixo}.png", full_page=True)

            self._registrar_diagnostico_evento(
                "snapshot",
                f"{etapa} nota={nota.id} chave={nota.chave} arquivo={caminho_json.name}",
            )
        except Exception as exc:
            self._log(f"Nao foi possivel salvar diagnostico da pagina: {exc}", error=True)

    def _registrar_diagnostico_evento(self, tipo: str, mensagem: str) -> None:
        if not getattr(config, "DIAGNOSTICO_ATIVO", False):
            return
        try:
            diretorio = self._garantir_diretorio_diagnostico()
            linha = f"{datetime.now().isoformat(timespec='seconds')} [{tipo}] {mensagem}\n"
            (diretorio / "eventos.log").open("a", encoding="utf-8").write(linha)
        except Exception:
            pass

    def _garantir_diretorio_diagnostico(self) -> Path:
        diretorio = Path(getattr(config, "DIAGNOSTICO_DIR", config.LOG_DIR / "diagnostico"))
        diretorio.mkdir(parents=True, exist_ok=True)
        return diretorio

    def _aguardar_campo_com_valor(self, page: Page, seletor: str, nome: str) -> None:
        locator = page.locator(seletor).first
        timeout_ms = getattr(config, "TIMEOUT_AUTOPREENCHIMENTO_MS", 4000)
        locator.wait_for(state="visible", timeout=timeout_ms)
        limite = time.time() + (timeout_ms / 1000)
        while time.time() < limite:
            valor = locator.input_value(timeout=500).strip()
            if valor:
                self._log(f"Autopreenchimento confirmado pelo {nome}.")
                return
            time.sleep(0.15)
        raise PlaywrightTimeoutError(f"Tempo excedido aguardando valor em {nome}.")

    def _ler_mensagem_validacao_formulario(self, page: Page) -> str:
        mensagens: list[str] = []

        for seletor in getattr(config, "MENSAGENS_VALIDACAO_FORMULARIO", []):
            try:
                localizador = page.locator(seletor)
                total = min(localizador.count(), 20)
                for indice in range(total):
                    item = localizador.nth(indice)
                    if not item.is_visible(timeout=200):
                        continue
                    texto = self._limpar_mensagem_portal(item.inner_text(timeout=500))
                    if self._texto_parece_mensagem_portal(texto):
                        mensagens.append(texto)
            except Exception:
                continue

        try:
            mensagens.extend(
                page.evaluate(
                    """
                    () => {
                        const normalizar = (valor) => (valor || '')
                            .normalize('NFD')
                            .replace(/[\\u0300-\\u036f]/g, '')
                            .toLowerCase()
                            .replace(/\\s+/g, ' ')
                            .trim();
                        const visivel = (elemento) => !!(
                            elemento &&
                            (elemento.offsetWidth || elemento.offsetHeight || elemento.getClientRects().length)
                        );
                        const padroes = [
                            'nota ja foi doada',
                            'ja foi doada',
                            'foi doada',
                            'chave invalida',
                            'verificar novamente',
                            'nao podem ter sido emitidas',
                            'nao pode ter sido emitida',
                            'mais de 2 meses',
                            'requisicoes excessivas',
                            'sessao encerrada'
                        ];
                        const classeMensagem = (elemento) => {
                            const texto = normalizar([
                                elemento.className || '',
                                elemento.id || '',
                                elemento.getAttribute('role') || '',
                                elemento.getAttribute('aria-live') || ''
                            ].join(' '));
                            return /(alert|message|mensagem|msg|erro|error|warning|info|rf-msg|rich-message|ui-message)/.test(texto);
                        };
                        const resultado = [];
                        for (const elemento of Array.from(document.querySelectorAll('body *'))) {
                            if (!visivel(elemento)) {
                                continue;
                            }
                            const textoOriginal = (elemento.innerText || elemento.textContent || '')
                                .replace(/\\s+/g, ' ')
                                .trim();
                            if (!textoOriginal || textoOriginal.length > 500) {
                                continue;
                            }
                            const texto = normalizar(textoOriginal);
                            const temPadrao = padroes.some((padrao) => texto.includes(padrao));
                            if (temPadrao || classeMensagem(elemento)) {
                                resultado.push(textoOriginal);
                            }
                        }
                        return Array.from(new Set(resultado)).slice(0, 30);
                    }
                    """
                )
            )
        except Exception:
            pass

        return self._escolher_mensagem_portal(mensagens)

    def _limpar_mensagem_portal(self, texto: str) -> str:
        linhas = (texto or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
        linhas = [linha.strip() for linha in linhas]
        while linhas and not linhas[0]:
            linhas.pop(0)
        while linhas and not linhas[-1]:
            linhas.pop()
        return "\n".join(linhas)

    def _texto_parece_mensagem_portal(self, texto: str) -> bool:
        texto = self._limpar_mensagem_portal(texto)
        if not texto or len(texto) > 500:
            return False
        normalizado = self._normalizar_texto(texto)
        padroes = (
            "nota ja foi doada",
            "ja foi doada",
            "foi doada",
            "chave invalida",
            "verificar novamente",
            "nao podem ter sido emitidas",
            "nao pode ter sido emitida",
            "mais de 2 meses",
            "requisicoes excessivas",
            "sessao encerrada",
            "atencao",
            "erro",
            "falha",
        )
        return any(padrao in normalizado for padrao in padroes)

    def _escolher_mensagem_portal(self, mensagens: list[str]) -> str:
        unicas: dict[str, str] = {}
        for mensagem in mensagens:
            limpa = self._limpar_mensagem_portal(mensagem)
            if not self._texto_parece_mensagem_portal(limpa):
                continue
            normalizada = self._normalizar_texto(limpa)
            unicas.setdefault(normalizada, limpa)

        if not unicas:
            return ""

        def prioridade(mensagem: str) -> tuple[int, int]:
            normalizada = self._normalizar_texto(mensagem)
            pontos = 0
            padroes_fortes = (
                "nota ja foi doada",
                "ja foi doada",
                "foi doada",
                "chave invalida",
                "verificar novamente",
                "nao podem ter sido emitidas",
                "nao pode ter sido emitida",
                "mais de 2 meses",
                "requisicoes excessivas",
                "sessao encerrada",
            )
            for padrao in padroes_fortes:
                if padrao in normalizada:
                    pontos += 10
            if "atencao" in normalizada:
                pontos += 2
            if "erro" in normalizada or "falha" in normalizada:
                pontos += 2
            return pontos, -len(mensagem)

        return max(unicas.values(), key=prioridade)

    def _ler_valor_nota(self, page: Page) -> Optional[float]:
        seletor = getattr(config, "CAMPO_VALOR_NOTA", "")
        if not seletor:
            return None
        try:
            texto = page.locator(seletor).first.input_value(timeout=1000)
        except Exception:
            return None
        return self._parse_valor_brasileiro(texto)

    def _ler_data_emissao_nota(self, page: Page) -> Optional[date]:
        texto = ""
        seletor = getattr(config, "CAMPO_DATA_EMISSAO_NOTA", "")
        if seletor:
            try:
                texto = page.locator(seletor).first.input_value(timeout=1000)
            except Exception:
                texto = ""

        if not texto:
            try:
                texto = page.evaluate(
                    """
                    () => {
                        const normalizar = (valor) => (valor || '')
                            .normalize('NFD')
                            .replace(/[\\u0300-\\u036f]/g, '')
                            .toLowerCase();
                        const rotulo = Array.from(document.querySelectorAll('span, td, label'))
                            .find((el) => normalizar(el.textContent).includes('data emissao'));
                        if (!rotulo) {
                            return '';
                        }
                        const linha = rotulo.closest('tr');
                        const campo = linha?.querySelector('input[type="text"]');
                        return campo?.value || '';
                    }
                    """
                )
            except Exception:
                texto = ""

        return self._parse_data_brasileira(texto)

    def _parse_data_brasileira(self, texto: str) -> Optional[date]:
        texto = (texto or "").strip()
        try:
            return datetime.strptime(texto, "%d/%m/%Y").date()
        except ValueError:
            return None

    def _data_emissao_fora_prazo(self, data_emissao: date) -> bool:
        limite = self._subtrair_meses(date.today(), getattr(config, "PRAZO_MAXIMO_EMISSAO_MESES", 2))
        return data_emissao <= limite

    def _subtrair_meses(self, data_base: date, meses: int) -> date:
        mes = data_base.month - max(0, meses)
        ano = data_base.year
        while mes <= 0:
            mes += 12
            ano -= 1
        dias_no_mes = (
            self._primeiro_dia_mes_seguinte(ano, mes) - date(ano, mes, 1)
        ).days
        return date(ano, mes, min(data_base.day, dias_no_mes))

    def _primeiro_dia_mes_seguinte(self, ano: int, mes: int) -> date:
        if mes == 12:
            return date(ano + 1, 1, 1)
        return date(ano, mes + 1, 1)

    def _mensagem_nota_fora_prazo(self, data_emissao: date) -> str:
        meses = getattr(config, "PRAZO_MAXIMO_EMISSAO_MESES", 2)
        limite = self._subtrair_meses(date.today(), meses)
        return (
            f"Nota ignorada automaticamente: data de emissao "
            f"{self._formatar_data(data_emissao)} fora do prazo de {meses} meses. "
            f"Limite atual: {self._formatar_data(limite)}."
        )

    def _parse_valor_brasileiro(self, texto: str) -> Optional[float]:
        texto = (texto or "").strip()
        if not texto:
            return None
        normalizado = texto.replace("R$", "").replace(" ", "")
        normalizado = normalizado.replace(".", "").replace(",", ".")
        try:
            return round(float(normalizado), 2)
        except ValueError:
            return None

    def _formatar_valor(self, valor: float) -> str:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def _formatar_data(self, valor: date) -> str:
        return valor.strftime("%d/%m/%Y")

    def _formatar_duracao(self, segundos: float) -> str:
        segundos_int = int(round(max(0.0, segundos)))
        minutos, resto = divmod(segundos_int, 60)
        horas, minutos = divmod(minutos, 60)
        if horas:
            return f"{horas}h {minutos}min {resto}s"
        if minutos:
            return f"{minutos}min {resto}s"
        return f"{resto}s"

    def _abrir_tela_cadastrar_notas(self, page: Page) -> None:
        if not config.MENU_CADASTRAR_NOTAS:
            return
        try:
            if page.locator(config.CAMPO_TIPO_NOTA).first.is_visible(timeout=500):
                return
        except Exception:
            pass
        try:
            page.locator(config.MENU_CADASTRAR_NOTAS).first.click(timeout=3000)
            self._aguardar_carregamento_curto(page)
            self._log("Tela Cadastrar Notas acessada.")
        except Exception:
            self._log("Menu Cadastrar Notas nao foi clicado; assumindo que a tela ja esta aberta.")

    def _selecionar_tipo_nfce(self, page: Page) -> None:
        self._log(f"Selecionando tipo de nota: {config.TIPO_NOTA_TEXTO}.")
        campo = page.locator(config.CAMPO_TIPO_NOTA).first
        try:
            selecionado = campo.evaluate(
                """
                (select) => {
                    const opcao = select.options[select.selectedIndex];
                    return opcao ? opcao.textContent.trim() : '';
                }
                """
            )
            if self._normalizar_texto(selecionado) == self._normalizar_texto(config.TIPO_NOTA_TEXTO):
                return
            campo.select_option(label=config.TIPO_NOTA_TEXTO)
        except Exception:
            campo.evaluate(
                """
                (select, texto) => {
                    const normalizar = (valor) => valor
                        .normalize('NFD')
                        .replace(/[\\u0300-\\u036f]/g, '')
                        .trim()
                        .toUpperCase();
                    const alvo = normalizar(texto);
                    const opcao = Array.from(select.options).find(
                        item => normalizar(item.textContent) === alvo
                    );
                    if (!opcao) {
                        throw new Error(`Opcao nao encontrada: ${texto}`);
                    }
                    select.value = opcao.value;
                    select.dispatchEvent(new Event('change', { bubbles: true }));
                }
                """,
                config.TIPO_NOTA_TEXTO,
            )
        page.wait_for_timeout(150)

    def _captcha_presente(self, page: Page) -> bool:
        if not config.SELETOR_CAPTCHA:
            return False
        try:
            return page.locator(config.SELETOR_CAPTCHA).first.is_visible(timeout=1000)
        except Exception:
            return False

    def _pausar_por_captcha(self, nota: Nota) -> None:
        self._atualizar_status_nota(
            nota.id,
            STATUS_AGUARDANDO_CAPTCHA,
            "Aguardando resolucao manual de CAPTCHA/validacao.",
            db_path=self.db_path,
        )
        self._notificar_nota(nota.id)
        self._pause_event.clear()
        self._estado("AGUARDANDO_CAPTCHA")
        self._log(
            "CAPTCHA ou validacao manual detectado. Resolva no navegador e clique em "
            "Continuar para prosseguir."
        )
        self._aguardar_continuacao()
        self._atualizar_status_nota(
            nota.id,
            STATUS_PENDENTE,
            "Validacao manual resolvida; retomando.",
            db_path=self.db_path,
        )
        self._notificar_nota(nota.id)

    def _ler_mensagem(self, page: Page) -> str:
        mensagem_formulario = self._ler_mensagem_validacao_formulario(page)
        if mensagem_formulario:
            return mensagem_formulario

        if not config.MENSAGEM_RETORNO:
            return self._ler_texto_body(page)
        try:
            texto = page.locator(config.MENSAGEM_RETORNO).first.inner_text(timeout=5000)
            return " ".join(texto.split())
        except Exception:
            return self._ler_texto_body(page)

    def _ler_texto_body(self, page: Page) -> str:
        try:
            texto = page.locator("body").inner_text(timeout=5000)
            return " ".join(texto.split())
        except Exception:
            return ""

    def _classificar_retorno(self, mensagem: str) -> str:
        texto = self._normalizar_texto(mensagem)
        if "nota cadastrada com sucesso" in texto or "operacao realizada com sucesso" in texto:
            return STATUS_CADASTRADA
        if any(palavra in texto for palavra in ("ja foi doada", "foi doada", "duplic", "ja cadastr", "existente")):
            return STATUS_DUPLICADA
        if any(
            palavra in texto
            for palavra in (
                "chave invalida",
                "numero da chave invalida",
                "verificar novamente",
                "nota nao existe",
                "nao encontrada",
                "nao podem ter sido emitidas",
                "nao pode ter sido emitida",
                "mais de 2 meses",
                "fora do prazo",
            )
        ):
            return STATUS_IGNORADA
        if any(palavra in texto for palavra in ("erro", "inval", "falha", "nao foi")):
            return STATUS_ERRO
        return STATUS_ERRO

    def _normalizar_texto(self, texto: str) -> str:
        sem_acentos = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
        return " ".join(sem_acentos.lower().split())

    def _resumir_mensagem(self, mensagem: str, limite: int = 300) -> str:
        texto = " ".join((mensagem or "").split())
        if len(texto) <= limite:
            return texto
        return texto[:limite].rstrip() + "..."

    def _aguardar_continuacao(self) -> None:
        while not self._stop_event.is_set() and not self._pause_event.is_set():
            time.sleep(0.2)

    def _notificar_nota(self, nota_id: str | int) -> None:
        if not self.nota_callback:
            return
        nota = self.api_client.obter_nota(nota_id)
        if nota:
            self.nota_callback(nota)

    def _atualizar_status_nota(
        self,
        nota: Nota | str | int,
        status: str,
        mensagem: str = "",
        *,
        incrementar_tentativa: bool = False,
        definir_data_cadastro: bool = False,
        valor: Optional[float] = None,
        data_emissao_nota: Optional[str] = None,
        tempo_cadastro_segundos: Optional[float] = None,
        db_path: Path | None = None,
    ) -> None:
        """Mantém a assinatura do fluxo antigo e grava na API central."""
        if status == STATUS_PENDENTE:
            # A nota já foi reservada pelo Worker. A retomada após CAPTCHA ou
            # pausa continua na mesma execução e não cria outra execução.
            return
        nota_obj = nota if isinstance(nota, Nota) else self._nota_em_processamento
        if nota_obj is None:
            raise RuntimeError("Nenhuma nota está associada à execução atual.")
        data_emissao = None
        if data_emissao_nota:
            try:
                data_emissao = date.fromisoformat(data_emissao_nota[:10])
            except ValueError:
                pass
        self.api_client.registrar_resultado(
            nota_obj,
            status,
            mensagem,
            valor=valor,
            data_emissao=data_emissao,
            tempo_segundos=tempo_cadastro_segundos,
        )

    def _log(self, mensagem: str, *, error: bool = False) -> None:
        if error:
            self._logger.error(mensagem)
        else:
            self._logger.info(mensagem)
        if self.log_callback:
            self.log_callback(mensagem)

    def _estado(self, estado: str) -> None:
        if self.estado_callback:
            self.estado_callback(estado)
