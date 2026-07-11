import customtkinter as ctk
import secrets
import string
import math
import sqlite3
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Configuração visual profissional (Dark Mode)
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ==========================================
# MÓDULO DE BANCO DE DADOS E CRIPTOGRAFIA
# ==========================================
def iniciar_banco():
    """Cria o banco de dados SQLite local se não existir."""
    conn = sqlite3.connect('cofre_senhas.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS senhas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            servico TEXT NOT NULL,
            usuario TEXT NOT NULL,
            senha_criptografada BLOB NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def gerar_chave_mestra(senha_mestra: str) -> bytes:
    """Deriva uma chave AES segura a partir da senha mestra do usuário."""
    # Nota: Em um sistema de produção em larga escala, o salt deve ser único e armazenado.
    # Aqui usamos um salt estático para manter o script em um único arquivo portátil.
    salt = b'senha_criptografica_segura_2026' 
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    chave = base64.urlsafe_b64encode(kdf.derive(senha_mestra.encode()))
    return chave

# ==========================================
# INTERFACE GRÁFICA PRINCIPAL
# ==========================================
class GeradorSenhasApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        iniciar_banco() # Prepara o cofre

        self.title("Security Hub - Gerador e Cofre")
        self.geometry("500x550")
        self.resizable(False, False)

        # Título
        self.titulo = ctk.CTkLabel(self, text="Security Hub", font=ctk.CTkFont(size=24, weight="bold"))
        self.titulo.pack(pady=(20, 5))

        # --- SEÇÃO: GERAÇÃO ---
        self.senha_entry = ctk.CTkEntry(self, font=ctk.CTkFont(size=18), width=400, justify="center")
        self.senha_entry.pack(pady=10)

        # Label de Entropia (Força da Senha)
        self.label_entropia = ctk.CTkLabel(self, text="Força: -- | Tempo de quebra: --", text_color="gray")
        self.label_entropia.pack(pady=(0, 10))

        # Botões de Ação Imediata
        self.frame_botoes = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_botoes.pack(pady=5)
        
        self.btn_copiar = ctk.CTkButton(self.frame_botoes, text="Copiar Senha", command=self.copiar_senha, width=190, fg_color="#28a745", hover_color="#218838")
        self.btn_copiar.pack(side="left", padx=5)

        self.btn_salvar = ctk.CTkButton(self.frame_botoes, text="Salvar no Cofre", command=self.abrir_janela_salvar, width=190, fg_color="#0056b3", hover_color="#004085")
        self.btn_salvar.pack(side="left", padx=5)

        # --- SEÇÃO: CONTROLES ---
        self.frame_tamanho = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_tamanho.pack(pady=(20, 5))
        
        self.label_tamanho = ctk.CTkLabel(self.frame_tamanho, text="Tamanho: 16", font=ctk.CTkFont(size=14))
        self.label_tamanho.pack(side="left", padx=10)
        
        self.slider_tamanho = ctk.CTkSlider(self.frame_tamanho, from_=8, to=128, command=self.atualizar_interface)
        self.slider_tamanho.set(16)
        self.slider_tamanho.pack(side="left", padx=10)

        self.label_nivel = ctk.CTkLabel(self, text="Nível de Segurança:", font=ctk.CTkFont(size=14))
        self.label_nivel.pack(pady=(15, 0))

        self.nivel_var = ctk.StringVar(value="extremo")
        self.frame_niveis = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_niveis.pack(pady=5)
        
        ctk.CTkRadioButton(self.frame_niveis, text="Básico", variable=self.nivel_var, value="basico", command=self.atualizar_interface).pack(side="left", padx=5)
        ctk.CTkRadioButton(self.frame_niveis, text="Forte", variable=self.nivel_var, value="forte", command=self.atualizar_interface).pack(side="left", padx=5)
        ctk.CTkRadioButton(self.frame_niveis, text="Extremo", variable=self.nivel_var, value="extremo", command=self.atualizar_interface).pack(side="left", padx=5)

        self.btn_gerar = ctk.CTkButton(self, text="Gerar Nova Senha", command=self.gerar_senha, height=45, font=ctk.CTkFont(size=16, weight="bold"))
        self.btn_gerar.pack(pady=20)

        # Label de status para mensagens dinâmicas
        self.label_status = ctk.CTkLabel(self, text="", text_color="#f39c12")
        self.label_status.pack()

    def atualizar_interface(self, *args):
        # Atualiza o texto do tamanho
        tamanho = int(self.slider_tamanho.get())
        self.label_tamanho.configure(text=f"Tamanho: {tamanho}")

    def calcular_entropia(self, tamanho, nivel):
        # Define o tamanho da "pool" de caracteres possíveis
        pool = 0
        if nivel == "basico":
            pool = 52 # a-z, A-Z
        elif nivel == "forte":
            pool = 62 # a-z, A-Z, 0-9
        elif nivel == "extremo":
            pool = 94 # a-z, A-Z, 0-9, símbolos

        # Fórmula da entropia em bits
        entropia = tamanho * math.log2(pool)
        
        # Estimativa grosseira de quebra (assumindo 100 bilhões de tentativas por segundo)
        tentativas_por_segundo = 100_000_000_000
        segundos = (2 ** entropia) / tentativas_por_segundo
        
        if segundos < 60:
            tempo_str = "Instantes"
            cor = "red"
        elif segundos < 86400:
            tempo_str = "Horas"
            cor = "orange"
        elif segundos < 31536000 * 100:
            tempo_str = "Anos"
            cor = "yellow"
        else:
            tempo_str = "Trilhões de anos"
            cor = "#28a745" # Verde
            
        self.label_entropia.configure(text=f"Entropia: {int(entropia)} bits | Resistência: {tempo_str}", text_color=cor)

    def gerar_senha(self):
        tamanho = int(self.slider_tamanho.get())
        nivel = self.nivel_var.get()
        
        letras = string.ascii_letters
        numeros = string.digits
        simbolos = string.punctuation

        if nivel == "basico":
            caracteres = letras
        elif nivel == "forte":
            caracteres = letras + numeros
        else:
            caracteres = letras + numeros + simbolos

        senha_gerada = ''.join(secrets.choice(caracteres) for _ in range(tamanho))

        if nivel == "extremo" and tamanho >= 4:
            senha_lista = list(senha_gerada)
            senha_lista[0] = secrets.choice(string.ascii_lowercase)
            senha_lista[1] = secrets.choice(string.ascii_uppercase)
            senha_lista[2] = secrets.choice(string.digits)
            senha_lista[3] = secrets.choice(string.punctuation)
            secrets.SystemRandom().shuffle(senha_lista)
            senha_gerada = ''.join(senha_lista)

        self.senha_entry.delete(0, 'end')
        self.senha_entry.insert(0, senha_gerada)
        
        self.calcular_entropia(tamanho, nivel)
        self.label_status.configure(text="")

    def copiar_senha(self):
        senha = self.senha_entry.get()
        if senha:
            self.clipboard_clear()
            self.clipboard_append(senha)
            self.update()
            
            self.label_status.configure(text="Senha copiada! Será limpa em 30 segundos.")
            # Agenda a limpeza da área de transferência (30.000 milissegundos)
            self.after(30000, self.limpar_area_transferencia, senha)

    def limpar_area_transferencia(self, senha_alvo):
        """Limpa a área de transferência apenas se a senha ainda estiver lá."""
        try:
            conteudo_atual = self.clipboard_get()
            if conteudo_atual == senha_alvo:
                self.clipboard_clear()
                self.update()
                self.label_status.configure(text="Área de transferência limpa por segurança.")
        except Exception:
            pass # Ignora caso a área de transferência já esteja vazia ou inacessível

    # --- FUNÇÕES DO COFRE (VAULT) ---
    def abrir_janela_salvar(self):
        senha_atual = self.senha_entry.get()
        if not senha_atual:
            self.label_status.configure(text="Gere uma senha primeiro!", text_color="red")
            return
            
        janela_cofre = ctk.CTkToplevel(self)
        janela_cofre.title("Salvar no Cofre")
        janela_cofre.geometry("350x350")
        janela_cofre.attributes('-topmost', True) # Mantém a janela na frente

        ctk.CTkLabel(janela_cofre, text="Plataforma/Site:", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 0))
        entry_servico = ctk.CTkEntry(janela_cofre, width=250)
        entry_servico.pack(pady=5)

        ctk.CTkLabel(janela_cofre, text="E-mail/Usuário:", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 0))
        entry_usuario = ctk.CTkEntry(janela_cofre, width=250)
        entry_usuario.pack(pady=5)

        ctk.CTkLabel(janela_cofre, text="Sua Senha Mestra (Não perca!):", font=ctk.CTkFont(weight="bold")).pack(pady=(10, 0))
        entry_mestra = ctk.CTkEntry(janela_cofre, width=250, show="*")
        entry_mestra.pack(pady=5)

        def confirmar_salvamento():
            servico = entry_servico.get()
            usuario = entry_usuario.get()
            mestra = entry_mestra.get()

            if not servico or not usuario or not mestra:
                return

            try:
                # Gera a chave AES e criptografa a senha
                chave = gerar_chave_mestra(mestra)
                fernet = Fernet(chave)
                senha_bytes = senha_atual.encode()
                senha_criptografada = fernet.encrypt(senha_bytes)

                # Salva no banco de dados local
                conn = sqlite3.connect('cofre_senhas.db')
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO senhas (servico, usuario, senha_criptografada) VALUES (?, ?, ?)",
                    (servico, usuario, senha_criptografada)
                )
                conn.commit()
                conn.close()

                self.label_status.configure(text=f"Senha salva com sucesso para: {servico}", text_color="#28a745")
                janela_cofre.destroy()
            except Exception as e:
                self.label_status.configure(text="Erro ao salvar senha.", text_color="red")

        ctk.CTkButton(janela_cofre, text="Criptografar e Salvar", command=confirmar_salvamento, fg_color="#8e44ad", hover_color="#732d91").pack(pady=20)


if __name__ == "__main__":
    app = GeradorSenhasApp()
    app.mainloop()