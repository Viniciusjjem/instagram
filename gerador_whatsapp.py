import customtkinter as ctk
import phonenumbers
from phonenumbers import phonenumberutil
import threading
import random
import os
import csv
import time
import sqlite3
from tkinter import filedialog
from plyer import notification

# Configuração Visual
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

class DatabaseManager:
    """Gerencia a persistência de dados para evitar duplicatas eternamente."""
    def __init__(self, db_name="anti_colisao.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.criar_tabela()

    def criar_tabela(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS numeros_gerados (
                numero TEXT PRIMARY KEY,
                data_geracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def numero_existe(self, numero):
        self.cursor.execute('SELECT 1 FROM numeros_gerados WHERE numero = ?', (numero,))
        return self.cursor.fetchone() is not None

    def salvar_lote(self, numeros):
        try:
            self.cursor.executemany(
                'INSERT OR IGNORE INTO numeros_gerados (numero) VALUES (?)', 
                [(n,) for n in numeros]
            )
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Erro no banco de dados: {e}")

    def contar_total(self):
        self.cursor.execute('SELECT COUNT(*) FROM numeros_gerados')
        return self.cursor.fetchone()[0]


class GeradorNumerosApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Gerador VCF Enterprise - v3.1")
        self.geometry("650x750")
        self.resizable(False, False)
        
        # Mapeamento Amigável de Países e Siglas (Correção do Bug)
        self.paises_map = {
            "🇧🇷 Brasil (BR)": "BR",
            "🇺🇸 Estados Unidos (US)": "US",
            "🇵🇹 Portugal (PT)": "PT",
            "🇲🇽 México (MX)": "MX",
            "🇪🇸 Espanha (ES)": "ES",
            "🇦🇷 Argentina (AR)": "AR",
            "🇨🇴 Colômbia (CO)": "CO",
            "🇬🇧 Reino Unido (GB)": "GB"
        }
        
        # Estado e Banco de Dados
        self.db = DatabaseManager()
        self.is_generating = False
        self.stop_event = threading.Event()
        self.diretorio_saida = ctk.StringVar(value=os.getcwd())
        
        self.criar_interface()
        self.log(f"[Sistema] Banco de Dados inicializado. Total histórico: {self.db.contar_total()} números.")

    def criar_interface(self):
        # Título
        lbl_titulo = ctk.CTkLabel(self, text="GERADOR VCF ENTERPRISE", font=("Consolas", 24, "bold"), text_color="#00FF00")
        lbl_titulo.pack(pady=(20, 10))

        # Frame Principal
        frame_config = ctk.CTkFrame(self, fg_color="#1E1E1E", border_width=1, border_color="#333333")
        frame_config.pack(padx=20, pady=10, fill="x")

        # Diretório
        ctk.CTkLabel(frame_config, text="Salvar em:", font=("Consolas", 12)).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        frame_dir = ctk.CTkFrame(frame_config, fg_color="transparent")
        frame_dir.grid(row=0, column=1, padx=10, pady=10, sticky="we")
        self.entry_dir = ctk.CTkEntry(frame_dir, textvariable=self.diretorio_saida, state="disabled", width=250)
        self.entry_dir.pack(side="left", padx=(0, 5))
        ctk.CTkButton(frame_dir, text="Procurar", width=80, command=self.escolher_diretorio, fg_color="#333333").pack(side="left")

        # Configurações de Geração (ComboBox Atualizado)
        ctk.CTkLabel(frame_config, text="País (Nome):", font=("Consolas", 12)).grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.combo_pais = ctk.CTkComboBox(frame_config, values=list(self.paises_map.keys()), width=200)
        self.combo_pais.set("🇧🇷 Brasil (BR)")
        self.combo_pais.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        ctk.CTkLabel(frame_config, text="DDD (Opcional):", font=("Consolas", 12)).grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.entry_ddd = ctk.CTkEntry(frame_config, placeholder_text="Ex: 47")
        self.entry_ddd.grid(row=2, column=1, padx=10, pady=10, sticky="w")

        ctk.CTkLabel(frame_config, text="Quantidade:", font=("Consolas", 12)).grid(row=3, column=0, padx=10, pady=10, sticky="w")
        self.entry_qtd = ctk.CTkEntry(frame_config, placeholder_text="Ex: 10000")
        self.entry_qtd.grid(row=3, column=1, padx=10, pady=10, sticky="w")

        # Exportação
        ctk.CTkLabel(frame_config, text="Formatos:", font=("Consolas", 12)).grid(row=4, column=0, padx=10, pady=10, sticky="w")
        frame_formatos = ctk.CTkFrame(frame_config, fg_color="transparent")
        frame_formatos.grid(row=4, column=1, padx=10, pady=10, sticky="w")
        
        self.var_txt = ctk.BooleanVar(value=False)
        self.var_csv = ctk.BooleanVar(value=False)
        self.var_vcf = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(frame_formatos, text="TXT", variable=self.var_txt).pack(side="left", padx=5)
        ctk.CTkCheckBox(frame_formatos, text="CSV", variable=self.var_csv).pack(side="left", padx=5)
        ctk.CTkCheckBox(frame_formatos, text="VCF", variable=self.var_vcf).pack(side="left", padx=5)

        # Controles
        frame_botoes = ctk.CTkFrame(self, fg_color="transparent")
        frame_botoes.pack(padx=20, pady=10, fill="x")

        self.btn_gerar = ctk.CTkButton(frame_botoes, text="INICIAR", font=("Consolas", 14, "bold"), command=self.iniciar_geracao, fg_color="#006400")
        self.btn_gerar.pack(side="left", expand=True, padx=5, fill="x")
        self.btn_parar = ctk.CTkButton(frame_botoes, text="PARAR", font=("Consolas", 14, "bold"), command=self.parar_geracao, fg_color="#8B0000", state="disabled")
        self.btn_parar.pack(side="left", expand=True, padx=5, fill="x")

        # Progresso e Log
        self.lbl_status = ctk.CTkLabel(self, text="Aguardando...", font=("Consolas", 12))
        self.lbl_status.pack(pady=(10, 0))
        self.progressbar = ctk.CTkProgressBar(self, progress_color="#00FF00")
        self.progressbar.pack(padx=20, pady=10, fill="x")
        self.progressbar.set(0)

        self.log_box = ctk.CTkTextbox(self, height=180, font=("Consolas", 12), fg_color="#0A0A0A", text_color="#00FF00", state="disabled")
        self.log_box.pack(padx=20, pady=(0, 20), fill="both", expand=True)

    # --- Funções de UI Auxiliares ---
    def escolher_diretorio(self):
        dir_selecionado = filedialog.askdirectory()
        if dir_selecionado:
            self.diretorio_saida.set(dir_selecionado)

    def log(self, mensagem):
        self.after(0, lambda: self._escrever_log(mensagem))

    def _escrever_log(self, mensagem):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", mensagem + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def atualizar_progresso(self, valor, texto):
        self.after(0, lambda: self._set_progresso(valor, texto))

    def _set_progresso(self, valor, texto):
        self.progressbar.set(valor)
        self.lbl_status.configure(text=texto)

    # --- Lógica de Negócio ---
    def parar_geracao(self):
        if self.is_generating:
            self.log("[!] Parando processo graciosamente...")
            self.stop_event.set()

    def gerar_numero_base(self, regiao, ddd_especifico):
        """Regras matemáticas específicas por país para evitar travamentos."""
        if regiao == "BR":
            ddd = ddd_especifico if ddd_especifico else str(random.randint(11, 99))
            return f"+55{ddd}9{random.randint(10000000, 99999999)}"
        elif regiao == "US":
            area = ddd_especifico if ddd_especifico else str(random.randint(201, 989))
            return f"+1{area}{random.randint(1000000, 9999999)}"
        elif regiao == "PT":
            prefixo = random.choice(["91", "92", "93", "96"])
            return f"+351{prefixo}{random.randint(1000000, 9999999)}"
        elif regiao == "MX":
            ddd = ddd_especifico if ddd_especifico else str(random.randint(10, 99))
            return f"+52{ddd}{random.randint(10000000, 99999999)}"
        elif regiao == "ES": # Espanha
            return f"+346{random.randint(10000000, 99999999)}"
        elif regiao == "AR": # Argentina
            ddd = ddd_especifico if ddd_especifico else "11"
            return f"+549{ddd}{random.randint(10000000, 99999999)}"
        elif regiao == "CO": # Colômbia
            return f"+573{random.randint(100000000, 999999999)}"
        elif regiao == "GB": # Reino Unido
            return f"+447{random.randint(100000000, 999999999)}"
        else:
            # Fallback seguro
            codigo = phonenumbers.country_code_for_region(regiao)
            return f"+{codigo}{random.randint(10000000, 9999999999)}"

    def iniciar_geracao(self):
        if self.is_generating: return
        
        try:
            qtd = int(self.entry_qtd.get())
            if qtd <= 0: raise ValueError
        except:
            self.log("[Erro] Quantidade inválida.")
            return

        formatos = {"txt": self.var_txt.get(), "csv": self.var_csv.get(), "vcf": self.var_vcf.get()}
        if not any(formatos.values()):
            self.log("[Erro] Selecione um formato.")
            return

        self.is_generating = True
        self.stop_event.clear()
        
        self.btn_gerar.configure(state="disabled", fg_color="#333333")
        self.btn_parar.configure(state="normal")
        self.progressbar.set(0)
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        
        # Pega o nome selecionado e extrai a sigla real do dicionário
        pais_selecionado = self.combo_pais.get()
        sigla = self.paises_map[pais_selecionado]
        
        ddd = self.entry_ddd.get().strip()
        
        threading.Thread(target=self.processar_geracao, args=(sigla, ddd, qtd, formatos), daemon=True).start()

    def processar_geracao(self, sigla, ddd, qtd, formatos):
        self.log(f"[*] Iniciando rotina. Alvo: {qtd} registros para {sigla}.")
        numeros_validos = []
        duplicatas = 0
        lote_atual = set()
        
        while len(numeros_validos) < qtd and not self.stop_event.is_set():
            num_bruto = self.gerar_numero_base(sigla, ddd)
            
            try:
                parsed = phonenumbers.parse(num_bruto, sigla)
                if phonenumbers.is_valid_number(parsed):
                    num_formatado = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                    
                    if num_formatado not in lote_atual and not self.db.numero_existe(num_formatado):
                        numeros_validos.append(num_formatado)
                        lote_atual.add(num_formatado)
                        
                        if len(numeros_validos) % max(1, qtd // 100) == 0:
                            self.atualizar_progresso(len(numeros_validos) / qtd, f"Gerados: {len(numeros_validos)}/{qtd}")
                    else:
                        duplicatas += 1
            except phonenumberutil.NumberParseException:
                pass

        status_msg = "Abortado" if self.stop_event.is_set() else "Concluído"
        self.log(f"[*] {status_msg}. Duplicatas globais bloqueadas: {duplicatas}.")
        
        if numeros_validos:
            self.db.salvar_lote(numeros_validos)
            self.salvar_arquivos(numeros_validos, formatos)
            self.enviar_notificacao(f"Tarefa {status_msg}", f"{len(numeros_validos)} contatos gerados.")

        self.after(0, self.finalizar_ui, len(numeros_validos))

    def salvar_arquivos(self, numeros, formatos):
        timestamp = int(time.time())
        pasta = self.diretorio_saida.get()
        self.log("[*] Escrevendo arquivos no disco...")
        
        if formatos["txt"]:
            with open(os.path.join(pasta, "numeros_gerados.txt"), "a", encoding="utf-8") as f:
                f.write("\n".join(numeros) + "\n")

        if formatos["csv"]:
            caminho = os.path.join(pasta, "numeros_gerados.csv")
            existe = os.path.isfile(caminho)
            with open(caminho, "a", newline='', encoding="utf-8") as f:
                writer = csv.writer(f)
                if not existe: writer.writerow(["Telefone"])
                writer.executemany("INSERT", [[n] for n in numeros])

        if formatos["vcf"]:
            caminho = os.path.join(pasta, f"contatos_{timestamp}.vcf")
            with open(caminho, "w", encoding="utf-8") as f:
                for i, n in enumerate(numeros):
                    f.write(f"BEGIN:VCARD\nVERSION:3.0\nFN:Contato_{timestamp}_{i+1}\nTEL;TYPE=CELL:{n}\nEND:VCARD\n")
            self.log(f" -> VCF {timestamp} salvo.")

    def enviar_notificacao(self, titulo, mensagem):
        try:
            notification.notify(title=titulo, message=mensagem, app_name="Gerador VCF", timeout=5)
        except:
            pass

    def finalizar_ui(self, qtd_gerada):
        self.is_generating = False
        self.btn_gerar.configure(state="normal", fg_color="#006400")
        self.btn_parar.configure(state="disabled")
        self.atualizar_progresso(1.0 if qtd_gerada > 0 else 0, "Pronto.")
        self.log(f"[Sistema] Tarefa finalizada. Total no Banco de Dados: {self.db.contar_total()}")

if __name__ == "__main__":
    app = GeradorNumerosApp()
    app.mainloop()