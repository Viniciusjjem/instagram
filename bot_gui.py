import os
import json
import threading
import time
import sys  
import telebot
import yt_dlp  
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import logging

# Configuração de registos (logs)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Limites extremos de tempo (1 hora) contra queda de rede
telebot.apihelper.READ_TIMEOUT = 3600
telebot.apihelper.CONNECT_TIMEOUT = 3600

# Definição do caminho absoluto para salvar tudo na mesma pasta
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, 'config.json')

class TelegramBotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gerenciador do Bot Telegram 📦")
        self.root.geometry("550x780") 
        self.bot = None
        self.bot_thread = None
        self.is_running = False
        
        self.cooldowns = {}

        # Variáveis do Painel
        self.token_var = tk.StringVar()
        self.chat_id_var = tk.StringVar()
        self.zip_folder_var = tk.StringVar()
        self.media_folder_var = tk.StringVar()
        self.txt_file_var = tk.StringVar() 
        self.auto_save_var = tk.BooleanVar()
        self.startup_var = tk.BooleanVar()  
        self.antilink_var = tk.BooleanVar()

        self.carregar_configuracoes()
        self.criar_interface()
        
        if self.is_running:
            self.iniciar_bot(mostrar_alerta=False)

    def criar_interface(self):
        # --- Credenciais ---
        frame_cred = tk.LabelFrame(self.root, text="Configurações do Bot", padx=10, pady=10)
        frame_cred.pack(fill="x", padx=10, pady=5)

        tk.Label(frame_cred, text="Token do Bot:").grid(row=0, column=0, sticky="w")
        tk.Entry(frame_cred, textvariable=self.token_var, width=45).grid(row=0, column=1, padx=5, pady=2)

        tk.Label(frame_cred, text="ID do Grupo:").grid(row=1, column=0, sticky="w")
        tk.Entry(frame_cred, textvariable=self.chat_id_var, width=45).grid(row=1, column=1, padx=5, pady=2)

        # --- Diretórios ---
        frame_pastas = tk.LabelFrame(self.root, text="Diretórios e Arquivos Específicos", padx=10, pady=10)
        frame_pastas.pack(fill="x", padx=10, pady=5)

        tk.Label(frame_pastas, text="Pasta de Arquivos .ZIP:").grid(row=0, column=0, sticky="w", columnspan=2)
        tk.Entry(frame_pastas, textvariable=self.zip_folder_var, width=40).grid(row=1, column=0, padx=5, pady=2)
        tk.Button(frame_pastas, text="Procurar", command=self.selecionar_pasta_zips).grid(row=1, column=1, padx=5)

        tk.Label(frame_pastas, text="Pasta para salvar Fotos/Vídeos:").grid(row=2, column=0, sticky="w", columnspan=2)
        tk.Entry(frame_pastas, textvariable=self.media_folder_var, width=40).grid(row=3, column=0, padx=5, pady=2)
        tk.Button(frame_pastas, text="Procurar", command=self.selecionar_pasta_midias).grid(row=3, column=1, padx=5)

        tk.Label(frame_pastas, text="Arquivo TXT com as URLs/Links:").grid(row=4, column=0, sticky="w", columnspan=2)
        tk.Entry(frame_pastas, textvariable=self.txt_file_var, width=40).grid(row=5, column=0, padx=5, pady=2)
        tk.Button(frame_pastas, text="Procurar", command=self.selecionar_arquivo_txt).grid(row=5, column=1, padx=5)

        tk.Checkbutton(frame_pastas, text="⚙️ Ligar com o PC (Segundo Plano)", variable=self.startup_var).grid(row=6, column=0, sticky="w", pady=2)
        tk.Checkbutton(frame_pastas, text="🛡️ Ativar Anti-Link no Grupo", variable=self.antilink_var).grid(row=7, column=0, sticky="w", pady=2)

        tk.Button(frame_pastas, text="Salvar Configurações", command=self.salvar_configuracoes, bg="lightblue").grid(row=8, column=0, columnspan=2, pady=5)

        # --- ZIPs e Botões ---
        frame_zips = tk.LabelFrame(self.root, text="Arquivos ZIP Disponíveis", padx=10, pady=10)
        frame_zips.pack(fill="both", expand=True, padx=10, pady=5)

        self.lista_zips = tk.Listbox(frame_zips, height=5)
        self.lista_zips.pack(fill="both", expand=True, pady=5)

        frame_botoes_zip = tk.Frame(frame_zips)
        frame_botoes_zip.pack(fill="x")
        tk.Button(frame_botoes_zip, text="🔄 Atualizar Lista", command=self.atualizar_lista_zips).pack(side="left", padx=5)
        tk.Button(frame_botoes_zip, text="📤 Enviar ZIP", command=self.enviar_zip_selecionado, bg="lightgreen").pack(side="right", padx=5)

        # --- Automação ---
        frame_auto = tk.LabelFrame(self.root, text="Automação do Grupo", padx=10, pady=10)
        frame_auto.pack(fill="x", padx=10, pady=5)

        tk.Checkbutton(frame_auto, text="Salvar automaticamente fotos e vídeos recebidos no grupo", variable=self.auto_save_var, command=self.salvar_configuracoes).pack(anchor="w")

        self.btn_iniciar = tk.Button(frame_auto, text="▶ Iniciar Bot (Escutar Grupo)", command=lambda: self.iniciar_bot(mostrar_alerta=True), bg="lightgreen")
        self.btn_iniciar.pack(side="left", pady=10, padx=5)

        self.btn_parar = tk.Button(frame_auto, text="⏹ Parar Bot", command=self.parar_bot, bg="salmon", state="disabled")
        self.btn_parar.pack(side="left", pady=10, padx=5)

        self.atualizar_lista_zips()

    # ================= FUNCIONALIDADES DA GUI =================

    def selecionar_pasta_zips(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta com os ZIPs")
        if pasta:
            self.zip_folder_var.set(pasta)
            self.atualizar_lista_zips()

    def selecionar_pasta_midias(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta para salvar mídias")
        if pasta:
            self.media_folder_var.set(pasta)
            
    def selecionar_arquivo_txt(self):
        arquivo = filedialog.askopenfilename(filetypes=[("Arquivos de Texto", "*.txt")])
        if arquivo:
            self.txt_file_var.set(arquivo)

    def atualizar_lista_zips(self):
        self.lista_zips.delete(0, tk.END)
        pasta = self.zip_folder_var.get()
        if os.path.isdir(pasta):
            arquivos = [f for f in os.listdir(pasta) if f.lower().endswith('.zip')]
            arquivos.sort()
            for arq in arquivos:
                self.lista_zips.insert(tk.END, arq)

    # ================= CONFIGURAÇÕES E AUTOSTART =================

    def gerenciar_autostart(self):
        autostart_dir = os.path.expanduser('~/.config/autostart')
        desktop_file_path = os.path.join(autostart_dir, 'cofre_blindado_bot.desktop')
        
        if self.startup_var.get():
            os.makedirs(autostart_dir, exist_ok=True)
            python_exe = sys.executable
            script_path = os.path.abspath(sys.argv[0])
            pasta_do_script = os.path.dirname(script_path)
            
            conteudo_desktop = f"""[Desktop Entry]
Type=Application
Exec={python_exe} {script_path}
Path={pasta_do_script}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Cofre Blindado Bot
Comment=Inicia o painel do bot em segundo plano
Terminal=false
"""
            try:
                with open(desktop_file_path, 'w') as f:
                    f.write(conteudo_desktop)
                os.chmod(desktop_file_path, 0o755)  
            except Exception as e:
                logging.error(f"Erro ao criar autostart: {e}")
        else:
            if os.path.exists(desktop_file_path):
                try:
                    os.remove(desktop_file_path)
                except Exception:
                    pass

    def salvar_configuracoes(self):
        dados = {
            "token": self.token_var.get(),
            "chat_id": self.chat_id_var.get(),
            "zip_folder": self.zip_folder_var.get(),
            "media_folder": self.media_folder_var.get(),
            "txt_file": self.txt_file_var.get(), 
            "auto_save": self.auto_save_var.get(),
            "startup": self.startup_var.get(),
            "antilink": self.antilink_var.get(),
            "bot_rodando": self.is_running  
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(dados, f)
            
        self.gerenciar_autostart()
        messagebox.showinfo("Sucesso", "Configurações salvas permanentemente!")

    def carregar_configuracoes(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                dados = json.load(f)
                self.token_var.set(dados.get("token", ""))
                self.chat_id_var.set(dados.get("chat_id", ""))
                self.zip_folder_var.set(dados.get("zip_folder", ""))
                self.media_folder_var.set(dados.get("media_folder", ""))
                self.txt_file_var.set(dados.get("txt_file", "")) 
                self.auto_save_var.set(dados.get("auto_save", False))
                self.startup_var.set(dados.get("startup", False))
                self.antilink_var.set(dados.get("antilink", False))
                self.is_running = dados.get("bot_rodando", False)

    # ================= ENVIO MANUAL =================

    def enviar_zip_selecionado(self):
        selecao = self.lista_zips.curselection()
        if not selecao:
            messagebox.showwarning("Atenção", "Selecione um arquivo.")
            return

        arquivo_nome = self.lista_zips.get(selecao[0])
        caminho_completo = os.path.join(self.zip_folder_var.get(), arquivo_nome)
        token = self.token_var.get()
        chat_id = self.chat_id_var.get()

        if not token or not chat_id:
            messagebox.showerror("Erro", "Token e ID do Grupo são obrigatórios!")
            return

        try:
            bot_temp = telebot.TeleBot(token)
            with open(caminho_completo, 'rb') as arquivo:
                bot_temp.send_document(chat_id=chat_id, document=arquivo, caption=f"Arquivo solicitado: {arquivo_nome} 📦 a/#2103294355", timeout=3600)
            messagebox.showinfo("Sucesso", f"{arquivo_nome} enviado ao grupo!")
        except Exception as e:
            messagebox.showerror("Erro ao Enviar", f"Ocorreu um erro:\n{e}")

    # ================= LÓGICA DE ESCUTA E COMANDOS =================

    def iniciar_bot(self, mostrar_alerta=True):
        token = self.token_var.get()
        if not token:
            if mostrar_alerta:
                messagebox.showerror("Erro", "Informe o Token para iniciar o bot.")
            return

        self.bot = telebot.TeleBot(token)
        
        # --- MENU INTERATIVO COM BOTÕES ---
        @self.bot.message_handler(commands=['start', 'ajuda', 'comandos', 'menu'])
        def cmd_ajuda(message):
            markup = telebot.types.InlineKeyboardMarkup(row_width=1)
            btn_geral = telebot.types.InlineKeyboardButton("📘 Comandos Gerais", callback_data="menu_geral")
            btn_down = telebot.types.InlineKeyboardButton("📥 Downloads e Mídias", callback_data="menu_down")
            btn_admin = telebot.types.InlineKeyboardButton("👑 Administração", callback_data="menu_admin")
            
            markup.add(btn_geral, btn_down, btn_admin)
            self.bot.reply_to(message, "🤖 *Central de Comando do Bot*\n\nSelecione uma categoria abaixo para ver as opções disponíveis:", parse_mode='Markdown', reply_markup=markup)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("menu_"))
        def callback_menu(call):
            try:
                self.bot.answer_callback_query(call.id)
                texto = ""
                markup = telebot.types.InlineKeyboardMarkup(row_width=1)
                
                if call.data == "menu_geral":
                    texto = (
                        "📘 *Comandos Gerais:*\n\n"
                        "🔹 `/start` ou `/menu` - Abre este menu\n"
                        "🔹 `/status` - Verifica se o bot está online\n"
                        "🔹 `/regras` - Exibe as regras do grupo\n"
                        "🔹 `/reportar [motivo]` - Alerta o administrador\n"
                        "🔹 `/id` - Mostra a sua identificação"
                    )
                    markup.add(telebot.types.InlineKeyboardButton("⬅️ Voltar ao Início", callback_data="menu_voltar"))
                    
                elif call.data == "menu_down":
                    texto = (
                        "📥 *Downloads e Mídias:*\n\n"
                        "🔹 `/baixar` - Abre a lista de arquivos ZIP\n"
                        "🔹 `/links` - Recebe o arquivo TXT com URLs úteis\n"
                        "🔹 `/video [link]` - Baixa um vídeo de qualquer rede social"
                    )
                    markup.add(telebot.types.InlineKeyboardButton("⬅️ Voltar ao Início", callback_data="menu_voltar"))
                    
                elif call.data == "menu_admin":
                    texto = (
                        "👑 *Administração (Apenas Admins):*\n\n"
                        "🔸 `/limpar` - Apaga o histórico de mensagens\n"
                        "🔸 `/fechar` e `/abrir` - Tranca ou destranca o chat\n"
                        "🔸 `/ban` - Bane (responda à mensagem)\n"
                        "🔸 `/mutar [tempo]` - Silencia (Ex: `/mutar 2h`)\n"
                        "🔸 `/aviso [texto]` - Envia e fixa um anúncio\n"
                        "🔸 `/antilink` - Liga ou desliga bloqueio de links"
                    )
                    markup.add(telebot.types.InlineKeyboardButton("⬅️ Voltar ao Início", callback_data="menu_voltar"))
                    
                elif call.data == "menu_voltar":
                    texto = "🤖 *Central de Comando do Bot*\n\nSelecione uma categoria abaixo para ver as opções disponíveis:"
                    markup.add(
                        telebot.types.InlineKeyboardButton("📘 Comandos Gerais", callback_data="menu_geral"),
                        telebot.types.InlineKeyboardButton("📥 Downloads e Mídias", callback_data="menu_down"),
                        telebot.types.InlineKeyboardButton("👑 Administração", callback_data="menu_admin")
                    )

                self.bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=texto,
                    parse_mode='Markdown',
                    reply_markup=markup
                )
            except Exception as e:
                logging.error(f"Erro no botão: {e}")

        # --- DEMAIS COMANDOS ---
        @self.bot.message_handler(commands=['status'])
        def cmd_status(message):
            self.bot.reply_to(message, "✅ Status: ONLINE.")

        @self.bot.message_handler(commands=['ban'])
        def cmd_ban(message):
            try:
                usuario_status = self.bot.get_chat_member(message.chat.id, message.from_user.id).status
                if usuario_status not in ['administrator', 'creator']:
                    return
                if not message.reply_to_message:
                    self.bot.reply_to(message, "⚠️ Responda à mensagem da pessoa que você quer banir.")
                    return
                alvo_id = message.reply_to_message.from_user.id
                self.bot.ban_chat_member(message.chat.id, alvo_id)
                self.bot.reply_to(message, "🔨 *Usuário banido permanentemente do grupo!*", parse_mode='Markdown')
            except Exception as e:
                logging.error(f"Erro no ban: {e}")

        @self.bot.message_handler(commands=['mutar'])
        def cmd_mutar(message):
            try:
                usuario_status = self.bot.get_chat_member(message.chat.id, message.from_user.id).status
                if usuario_status not in ['administrator', 'creator']:
                    return
                if not message.reply_to_message:
                    self.bot.reply_to(message, "⚠️ Responda à mensagem do infrator. Exemplo: `/mutar 2h` ou `/mutar 10m`", parse_mode='Markdown')
                    return

                alvo_id = message.reply_to_message.from_user.id
                partes = message.text.split()
                tempo_segundos = 0
                texto_tempo = "tempo indeterminado"

                if len(partes) > 1:
                    formato = partes[1].lower()
                    if formato.endswith('m'):
                        tempo_segundos = int(formato[:-1]) * 60
                        texto_tempo = f"{formato[:-1]} minuto(s)"
                    elif formato.endswith('h'):
                        tempo_segundos = int(formato[:-1]) * 3600
                        texto_tempo = f"{formato[:-1]} hora(s)"
                    elif formato.endswith('d'):
                        tempo_segundos = int(formato[:-1]) * 86400
                        texto_tempo = f"{formato[:-1]} dia(s)"

                until_date = int(time.time() + tempo_segundos) if tempo_segundos > 0 else 0
                permissoes_mutado = telebot.types.ChatPermissions(can_send_messages=False)
                self.bot.restrict_chat_member(message.chat.id, alvo_id, until_date=until_date, permissions=permissoes_mutado)
                self.bot.reply_to(message, f"🔇 O usuário foi silenciado por: *{texto_tempo}*.", parse_mode='Markdown')
            except Exception as e:
                logging.error(f"Erro ao mutar: {e}")

        @self.bot.message_handler(commands=['regras'])
        def cmd_regras(message):
            texto = (
                "📜 *Regras Oficiais do Grupo:*\n\n"
                "1️⃣ Respeito mútuo é obrigatório.\n"
                "2️⃣ Proibido compartilhar links externos ou fazer spam.\n"
                "3️⃣ Não é permitido o envio de conteúdo ofensivo.\n"
                "4️⃣ Para baixar arquivos, use o comando `/baixar` e aguarde.\n\n"
                "📌 _O descumprimento pode gerar banimento sem aviso prévio._"
            )
            self.bot.reply_to(message, texto, parse_mode='Markdown')

        @self.bot.message_handler(commands=['reportar'])
        def cmd_reportar(message):
            partes = message.text.split(maxsplit=1)
            if len(partes) < 2:
                self.bot.reply_to(message, "⚠️ Digite o motivo logo à frente. Exemplo: `/reportar o link 2 parou de funcionar`", parse_mode='Markdown')
                return
            
            relatorio = partes[1].strip()
            usuario = message.from_user.first_name
            data_hora = time.strftime('%d/%m/%Y %H:%M:%S')
            caminho_relatorio = os.path.join(SCRIPT_DIR, 'relatorios.txt')
            
            try:
                with open(caminho_relatorio, 'a', encoding='utf-8') as f:
                    f.write(f"[{data_hora}] {usuario} (ID: {message.from_user.id}) reportou: {relatorio}\n")
                self.bot.reply_to(message, "✅ Seu alerta foi registrado e enviado com sucesso ao administrador do sistema!")
            except Exception as e:
                logging.error(f"Erro ao salvar report: {e}")

        @self.bot.message_handler(commands=['antilink'])
        def cmd_antilink(message):
            try:
                usuario_status = self.bot.get_chat_member(message.chat.id, message.from_user.id).status
                if usuario_status not in ['administrator', 'creator']:
                    return
                
                estado_atual = self.antilink_var.get()
                self.antilink_var.set(not estado_atual)
                self.salvar_configuracoes()
                
                if self.antilink_var.get():
                    self.bot.send_message(message.chat.id, "🛡️ *Anti-Link ATIVADO!* O bot começará a excluir qualquer mensagem com URLs ou convites.", parse_mode='Markdown')
                else:
                    self.bot.send_message(message.chat.id, "⚠️ *Anti-Link DESATIVADO!* O envio de links está temporariamente liberado no chat.", parse_mode='Markdown')
            except Exception as e:
                logging.error(f"Erro no antilink: {e}")

        @self.bot.message_handler(commands=['aviso'])
        def cmd_aviso(message):
            try:
                usuario_status = self.bot.get_chat_member(message.chat.id, message.from_user.id).status
                if usuario_status not in ['administrator', 'creator']:
                    return
                partes = message.text.split(maxsplit=1)
                if len(partes) < 2:
                    self.bot.reply_to(message, "⚠️ Informe a mensagem para o anúncio. Exemplo: `/aviso Pessoal, o sistema voltou!`", parse_mode='Markdown')
                    return
                
                texto = partes[1].strip()
                msg_fixada = self.bot.send_message(message.chat.id, f"📢 *COMUNICADO OFICIAL:*\n\n{texto}", parse_mode='Markdown')
                self.bot.pin_chat_message(message.chat.id, msg_fixada.message_id)
                self.bot.delete_message(message.chat.id, message.message_id)
            except Exception as e:
                logging.error(f"Erro no comando aviso: {e}")

        @self.bot.message_handler(commands=['id'])
        def cmd_id(message):
            texto = f"👤 *Identificação de Sistema:*\n\nSeu ID: `{message.from_user.id}`\nID do Grupo: `{message.chat.id}`"
            self.bot.reply_to(message, texto, parse_mode='Markdown')

        @self.bot.message_handler(commands=['links', 'urls'])
        def cmd_links(message):
            caminho_txt = self.txt_file_var.get()
            if not caminho_txt or not os.path.isfile(caminho_txt):
                self.bot.reply_to(message, "⚠️ O arquivo de links ainda não foi configurado.")
                return
            try:
                nome_arquivo = os.path.basename(caminho_txt)
                self.bot.send_chat_action(message.chat.id, 'upload_document')
                with open(caminho_txt, 'rb') as arquivo:
                    self.bot.send_document(chat_id=message.chat.id, document=arquivo, caption=f"🔗 Arquivo solicitado: `{nome_arquivo}`", parse_mode='Markdown')
            except Exception as e:
                logging.error(f"Erro no comando links: {e}")

        @self.bot.message_handler(commands=['fechar'])
        def cmd_fechar(message):
            try:
                usuario_status = self.bot.get_chat_member(message.chat.id, message.from_user.id).status
                if usuario_status in ['administrator', 'creator']:
                    perms = telebot.types.ChatPermissions(can_send_messages=False, can_send_media_messages=False, can_send_polls=False, can_send_other_messages=False, can_add_web_page_previews=False)
                    self.bot.set_chat_permissions(message.chat.id, perms)
                    self.bot.send_message(message.chat.id, "🔒 *GRUPO FECHADO!*", parse_mode='Markdown')
            except Exception as e:
                pass

        @self.bot.message_handler(commands=['abrir'])
        def cmd_abrir(message):
            try:
                usuario_status = self.bot.get_chat_member(message.chat.id, message.from_user.id).status
                if usuario_status in ['administrator', 'creator']:
                    perms = telebot.types.ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_polls=True, can_send_other_messages=True, can_add_web_page_previews=True)
                    self.bot.set_chat_permissions(message.chat.id, perms)
                    self.bot.send_message(message.chat.id, "🔓 *GRUPO ABERTO!*", parse_mode='Markdown')
            except Exception as e:
                pass

        @self.bot.message_handler(commands=['limpar'])
        def cmd_limpar(message):
            try:
                usuario_status = self.bot.get_chat_member(message.chat.id, message.from_user.id).status
                if usuario_status in ['administrator', 'creator']:
                    threading.Thread(target=self._processar_limpeza, args=(message,), daemon=True).start()
            except Exception:
                pass

        @self.bot.message_handler(commands=['video'])
        def cmd_video(message):
            partes = message.text.split(maxsplit=1)
            if len(partes) < 2:
                self.bot.reply_to(message, "❌ *Uso incorreto!* Exemplo: `/video link_aqui`", parse_mode='Markdown')
                return
            threading.Thread(target=self._processar_download_video, args=(message, partes[1].strip())).start()

        @self.bot.message_handler(commands=['baixar'])
        def cmd_baixar(message):
            pasta_zips = self.zip_folder_var.get()
            if not pasta_zips or not os.path.isdir(pasta_zips):
                self.bot.reply_to(message, "⚠️ Diretório ZIP inválido.")
                return

            arquivos_disponiveis = [f for f in os.listdir(pasta_zips) if f.lower().endswith('.zip')]
            arquivos_disponiveis.sort()
            partes = message.text.split(maxsplit=1)
            
            if len(partes) < 2:
                if not arquivos_disponiveis:
                    self.bot.reply_to(message, "📭 Nenhum ficheiro ZIP disponível.")
                    return
                texto_atual = "📋 *Ficheiros ZIP disponíveis:*\n\n"
                for i, arq in enumerate(arquivos_disponiveis):
                    linha = f"*{i+1}* - `{arq}`\n"
                    if len(texto_atual) + len(linha) > 4000:
                        self.bot.send_message(message.chat.id, texto_atual, parse_mode='Markdown')
                        texto_atual = ""
                        time.sleep(0.5)
                    texto_atual += linha
                texto_atual += "\nDigite: `/baixar 1`"
                self.bot.send_message(message.chat.id, texto_atual, parse_mode='Markdown')
                return

            escolha = partes[1].strip()
            nome_arquivo_pedido = None
            if escolha.isdigit():
                idx = int(escolha) - 1
                if 0 <= idx < len(arquivos_disponiveis):
                    nome_arquivo_pedido = arquivos_disponiveis[idx]
                else:
                    self.bot.reply_to(message, "❌ Número inválido.")
                    return
            else:
                if escolha in arquivos_disponiveis:
                    nome_arquivo_pedido = escolha
                else:
                    self.bot.reply_to(message, "❌ Opção inválida.")
                    return

            user_id = message.from_user.id
            tempo_atual = time.time()
            if user_id in self.cooldowns and tempo_atual - self.cooldowns[user_id] < 420:
                self.bot.reply_to(message, "🛑 *Anti-Spam!* Aguarde.", parse_mode='Markdown')
                return

            threading.Thread(target=self._processar_fila_envio, args=(message, pasta_zips, nome_arquivo_pedido, user_id, tempo_atual)).start()

        # --- MOTOR DO ANTI-LINK ---
        @self.bot.message_handler(func=lambda m: m.text and self.antilink_var.get() and any(x in m.text.lower() for x in ['http://', 'https://', 't.me/', 'www.']))
        def bloqueador_de_links(message):
            try:
                usuario_status = self.bot.get_chat_member(message.chat.id, message.from_user.id).status
                if usuario_status not in ['administrator', 'creator']:
                    self.bot.delete_message(message.chat.id, message.message_id)
            except Exception:
                pass

        # --- AVISO E SALVAMENTO AUTOMÁTICO DE MÍDIA ---
        @self.bot.message_handler(content_types=['photo', 'video'])
        def handle_midia(message):
            if not self.auto_save_var.get():
                return 
            pasta_midia = self.media_folder_var.get()
            if not pasta_midia or not os.path.isdir(pasta_midia):
                return
            try:
                if message.photo:
                    file_id = message.photo[-1].file_id
                    extensao = ".jpg"
                elif message.video:
                    file_id = message.video.file_id
                    extensao = ".mp4"

                # Log indicando o INÍCIO do download
                logging.info("⏳ Detetada nova mídia no chat. Iniciando download...")

                file_info = self.bot.get_file(file_id)
                baixar_arquivo = self.bot.download_file(file_info.file_path)
                nome_arquivo = f"midia_{message.message_id}{extensao}"
                caminho_salvar = os.path.join(pasta_midia, nome_arquivo)

                with open(caminho_salvar, 'wb') as f:
                    f.write(baixar_arquivo)
                
                # Log indicando o TÉRMINO do download
                logging.info(f"✅ Mídia salva com sucesso: {nome_arquivo} | Processo finalizado.")
            except Exception as e:
                logging.error(f"❌ Erro no download de mídia automática: {e}")

        self.is_running = True
        dados_atualizar = {
            "token": self.token_var.get(), "chat_id": self.chat_id_var.get(),
            "zip_folder": self.zip_folder_var.get(), "media_folder": self.media_folder_var.get(),
            "txt_file": self.txt_file_var.get(), "auto_save": self.auto_save_var.get(), 
            "startup": self.startup_var.get(), "antilink": self.antilink_var.get(),
            "bot_rodando": True
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(dados_atualizar, f)

        self.bot_thread = threading.Thread(target=self._rodar_polling, daemon=True)
        self.bot_thread.start()

        self.btn_iniciar.config(state="disabled")
        self.btn_parar.config(state="normal")
        
        if mostrar_alerta:
            messagebox.showinfo("Bot Iniciado", "As funcionalidades avançadas estão rodando perfeitamente!")

    # ================= FUNÇÕES DE SEGUNDO PLANO =================

    def _processar_limpeza(self, message):
        try:
            id_final = message.message_id
            mensagens_apagadas = 0
            if message.reply_to_message:
                id_inicial = message.reply_to_message.message_id
                quantidade = id_final - id_inicial + 1
                if quantidade > 100:
                    id_inicial = id_final - 99
                msg_status = self.bot.send_message(message.chat.id, "🧹 *Limpando o trecho...*", parse_mode='Markdown')
                for msg_id in range(id_inicial, id_final + 1):
                    try:
                        self.bot.delete_message(message.chat.id, msg_id)
                        mensagens_apagadas += 1
                    except Exception:
                        continue 
            else:
                partes = message.text.split()
                quantidade = int(partes[1]) if len(partes) > 1 and partes[1].isdigit() else 100
                quantidade = min(quantidade, 100)
                msg_status = self.bot.send_message(message.chat.id, f"🧹 *Limpando {quantidade} mensagens...*", parse_mode='Markdown')
                for i in range(quantidade + 1):
                    try:
                        self.bot.delete_message(message.chat.id, id_final - i)
                        mensagens_apagadas += 1
                    except Exception:
                        continue
            try:
                self.bot.edit_message_text(chat_id=message.chat.id, message_id=msg_status.message_id, text=f"✅ *Limpeza Concluída!*\n`{mensagens_apagadas}` mensagens removidas.", parse_mode='Markdown')
                time.sleep(5)
                self.bot.delete_message(message.chat.id, msg_status.message_id)
            except:
                pass
        except Exception:
            pass

    def _processar_download_video(self, message, url):
        msg_status = self.bot.reply_to(message, "⏳ <b>Processando o link...</b>", parse_mode='HTML')
        caminho_arquivo = None
        try:
            ydl_opts = {'outtmpl': os.path.join(os.getcwd(), 'temp_vid_%(id)s.%(ext)s'), 'format': 'best[ext=mp4]/best', 'quiet': True, 'no_warnings': True}
            self.bot.edit_message_text(chat_id=message.chat.id, message_id=msg_status.message_id, text="📥 <b>Baixando o vídeo...</b>", parse_mode='HTML')
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                caminho_arquivo = ydl.prepare_filename(info)
                if not os.path.exists(caminho_arquivo):
                    base, _ = os.path.splitext(caminho_arquivo)
                    for ext in ['.mp4', '.mkv', '.webm', '.3gp']:
                        if os.path.exists(base + ext):
                            caminho_arquivo = base + ext
                            break
            if os.path.getsize(caminho_arquivo) / (1024 * 1024) > 50:
                self.bot.edit_message_text(chat_id=message.chat.id, message_id=msg_status.message_id, text="❌ <b>Erro:</b> O vídeo ultrapassa 50MB.", parse_mode='HTML')
                return
            self.bot.edit_message_text(chat_id=message.chat.id, message_id=msg_status.message_id, text="📤 <b>Enviando vídeo...</b>", parse_mode='HTML')
            with open(caminho_arquivo, 'rb') as video_file:
                self.bot.send_video(chat_id=message.chat.id, video=video_file, caption=f"<b>🎥 Vídeo entregue!</b>\n{url}", parse_mode='HTML', timeout=600)
            try:
                self.bot.delete_message(message.chat.id, msg_status.message_id)
            except Exception:
                pass
        except Exception:
            try:
                self.bot.edit_message_text(chat_id=message.chat.id, message_id=msg_status.message_id, text="❌ <b>Erro:</b> Processamento falhou.", parse_mode='HTML')
            except Exception:
                pass
        finally:
            if caminho_arquivo and os.path.exists(caminho_arquivo):
                try:
                    os.remove(caminho_arquivo)
                except Exception:
                    pass

    def _processar_fila_envio(self, message, pasta_zips, nome_arquivo_inicial, user_id, tempo_atual):
        fila_envio = []
        if "parte_1" in nome_arquivo_inicial:
            prefixo, sufixo = nome_arquivo_inicial.split("parte_1")
            contador = 1
            while True:
                nome_parte = f"{prefixo}parte_{contador}{sufixo}"
                caminho_parte = os.path.join(pasta_zips, nome_parte)
                if os.path.exists(caminho_parte):
                    fila_envio.append((caminho_parte, nome_parte))
                    contador += 1
                else:
                    break
        else:
            fila_envio.append((os.path.join(pasta_zips, nome_arquivo_inicial), nome_arquivo_inicial))

        total_arquivos = len(fila_envio)
        msg_carregando = self.bot.reply_to(message, f"📥 *Processamento Iniciado!*\nIdentificados `{total_arquivos}` ficheiro(s).", parse_mode='Markdown')

        try:
            for indice, (caminho_completo, nome_atual) in enumerate(fila_envio):
                status_msg = self.bot.send_message(message.chat.id, f"📦 *Upload:* `{nome_atual}` ({indice+1}/{total_arquivos})...", parse_mode='Markdown')
                with open(caminho_completo, 'rb') as arquivo:
                    self.bot.send_document(chat_id=message.chat.id, document=arquivo, caption=f"📦 a/#2103294355", timeout=3600)
                try:
                    self.bot.delete_message(message.chat.id, status_msg.message_id)
                except Exception:
                    pass
                if indice < total_arquivos - 1:
                    time.sleep(20)

            self.cooldowns[user_id] = time.time()
            self.bot.edit_message_text(chat_id=message.chat.id, message_id=msg_carregando.message_id, text="✅ *Ciclo Concluído!*", parse_mode='Markdown')
        except Exception:
            pass

    def _rodar_polling(self):
        try:
            self.bot.infinity_polling()
        except Exception as e:
            logging.error(f"Erro no polling: {e}")

    def parar_bot(self):
        if self.bot and self.is_running:
            self.bot.stop_polling()
            self.is_running = False
            self.salvar_configuracoes()
            self.btn_iniciar.config(state="normal")
            self.btn_parar.config(state="disabled")
            messagebox.showinfo("Bot Parado", "O bot parou de escutar o grupo.")

if __name__ == "__main__":
    root = tk.Tk()
    app = TelegramBotApp(root)
    root.mainloop()