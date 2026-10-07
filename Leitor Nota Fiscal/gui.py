import logging
import tkinter as tk
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from api_client import ApiNotasClient
import relatorios
from automacao_notalegal import AutomacaoNotaLegal
from config import APP_ICON_PATH, LOG_FILE, MAX_TENTATIVAS_CADASTRO
from leitor_txt import processar_arquivo_txt
from models import Nota, STATUS_CADASTRADA, STATUS_ERRO, STATUS_IGNORADA


STATUS_RELATORIO_MANUAL = (STATUS_IGNORADA, STATUS_ERRO)


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Leitor Nota Fiscal - Nota Legal")
        self.geometry("1180x760")
        self.minsize(980, 640)

        self.logger = logging.getLogger("leitor_nota_fiscal")
        self.api_client = ApiNotasClient()
        self._aplicar_icone()
        self.arquivo_selecionado = tk.StringVar(value="")
        self.estado_automacao = tk.StringVar(value="Pronta")
        self.resumo_importacao = tk.StringVar(value=self._texto_lista_operacao())
        self.mensagem_operacao = tk.StringVar(value="Pronto para importar notas ou iniciar a automacao assistida.")
        self.titulo_lista_operacao = tk.StringVar(value=self._texto_lista_operacao())
        self.contadores_operacao = tk.StringVar(value="Fila pendente: 0 | Cadastradas hoje: 0 | Cadastradas total: 0")
        self.relatorio_resumo = tk.StringVar(value="Informe o periodo e atualize o relatorio.")
        self.relatorio_manual_resumo = tk.StringVar(value="Notas para teste manual: 0")
        self.mostrar_notas_cadastradas = tk.BooleanVar(value=False)
        self.codigos_relatorio_manual: list[str] = []
        self.automacao: AutomacaoNotaLegal | None = None

        self._configurar_estilo()
        self._montar_interface()
        self.atualizar_tabela_notas()
        self.atualizar_contadores_operacao()
        self.atualizar_relatorio()

    def _aplicar_icone(self) -> None:
        try:
            if APP_ICON_PATH.exists():
                self.iconbitmap(str(APP_ICON_PATH))
        except Exception:
            self.logger.debug("Nao foi possivel aplicar o icone da janela.", exc_info=True)

    def _configurar_estilo(self) -> None:
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        style = ttk.Style(self)
        style.theme_use("default")
        style.configure(
            "Treeview",
            rowheight=28,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def _montar_interface(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=0, column=0, sticky="nsew", padx=14, pady=(14, 6))
        self.tab_operacao = self.tabs.add("Operacao")
        self.tab_relatorios = self.tabs.add("Relatorios")

        self._montar_tab_operacao()
        self._montar_tab_relatorios()

        ctk.CTkLabel(
            self,
            text="Desenvolvido por NTI APAE 2026",
            anchor="e",
            text_color=("gray35", "gray70"),
            font=("Segoe UI", 11, "bold"),
        ).grid(row=1, column=0, sticky="e", padx=18, pady=(0, 8))

    def _montar_tab_operacao(self) -> None:
        tab = self.tab_operacao
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(4, weight=3)
        tab.grid_rowconfigure(5, weight=1)

        topo = ctk.CTkFrame(tab)
        topo.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 8))
        topo.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(topo, text="Selecionar arquivo TXT", command=self.selecionar_arquivo).grid(
            row=0, column=0, padx=10, pady=10
        )
        ctk.CTkEntry(topo, textvariable=self.arquivo_selecionado, state="readonly").grid(
            row=0, column=1, sticky="ew", padx=(0, 10), pady=10
        )
        ctk.CTkButton(topo, text="Processar arquivo", command=self.processar_arquivo).grid(
            row=0, column=2, padx=(0, 10), pady=10
        )

        controles = ctk.CTkFrame(tab)
        controles.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))
        controles.grid_columnconfigure(7, weight=1)

        self.botao_iniciar = ctk.CTkButton(
            controles,
            text="Iniciar automacao",
            command=self.iniciar_automacao,
        )
        self.botao_iniciar.grid(row=0, column=0, padx=10, pady=10)

        self.botao_pausar = ctk.CTkButton(
            controles,
            text="Pausar",
            command=self.pausar_automacao,
        )
        self.botao_pausar.grid(row=0, column=1, padx=(0, 10), pady=10)

        self.botao_continuar = ctk.CTkButton(
            controles,
            text="Continuar",
            command=self.continuar_automacao,
        )
        self.botao_continuar.grid(row=0, column=2, padx=(0, 10), pady=10)

        ctk.CTkButton(
            controles,
            text="Exportar relatorio",
            command=self.exportar_relatorio,
        ).grid(row=0, column=3, padx=(0, 10), pady=10)

        ctk.CTkButton(
            controles,
            text="Excluir fila",
            command=self.excluir_fila_importada,
            fg_color=("#B3261E", "#8C1D18"),
            hover_color=("#8C1D18", "#6E1712"),
        ).grid(row=0, column=4, padx=(0, 10), pady=10)

        ctk.CTkButton(
            controles,
            text="Atualizar fila",
            command=self.atualizar_fila_manual,
        ).grid(row=0, column=5, padx=(0, 10), pady=10)

        ctk.CTkLabel(controles, text="Estado:").grid(row=0, column=6, padx=(0, 4), pady=10)
        ctk.CTkLabel(controles, textvariable=self.estado_automacao, anchor="w").grid(
            row=0, column=7, sticky="ew", padx=(0, 10), pady=10
        )
        ctk.CTkLabel(
            controles,
            textvariable=self.contadores_operacao,
            anchor="w",
            font=("Segoe UI", 12, "bold"),
        ).grid(
            row=1,
            column=0,
            columnspan=8,
            sticky="ew",
            padx=10,
            pady=(0, 10),
        )

        self.mensagem_operacao_frame = ctk.CTkFrame(tab, fg_color=("#E8F1FF", "#182A44"))
        self.mensagem_operacao_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))
        self.mensagem_operacao_frame.grid_columnconfigure(0, weight=1)
        self.mensagem_operacao_label = ctk.CTkLabel(
            self.mensagem_operacao_frame,
            textvariable=self.mensagem_operacao,
            anchor="w",
            font=("Segoe UI", 13, "bold"),
            text_color=("#163B73", "#DCEBFF"),
        )
        self.mensagem_operacao_label.grid(row=0, column=0, sticky="ew", padx=12, pady=10)

        ctk.CTkLabel(tab, textvariable=self.resumo_importacao, anchor="w").grid(
            row=3, column=0, sticky="new", padx=12, pady=(0, 6)
        )

        tabela_frame = ctk.CTkFrame(tab)
        tabela_frame.grid(row=4, column=0, sticky="nsew", padx=10, pady=(0, 8))
        tabela_frame.grid_columnconfigure(0, weight=1)
        tabela_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            tabela_frame,
            textvariable=self.titulo_lista_operacao,
            anchor="w",
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))

        colunas = (
            "id",
            "chave",
            "status",
            "valor",
            "data_emissao",
            "tempo",
            "tentativa",
            "mensagem",
            "arquivo",
            "data_importacao",
            "data_cadastro",
        )
        self.tabela_notas = ttk.Treeview(tabela_frame, columns=colunas, show="headings")
        self.tabela_notas.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(0, 10))
        scrollbar = ttk.Scrollbar(tabela_frame, orient="vertical", command=self.tabela_notas.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=(0, 10))
        self.tabela_notas.configure(yscrollcommand=scrollbar.set)

        cabecalhos = {
            "id": ("ID", 60),
            "chave": ("Chave", 330),
            "status": ("Status", 150),
            "valor": ("Valor", 110),
            "data_emissao": ("Emissao", 110),
            "tempo": ("Tempo", 90),
            "tentativa": ("Tent.", 70),
            "mensagem": ("Mensagem", 250),
            "arquivo": ("Arquivo", 150),
            "data_importacao": ("Importacao", 150),
            "data_cadastro": ("Cadastro", 150),
        }
        for coluna, (texto, largura) in cabecalhos.items():
            self.tabela_notas.heading(coluna, text=texto)
            self.tabela_notas.column(coluna, width=largura, minwidth=50, stretch=coluna in {"mensagem", "chave"})

        log_frame = ctk.CTkFrame(tab)
        log_frame.grid(row=5, column=0, sticky="nsew", padx=10, pady=(0, 10))
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(log_frame, text="Log em tempo real", anchor="w").grid(
            row=0, column=0, sticky="ew", padx=10, pady=(8, 0)
        )
        self.caixa_log = ctk.CTkTextbox(log_frame, height=150)
        self.caixa_log.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.caixa_log.configure(state="disabled")

    def _montar_tab_relatorios(self) -> None:
        tab = self.tab_relatorios
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)
        tab.grid_rowconfigure(4, weight=2)

        hoje = date.today()
        primeiro_dia = hoje.replace(day=1)
        self.data_inicial = tk.StringVar(value=self._formatar_data_br(primeiro_dia))
        self.data_final = tk.StringVar(value=self._formatar_data_br(hoje))

        filtros = ctk.CTkFrame(tab)
        filtros.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        filtros.grid_columnconfigure(7, weight=1)

        ctk.CTkLabel(filtros, text="Data inicial").grid(row=0, column=0, padx=(10, 6), pady=10)
        ctk.CTkEntry(filtros, textvariable=self.data_inicial, width=130).grid(
            row=0, column=1, padx=(0, 12), pady=10
        )
        ctk.CTkLabel(filtros, text="Data final").grid(row=0, column=2, padx=(0, 6), pady=10)
        ctk.CTkEntry(filtros, textvariable=self.data_final, width=130).grid(
            row=0, column=3, padx=(0, 12), pady=10
        )
        ctk.CTkButton(filtros, text="Atualizar", command=self.atualizar_relatorio).grid(
            row=0, column=4, padx=(0, 10), pady=10
        )
        ctk.CTkButton(filtros, text="Exportar Excel", command=self.exportar_relatorio).grid(
            row=0, column=5, padx=(0, 10), pady=10
        )
        ctk.CTkButton(
            filtros,
            text="Limpar relatorio",
            command=self.limpar_relatorio,
            fg_color=("#B3261E", "#8C1D18"),
            hover_color=("#8C1D18", "#6E1712"),
        ).grid(row=0, column=6, padx=(0, 10), pady=10)

        ctk.CTkLabel(tab, textvariable=self.relatorio_resumo, anchor="w").grid(
            row=1, column=0, sticky="ew", padx=12, pady=(0, 8)
        )

        tabela_frame = ctk.CTkFrame(tab)
        tabela_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        tabela_frame.grid_columnconfigure(0, weight=1)
        tabela_frame.grid_rowconfigure(0, weight=1)

        colunas = (
            "data",
            "cadastradas",
            "valor_cadastradas",
            "tempo_total",
            "fora_prazo",
            "valor_fora_prazo",
            "duplicadas",
            "erros",
            "valor_erros",
            "ignoradas",
            "pendentes",
            "total",
        )
        self.tabela_relatorio = ttk.Treeview(tabela_frame, columns=colunas, show="headings")
        self.tabela_relatorio.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(tabela_frame, orient="vertical", command=self.tabela_relatorio.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tabela_relatorio.configure(yscrollcommand=scrollbar.set)

        cabecalhos = {
            "data": ("Data", 140),
            "cadastradas": ("Cadastradas", 140),
            "valor_cadastradas": ("Valor Cadastrado", 150),
            "tempo_total": ("Tempo Total", 130),
            "fora_prazo": ("Fora Prazo", 120),
            "valor_fora_prazo": ("Valor Fora Prazo", 150),
            "duplicadas": ("Duplicadas", 140),
            "erros": ("Erros", 120),
            "valor_erros": ("Valor Erros", 130),
            "ignoradas": ("Ignoradas", 130),
            "pendentes": ("Pendentes", 140),
            "total": ("Total", 120),
        }
        for coluna, (texto, largura) in cabecalhos.items():
            self.tabela_relatorio.heading(coluna, text=texto)
            self.tabela_relatorio.column(coluna, width=largura, anchor="center")

        detalhe_topo = ctk.CTkFrame(tab)
        detalhe_topo.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 8))
        detalhe_topo.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            detalhe_topo,
            textvariable=self.relatorio_manual_resumo,
            anchor="w",
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, sticky="ew", padx=10, pady=8)
        ctk.CTkButton(
            detalhe_topo,
            text="Copiar selecionada",
            command=self.copiar_codigo_relatorio_selecionado,
            width=150,
        ).grid(row=0, column=1, padx=(0, 8), pady=8)
        ctk.CTkButton(
            detalhe_topo,
            text="Copiar codigos",
            command=self.copiar_codigos_relatorio,
            width=130,
        ).grid(row=0, column=2, padx=(0, 10), pady=8)
        ctk.CTkSwitch(
            detalhe_topo,
            text="Mostrar cadastradas",
            variable=self.mostrar_notas_cadastradas,
            command=self.atualizar_relatorio,
        ).grid(row=0, column=3, padx=(0, 10), pady=8)

        detalhe_frame = ctk.CTkFrame(tab)
        detalhe_frame.grid(row=4, column=0, sticky="nsew", padx=10, pady=(0, 10))
        detalhe_frame.grid_columnconfigure(0, weight=1)
        detalhe_frame.grid_rowconfigure(0, weight=1)

        detalhe_colunas = (
            "codigo",
            "valor",
            "data_emissao",
            "tempo",
            "status",
            "tentativa",
            "mensagem",
            "arquivo",
            "data_importacao",
            "data_cadastro",
        )
        self.tabela_relatorio_detalhe = ttk.Treeview(detalhe_frame, columns=detalhe_colunas, show="headings")
        self.tabela_relatorio_detalhe.grid(row=0, column=0, sticky="nsew")
        detalhe_scrollbar = ttk.Scrollbar(
            detalhe_frame,
            orient="vertical",
            command=self.tabela_relatorio_detalhe.yview,
        )
        detalhe_scrollbar.grid(row=0, column=1, sticky="ns")
        self.tabela_relatorio_detalhe.configure(yscrollcommand=detalhe_scrollbar.set)

        detalhe_cabecalhos = {
            "codigo": ("Codigo NF", 330),
            "valor": ("Valor", 100),
            "data_emissao": ("Emissao", 110),
            "tempo": ("Tempo", 90),
            "status": ("Status", 130),
            "tentativa": ("Tent.", 70),
            "mensagem": ("Mensagem", 320),
            "arquivo": ("Arquivo", 150),
            "data_importacao": ("Importacao", 150),
            "data_cadastro": ("Cadastro", 150),
        }
        for coluna, (texto, largura) in detalhe_cabecalhos.items():
            self.tabela_relatorio_detalhe.heading(coluna, text=texto)
            self.tabela_relatorio_detalhe.column(
                coluna,
                width=largura,
                minwidth=50,
                stretch=coluna in {"codigo", "mensagem"},
            )
        self.tabela_relatorio_detalhe.bind("<Control-c>", self._copiar_codigo_relatorio_evento)
        self.tabela_relatorio_detalhe.bind("<Double-1>", self._copiar_codigo_relatorio_evento)

    def selecionar_arquivo(self) -> None:
        caminho = filedialog.askopenfilename(
            title="Selecionar arquivo TXT",
            filetypes=[("Arquivos TXT", "*.txt"), ("Todos os arquivos", "*.*")],
        )
        if caminho:
            self.arquivo_selecionado.set(caminho)
            self._definir_mensagem_operacao("Arquivo selecionado. Clique em Processar arquivo para importar as notas.")
            self.log(f"Arquivo selecionado: {caminho}")

    def processar_arquivo(self) -> None:
        caminho = self.arquivo_selecionado.get().strip()
        if not caminho:
            messagebox.showwarning("Arquivo nao selecionado", "Selecione um arquivo TXT primeiro.")
            return

        try:
            processamento = processar_arquivo_txt(caminho)
            resultado = self.api_client.importar_chaves(
                caminho_arquivo=processamento.caminho_arquivo,
                chaves=processamento.chaves,
                total_linhas=processamento.total_linhas,
                total_invalidas=processamento.total_invalidas,
                total_duplicadas_txt=processamento.total_duplicadas,
            )
            notas_encontradas = processamento.total_validas + processamento.total_duplicadas
            resumo = (
                f"Linhas processadas: {processamento.total_linhas} | "
                f"Notas encontradas: {notas_encontradas} | "
                f"Validas: {resultado.total_validas} | "
                f"Duplicadas: {resultado.total_duplicadas} | "
                f"Invalidas: {resultado.total_invalidas} | "
                f"Inseridas: {resultado.total_inseridas} | "
                f"Reativadas: {resultado.total_reativadas}"
            )
            self.resumo_importacao.set(resumo)
            total_para_cadastro = resultado.total_inseridas + resultado.total_reativadas
            if total_para_cadastro:
                self._definir_mensagem_operacao(
                    f"Importacao concluida: {total_para_cadastro} nota(s) aguardando cadastro.",
                    "sucesso",
                )
            else:
                self._definir_mensagem_operacao(
                    "Importacao concluida: nenhuma nota nova foi adicionada ao cadastro.",
                    "alerta",
                )
            self.log(resumo)
            if resultado.total_reativadas:
                self.log(
                    f"{resultado.total_reativadas} chave(s) com ERRO ou IGNORADA foram reativadas para novo envio."
                )
            if resultado.total_ja_existentes:
                self.log(f"{resultado.total_ja_existentes} chave(s) ja existiam no banco e nao foram repetidas.")
            self.atualizar_tabela_notas()
            self.atualizar_contadores_operacao()
            self.atualizar_relatorio()
        except Exception as exc:
            self.log(f"Erro ao processar arquivo: {exc}", error=True)
            messagebox.showerror("Erro", f"Erro ao processar arquivo:\n{exc}")

    def iniciar_automacao(self) -> None:
        if self.automacao and self.automacao.rodando:
            self.log("A automacao ja esta rodando.")
            return

        self.automacao = AutomacaoNotaLegal(
            log_callback=self.log_threadsafe,
            nota_callback=self.nota_atualizada_threadsafe,
            estado_callback=self.estado_threadsafe,
            conclusao_callback=self.conclusao_threadsafe,
            api_client=self.api_client,
        )
        self.botao_iniciar.configure(state="disabled")
        self.estado_automacao.set("Iniciando")
        self._definir_mensagem_operacao(
            "Automacao iniciada. Confira o login preenchido, resolva o CAPTCHA, clique em Acessar e continue."
        )
        self.automacao.iniciar()

    def pausar_continuar(self) -> None:
        if not self.automacao or not self.automacao.rodando:
            self.log("Nao ha automacao em execucao.")
            return
        self.automacao.alternar_pausa()

    def pausar_automacao(self) -> None:
        if not self.automacao or not self.automacao.rodando:
            self.log("Nao ha automacao em execucao para pausar.")
            return
        self.automacao.pausar()

    def continuar_automacao(self) -> None:
        if not self.automacao or not self.automacao.rodando:
            self.log("Nao ha automacao em execucao para continuar.")
            return
        self.automacao.continuar()

    def excluir_fila_importada(self) -> None:
        if self.automacao and self.automacao.rodando:
            messagebox.showwarning(
                "Automacao em execucao",
                "Pause ou finalize a automacao antes de excluir a fila de notas.",
            )
            return

        messagebox.showinfo(
            "Fila central",
            "A fila agora é administrada pela API central. A remoção em lote deve ser feita por uma operação administrativa da API.",
        )
        return

    def atualizar_tabela_notas(self) -> None:
        data_lista = self._data_lista_operacao()
        self.titulo_lista_operacao.set(self._texto_lista_operacao(data_lista))
        for item in self.tabela_notas.get_children():
            self.tabela_notas.delete(item)

        try:
            notas_operacao = self.api_client.listar_notas_operacao()
        except Exception as exc:
            self.log(f"API de notas indisponível: {exc}", error=True)
            self._definir_mensagem_operacao(
                "API de notas indisponível. Confira NOTAS_API_URL e tente novamente.",
                "erro",
            )
            return

        for nota in notas_operacao:
            self.tabela_notas.insert(
                "",
                "end",
                iid=str(nota.id),
                values=(
                    nota.id,
                    nota.chave,
                    nota.status,
                    self._formatar_moeda(nota.valor),
                    self._formatar_data_iso(nota.data_emissao_nota),
                    self._formatar_duracao(nota.tempo_cadastro_segundos),
                    nota.tentativa,
                    nota.mensagem,
                    nota.arquivo_origem,
                    self._formatar_data_hora_br(nota.data_importacao),
                    self._formatar_data_hora_br(nota.data_cadastro),
                ),
            )

    def _data_lista_operacao(self) -> str:
        return date.today().isoformat()

    def _texto_lista_operacao(self, data_lista: str | None = None) -> str:
        data_lista = data_lista or date.today().isoformat()
        data_lista_br = self._formatar_data_iso(data_lista)
        return (
            f"Lista da operacao: notas adicionadas hoje ({data_lista_br}) "
            "e toda a fila pendente que sera processada."
        )

    def _nota_pertence_lista_operacao(self, nota: Nota) -> bool:
        adicionada_hoje = bool(nota.data_importacao) and nota.data_importacao[:10] == self._data_lista_operacao()
        em_fila = nota.status in {"PENDENTE", "PROCESSANDO", "AGUARDANDO_CAPTCHA", "PAUSADA"} or (
            nota.status == "ERRO" and nota.tentativa < MAX_TENTATIVAS_CADASTRO
        )
        return adicionada_hoje or em_fila

    def atualizar_contadores_operacao(self) -> None:
        try:
            contadores = self.api_client.contadores_operacao()
        except Exception as exc:
            self.log(f"Erro ao atualizar contadores: {exc}", error=True)
            return

        self.contadores_operacao.set(
            f"Fila pendente: {contadores.get('fila_pendente', 0)} | "
            f"Cadastradas hoje: {contadores.get('cadastradas_hoje', 0)} | "
            f"Cadastradas total: {contadores.get('cadastradas_total', 0)}"
        )

    def atualizar_fila_manual(self) -> None:
        self.log("Atualizando fila de notas manualmente.")
        self.atualizar_tabela_notas()
        self.atualizar_contadores_operacao()
        self._definir_mensagem_operacao("Fila e contadores atualizados.", "sucesso")

    def atualizar_relatorio(self) -> None:
        periodo = self._periodo_relatorio_iso()
        if not periodo:
            return
        data_inicial, data_final = periodo

        try:
            linhas = self.api_client.relatorio_por_dia(data_inicial, data_final)
        except Exception as exc:
            self.log(f"Erro ao atualizar relatorio: {exc}", error=True)
            return

        for item in self.tabela_relatorio.get_children():
            self.tabela_relatorio.delete(item)

        total_cadastradas = total_duplicadas = total_erros = total_ignoradas = total_pendentes = total_geral = 0
        total_valor_cadastradas = 0.0
        total_tempo_cadastradas = 0.0
        total_fora_prazo = 0
        total_valor_fora_prazo = 0.0
        total_valor_erros = 0.0
        for linha in linhas:
            total_cadastradas += linha.cadastradas
            total_valor_cadastradas += linha.valor_cadastradas
            total_tempo_cadastradas += linha.tempo_total_segundos
            total_fora_prazo += linha.fora_prazo
            total_valor_fora_prazo += linha.valor_fora_prazo
            total_duplicadas += linha.duplicadas
            total_erros += linha.erros
            total_valor_erros += linha.valor_erros
            total_ignoradas += linha.ignoradas
            total_pendentes += linha.pendentes
            total_geral += linha.total
            self.tabela_relatorio.insert(
                "",
                "end",
                values=(
                    self._formatar_data_iso(linha.data),
                    linha.cadastradas,
                    self._formatar_moeda(linha.valor_cadastradas),
                    self._formatar_duracao(linha.tempo_total_segundos),
                    linha.fora_prazo,
                    self._formatar_moeda(linha.valor_fora_prazo),
                    linha.duplicadas,
                    linha.erros,
                    self._formatar_moeda(linha.valor_erros),
                    linha.ignoradas,
                    linha.pendentes,
                    linha.total,
                ),
            )

        for item in self.tabela_relatorio_detalhe.get_children():
            self.tabela_relatorio_detalhe.delete(item)

        statuses_detalhe = (
            (STATUS_CADASTRADA,)
            if self.mostrar_notas_cadastradas.get()
            else STATUS_RELATORIO_MANUAL
        )
        detalhamento = self.api_client.detalhamento_relatorio(
            data_inicial, data_final, statuses_detalhe
        )
        self.codigos_relatorio_manual = [
            str(linha.get("chave", "")).strip()
            for linha in detalhamento
            if str(linha.get("chave", "")).strip()
        ]
        if self.mostrar_notas_cadastradas.get():
            valor_detalhe = sum(float(linha.get("valor") or 0) for linha in detalhamento)
            tempo_detalhe = sum(float(linha.get("tempo_cadastro_segundos") or 0) for linha in detalhamento)
            self.relatorio_manual_resumo.set(
                f"Notas cadastradas: {len(detalhamento)} | "
                f"Valor: {self._formatar_moeda(valor_detalhe)} | "
                f"Tempo: {self._formatar_duracao(tempo_detalhe)}"
            )
        else:
            self.relatorio_manual_resumo.set(
                f"Notas para teste manual: {len(self.codigos_relatorio_manual)} | Status: IGNORADA e ERRO"
            )
        for indice, linha in enumerate(detalhamento, start=1):
            self.tabela_relatorio_detalhe.insert(
                "",
                "end",
                iid=f"detalhe-{indice}",
                values=(
                    linha.get("chave", ""),
                    self._formatar_moeda(linha.get("valor")),
                    self._formatar_data_iso(linha.get("data_emissao_nota")),
                    self._formatar_duracao(linha.get("tempo_cadastro_segundos")),
                    linha.get("status", ""),
                    linha.get("tentativa", ""),
                    linha.get("mensagem", ""),
                    linha.get("arquivo_origem", ""),
                    self._formatar_data_hora_br(linha.get("data_importacao")),
                    self._formatar_data_hora_br(linha.get("data_cadastro")),
                ),
            )

        self.relatorio_resumo.set(
            f"Periodo {self._formatar_data_iso(data_inicial)} a {self._formatar_data_iso(data_final)} | "
            f"Cadastradas: {total_cadastradas} | "
            f"Valor cadastrado: {self._formatar_moeda(total_valor_cadastradas)} | "
            f"Tempo cadastrado: {self._formatar_duracao(total_tempo_cadastradas)} | "
            f"Fora prazo: {total_fora_prazo} | "
            f"Valor fora prazo: {self._formatar_moeda(total_valor_fora_prazo)} | "
            f"Duplicadas: {total_duplicadas} | "
            f"Erros: {total_erros} | "
            f"Valor erros: {self._formatar_moeda(total_valor_erros)} | "
            f"Ignoradas: {total_ignoradas} | "
            f"Pendentes: {total_pendentes} | "
            f"Total: {total_geral}"
        )

    def _formatar_moeda(self, valor: object) -> str:
        if valor in (None, ""):
            return ""
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            return str(valor)
        return f"R$ {numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def _formatar_data_iso(self, valor: object) -> str:
        texto = str(valor or "").strip()
        if not texto:
            return ""
        try:
            ano, mes, dia = texto[:10].split("-")
            return f"{dia}/{mes}/{ano}"
        except ValueError:
            return texto

    def _formatar_data_hora_br(self, valor: object) -> str:
        texto = str(valor or "").strip()
        if not texto:
            return ""
        normalizado = texto.replace("T", " ")
        partes = normalizado.split(" ", 1)
        data_br = self._formatar_data_iso(partes[0])
        if len(partes) == 1:
            return data_br
        hora = partes[1].split(".")[0].strip()
        return f"{data_br} {hora}" if hora else data_br

    def _formatar_data_br(self, valor: date) -> str:
        return valor.strftime("%d/%m/%Y")

    def _data_br_para_iso(self, valor: str) -> str:
        texto = (valor or "").strip()
        try:
            return datetime.strptime(texto, "%d/%m/%Y").date().isoformat()
        except ValueError as exc:
            raise ValueError("Use o formato DD/MM/AAAA, por exemplo 10/06/2026.") from exc

    def _periodo_relatorio_iso(self) -> tuple[str, str] | None:
        data_inicial_texto = self.data_inicial.get().strip()
        data_final_texto = self.data_final.get().strip()
        if not data_inicial_texto or not data_final_texto:
            return None
        try:
            data_inicial = self._data_br_para_iso(data_inicial_texto)
            data_final = self._data_br_para_iso(data_final_texto)
        except ValueError as exc:
            messagebox.showwarning("Periodo invalido", str(exc))
            return None
        if data_inicial > data_final:
            messagebox.showwarning("Periodo invalido", "A data inicial nao pode ser maior que a data final.")
            return None
        return data_inicial, data_final

    def _formatar_duracao(self, valor: object) -> str:
        if valor in (None, ""):
            return ""
        try:
            segundos = int(round(float(valor)))
        except (TypeError, ValueError):
            return str(valor)
        minutos, resto = divmod(max(0, segundos), 60)
        horas, minutos = divmod(minutos, 60)
        if horas:
            return f"{horas}h {minutos}min {resto}s"
        if minutos:
            return f"{minutos}min {resto}s"
        return f"{resto}s"

    def _definir_mensagem_operacao(self, mensagem: str, tipo: str = "info") -> None:
        self.mensagem_operacao.set(mensagem)
        cores = {
            "info": (("#E8F1FF", "#182A44"), ("#163B73", "#DCEBFF")),
            "sucesso": (("#E8F7EE", "#143824"), ("#17613A", "#DDF8E8")),
            "alerta": (("#FFF7E6", "#3E2B12"), ("#7A4A00", "#FFE8B0")),
            "erro": (("#FDECEC", "#441D1D"), ("#8A1F1F", "#FFD7D7")),
        }
        frame_cor, texto_cor = cores.get(tipo, cores["info"])
        if hasattr(self, "mensagem_operacao_frame"):
            self.mensagem_operacao_frame.configure(fg_color=frame_cor)
        if hasattr(self, "mensagem_operacao_label"):
            self.mensagem_operacao_label.configure(text_color=texto_cor)

    def copiar_codigos_relatorio(self) -> None:
        if not self.codigos_relatorio_manual:
            messagebox.showinfo("Copiar codigos", "Nao ha notas IGNORADA ou ERRO no periodo.")
            return

        texto = "\n".join(self.codigos_relatorio_manual)
        self.clipboard_clear()
        self.clipboard_append(texto)
        self.update()
        self.log(f"{len(self.codigos_relatorio_manual)} codigo(s) copiado(s) para teste manual.")

    def copiar_codigo_relatorio_selecionado(self) -> None:
        selecionados = self.tabela_relatorio_detalhe.selection()
        if not selecionados:
            messagebox.showinfo("Copiar nota", "Selecione uma nota na lista de teste manual.")
            return

        valores = self.tabela_relatorio_detalhe.item(selecionados[0], "values")
        codigo = str(valores[0]).strip() if valores else ""
        if not codigo:
            messagebox.showinfo("Copiar nota", "A nota selecionada nao possui codigo para copiar.")
            return

        self.clipboard_clear()
        self.clipboard_append(codigo)
        self.update()
        self.log(f"Codigo copiado para teste manual: {codigo}")

    def _copiar_codigo_relatorio_evento(self, _event: tk.Event) -> str:
        item = self.tabela_relatorio_detalhe.identify_row(getattr(_event, "y", 0))
        if item:
            self.tabela_relatorio_detalhe.selection_set(item)
            self.tabela_relatorio_detalhe.focus(item)
        self.copiar_codigo_relatorio_selecionado()
        return "break"

    def exportar_relatorio(self) -> None:
        periodo = self._periodo_relatorio_iso()
        if not periodo:
            return
        data_inicial, data_final = periodo
        caminho = filedialog.asksaveasfilename(
            title="Exportar relatorio",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=(
                "relatorio_notas_"
                f"{self.data_inicial.get().strip().replace('/', '-')}_a_"
                f"{self.data_final.get().strip().replace('/', '-')}.xlsx"
            ),
        )
        if not caminho:
            return

        try:
            saida = relatorios.exportar_relatorio_excel(caminho, data_inicial, data_final)
            self.log(f"Relatorio exportado: {saida}")
            messagebox.showinfo("Relatorio exportado", f"Arquivo gerado:\n{saida}")
        except Exception as exc:
            self.log(f"Erro ao exportar relatorio: {exc}", error=True)
            messagebox.showerror("Erro", f"Erro ao exportar relatorio:\n{exc}")

    def limpar_relatorio(self) -> None:
        if self.automacao and self.automacao.rodando:
            messagebox.showwarning(
                "Automacao em execucao",
                "Pause ou finalize a automacao antes de limpar os relatorios.",
            )
            return

        confirmar = messagebox.askyesno(
            "Limpar relatorio",
            (
                "Limpar o historico dos relatorios?\n\n"
                "Serao removidas notas CADASTRADA, DUPLICADA, IGNORADA e ERRO que ja atingiram "
                "o limite de tentativas.\n\n"
                "A fila ainda pendente sera preservada."
            ),
        )
        if not confirmar:
            return

        messagebox.showinfo(
            "Histórico central",
            "A limpeza do histórico deve ser feita por uma operação administrativa da API central.",
        )
        return

    def nota_atualizada_threadsafe(self, nota: Nota) -> None:
        self.after(0, lambda: self._nota_atualizada(nota))

    def _nota_atualizada(self, nota: Nota) -> None:
        self.titulo_lista_operacao.set(self._texto_lista_operacao())
        iid = str(nota.id)
        if not self._nota_pertence_lista_operacao(nota):
            if self.tabela_notas.exists(iid):
                self.tabela_notas.delete(iid)
            self.atualizar_contadores_operacao()
            self.atualizar_relatorio()
            return

        valores = (
            nota.id,
            nota.chave,
            nota.status,
            self._formatar_moeda(nota.valor),
            self._formatar_data_iso(nota.data_emissao_nota),
            self._formatar_duracao(nota.tempo_cadastro_segundos),
            nota.tentativa,
            nota.mensagem,
            nota.arquivo_origem,
            self._formatar_data_hora_br(nota.data_importacao),
            self._formatar_data_hora_br(nota.data_cadastro),
        )
        if self.tabela_notas.exists(iid):
            self.tabela_notas.item(iid, values=valores)
        else:
            self.tabela_notas.insert("", "end", iid=iid, values=valores)
        self.atualizar_contadores_operacao()
        self.atualizar_relatorio()

    def conclusao_threadsafe(self, resumo: dict[str, object]) -> None:
        self.after(0, lambda: self._automacao_concluida(resumo))

    def _automacao_concluida(self, resumo: dict[str, object]) -> None:
        tempo_total = self._formatar_duracao(resumo.get("tempo_total_segundos"))
        tempo_notas = self._formatar_duracao(resumo.get("tempo_notas_segundos"))
        mensagem = (
            "Cadastro de notas concluido.\n\n"
            f"Tentativas realizadas: {resumo.get('tentadas', 0)}\n"
            f"Cadastradas: {resumo.get('cadastradas', 0)}\n"
            f"Duplicadas: {resumo.get('duplicadas', 0)}\n"
            f"Ignoradas: {resumo.get('ignoradas', 0)}\n"
            f"Erros apos 3 tentativas: {resumo.get('erros', 0)}\n"
            f"Tempo total: {tempo_total or '0s'}\n"
            f"Tempo efetivo nas notas: {tempo_notas or '0s'}"
        )
        self._definir_mensagem_operacao(
            f"Cadastros concluidos em {tempo_total or '0s'}. Confira o resumo e os relatorios.",
            "sucesso",
        )
        self.atualizar_tabela_notas()
        self.atualizar_contadores_operacao()
        self.atualizar_relatorio()
        messagebox.showinfo("Cadastros concluidos", mensagem)

    def estado_threadsafe(self, estado: str) -> None:
        self.after(0, lambda: self._estado_atualizado(estado))

    def _estado_atualizado(self, estado: str) -> None:
        self.estado_automacao.set(estado)
        if estado == "AGUARDANDO_LOGIN":
            self._definir_mensagem_operacao(
                "Login preparado no navegador. Resolva o CAPTCHA, clique em Acessar e depois em Continuar.",
                "alerta",
            )
        elif estado == "EXECUTANDO":
            self._definir_mensagem_operacao("Automacao em execucao. As notas estao sendo cadastradas.")
        elif estado == "PROCESSO_CONCLUIDO":
            self._definir_mensagem_operacao(
                "Fim dos cadastros: nao ha notas pendentes ou com erro dentro do limite de tentativas.",
                "sucesso",
            )
            self.atualizar_tabela_notas()
            self.atualizar_contadores_operacao()
            self.atualizar_relatorio()
        elif estado == "AGUARDANDO_CAPTCHA":
            self._definir_mensagem_operacao(
                "Automacao pausada: resolva a validacao manual no navegador e continue.",
                "alerta",
            )
        elif estado == "PAUSADA":
            self._definir_mensagem_operacao("Automacao pausada pelo usuario.", "alerta")
        elif estado == "SESSAO_ENCERRADA":
            self._definir_mensagem_operacao(
                "Sessao encerrada por requisicoes excessivas. Faca login novamente antes de continuar.",
                "erro",
            )
        elif estado in {"ERRO", "CONFIGURACAO_INCOMPLETA"}:
            self._definir_mensagem_operacao("Automacao interrompida. Confira o log para ver o motivo.", "erro")
        elif estado == "FINALIZADA":
            self._definir_mensagem_operacao("Automacao finalizada.", "sucesso")
            self.botao_iniciar.configure(state="normal")
            self.atualizar_tabela_notas()
            self.atualizar_contadores_operacao()
            self.atualizar_relatorio()

    def log_threadsafe(self, mensagem: str) -> None:
        self.after(0, lambda: self.log(mensagem))

    def log(self, mensagem: str, *, error: bool = False) -> None:
        if error:
            self.logger.error(mensagem)
        else:
            self.logger.info(mensagem)

        self.caixa_log.configure(state="normal")
        self.caixa_log.insert("end", f"{mensagem}\n")
        self.caixa_log.see("end")
        self.caixa_log.configure(state="disabled")

    def ao_fechar(self) -> None:
        if self.automacao and self.automacao.rodando:
            self.automacao.parar()
        self.destroy()


def configurar_logging() -> None:
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
