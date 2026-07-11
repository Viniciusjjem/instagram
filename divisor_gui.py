import os
import shutil
import threading
import pyzipper
import customtkinter as ctk
from tkinter import filedialog

# Configuração visual do aplicativo
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class DivisorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Ferramenta ZIP Universal (Dividir e Extrair)")
        self.geometry("550x650")
        
        # Variáveis globais da classe
        self.pasta_origem = ""
        self.pasta_destino = ""
        self.arquivos_zip_extracao = []
        self.pasta_destino_extracao = ""
        self.max_mb = 0
        
        # --- Sistema de Abas (Tabs) ---
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Criação das duas abas principais
        self.tab_compactar = self.tabview.add("Dividir & Compactar")
        self.tab_extrair = self.tabview.add("Extrair ZIPs")
        
        self.construir_aba_compactar()
        self.construir_aba_extrair()

    # =======================================================
    # ABA 1: DIVIDIR E COMPACTAR
    # =======================================================
    def construir_aba_compactar(self):
        self.label_titulo = ctk.CTkLabel(self.tab_compactar, text="Organizador Seguro de Arquivos", font=ctk.CTkFont(size=18, weight="bold"))
        self.label_titulo.pack(pady=(10, 10))

        self.label_plataforma = ctk.CTkLabel(self.tab_compactar, text="Escolha a plataforma ou limite:")
        self.label_plataforma.pack()

        self.opcao_plataforma = ctk.CTkOptionMenu(
            self.tab_compactar,
            values=["Telegram (Max 495MB)", "WhatsApp Docs (Max 1900MB)", "Zangi (Max 45MB)", "Outros (Personalizado)"],
            command=self.mudar_plataforma
        )
        self.opcao_plataforma.pack(pady=5)

        self.entrada_tamanho = ctk.CTkEntry(self.tab_compactar, placeholder_text="Tamanho máximo em MB")
        self.entrada_tamanho.pack(pady=5)
        self.entrada_tamanho.configure(state="disabled", fg_color="gray20")
        
        self.frame_privacidade = ctk.CTkFrame(self.tab_compactar)
        self.frame_privacidade.pack(pady=10, padx=20, fill="x")
        
        self.label_priv = ctk.CTkLabel(self.frame_privacidade, text="Opções de Privacidade", font=ctk.CTkFont(weight="bold"))
        self.label_priv.pack(pady=5)
        
        self.check_metadados = ctk.CTkCheckBox(self.frame_privacidade, text="Remover Metadados (Datas e Permissões)")
        self.check_metadados.pack(pady=5, anchor="w", padx=20)
        
        self.check_senha = ctk.CTkCheckBox(self.frame_privacidade, text="Proteger ZIP com Senha", command=self.alternar_senha)
        self.check_senha.pack(pady=5, anchor="w", padx=20)
        
        self.entrada_senha = ctk.CTkEntry(self.frame_privacidade, placeholder_text="Digite a senha desejada", show="*")
        self.entrada_senha.pack(pady=5, padx=20, fill="x")
        self.entrada_senha.configure(state="disabled", fg_color="gray20")

        self.btn_origem = ctk.CTkButton(self.tab_compactar, text="1. Selecionar Pasta de Origem", command=self.selecionar_origem)
        self.btn_origem.pack(pady=(10, 5))
        
        self.btn_destino = ctk.CTkButton(self.tab_compactar, text="2. Selecionar Pasta de Destino", command=self.selecionar_destino)
        self.btn_destino.pack(pady=5)
        
        self.btn_iniciar = ctk.CTkButton(self.tab_compactar, text="3. Iniciar Processo", command=self.iniciar_thread_compactar, fg_color="#27ae60", hover_color="#2ecc71")
        self.btn_iniciar.pack(pady=10)
        
        self.label_status = ctk.CTkLabel(self.tab_compactar, text="Aguardando configurações...", text_color="gray")
        self.label_status.pack(pady=5)

    def mudar_plataforma(self, escolha):
        if escolha == "Outros (Personalizado)":
            self.entrada_tamanho.configure(state="normal", fg_color=["#F9F9FA", "#343638"])
            self.entrada_tamanho.focus()
        else:
            self.entrada_tamanho.delete(0, "end")
            self.entrada_tamanho.configure(state="disabled", fg_color="gray20")

    def alternar_senha(self):
        if self.check_senha.get():
            self.entrada_senha.configure(state="normal", fg_color=["#F9F9FA", "#343638"])
            self.entrada_senha.focus()
        else:
            self.entrada_senha.delete(0, "end")
            self.entrada_senha.configure(state="disabled", fg_color="gray20")

    def selecionar_origem(self):
        self.pasta_origem = filedialog.askdirectory(title="Selecione onde estão os arquivos")
        if self.pasta_origem:
            self.label_status.configure(text=f"Origem: {os.path.basename(self.pasta_origem)}", text_color="white")

    def selecionar_destino(self):
        self.pasta_destino = filedialog.askdirectory(title="Selecione onde criar os arquivos ZIP")
        if self.pasta_destino:
            self.label_status.configure(text=f"Destino: {os.path.basename(self.pasta_destino)}", text_color="white")

    def iniciar_thread_compactar(self):
        if not self.pasta_origem or not self.pasta_destino:
            self.label_status.configure(text="Erro: Selecione as duas pastas!", text_color="#e74c3c")
            return
            
        if self.check_senha.get() and not self.entrada_senha.get():
            self.label_status.configure(text="Erro: Digite uma senha!", text_color="#e74c3c")
            return
        
        escolha = self.opcao_plataforma.get()
        if "Telegram" in escolha: self.max_mb = 495
        elif "WhatsApp" in escolha: self.max_mb = 1900
        elif "Zangi" in escolha: self.max_mb = 45
        else:
            try:
                self.max_mb = float(self.entrada_tamanho.get().replace(',', '.'))
                if self.max_mb <= 0: raise ValueError
            except ValueError:
                self.label_status.configure(text="Erro: Digite um número válido em MB!", text_color="#e74c3c")
                return

        self.btn_iniciar.configure(state="disabled")
        self.label_status.configure(text=f"Processando...", text_color="#f1c40f")
        threading.Thread(target=self.processar_e_zipar, daemon=True).start()

    def compactar_pasta(self, caminho_pasta):
        if not os.path.exists(caminho_pasta) or not os.listdir(caminho_pasta): return
        nome_pasta = os.path.basename(caminho_pasta)
        caminho_zip = f"{caminho_pasta}.zip"
        self.label_status.configure(text=f"Compactando {nome_pasta}.zip...", text_color="#f1c40f")
        
        if self.check_senha.get() and self.entrada_senha.get():
            with pyzipper.AESZipFile(caminho_zip, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as zf:
                zf.setpassword(self.entrada_senha.get().encode('utf-8'))
                for root, _, files in os.walk(caminho_pasta):
                    for file in files:
                        c_comp = os.path.join(root, file)
                        zf.write(c_comp, os.path.relpath(c_comp, caminho_pasta))
        else:
            shutil.make_archive(caminho_pasta, 'zip', caminho_pasta)
        shutil.rmtree(caminho_pasta)

    def processar_e_zipar(self):
        tamanho_max_bytes = self.max_mb * 1024 * 1024
        pasta_atual, tamanho_atual = 1, 0
        
        caminho_pasta_atual = os.path.join(self.pasta_destino, f"parte_{pasta_atual}")
        os.makedirs(caminho_pasta_atual, exist_ok=True)
        
        try:
            arquivos = [a for a in os.listdir(self.pasta_origem) if os.path.isfile(os.path.join(self.pasta_origem, a))]
            for arquivo in arquivos:
                c_arq = os.path.join(self.pasta_origem, arquivo)
                t_arq = os.path.getsize(c_arq)
                
                if t_arq > tamanho_max_bytes: continue
                if tamanho_atual + t_arq > tamanho_max_bytes:
                    self.compactar_pasta(caminho_pasta_atual)
                    pasta_atual += 1
                    tamanho_atual = 0
                    caminho_pasta_atual = os.path.join(self.pasta_destino, f"parte_{pasta_atual}")
                    os.makedirs(caminho_pasta_atual, exist_ok=True)
                    
                self.label_status.configure(text=f"Copiando: {arquivo[:20]}...", text_color="white")
                if self.check_metadados.get(): shutil.copy(c_arq, caminho_pasta_atual)
                else: shutil.copy2(c_arq, caminho_pasta_atual)
                tamanho_atual += t_arq
                
            self.compactar_pasta(caminho_pasta_atual)
            self.label_status.configure(text="Sucesso! Processo finalizado com segurança.", text_color="#2ecc71")
        except Exception as e:
            self.label_status.configure(text=f"Erro: {str(e)}", text_color="#e74c3c")
        finally:
            self.btn_iniciar.configure(state="normal")

    # =======================================================
    # ABA 2: EXTRAIR ZIPS
    # =======================================================
    def construir_aba_extrair(self):
        self.label_titulo_ext = ctk.CTkLabel(self.tab_extrair, text="Extração Segura de ZIPs", font=ctk.CTkFont(size=18, weight="bold"))
        self.label_titulo_ext.pack(pady=(10, 20))

        self.btn_sel_zips = ctk.CTkButton(self.tab_extrair, text="1. Selecionar Arquivo(s) ZIP", command=self.selecionar_zips_extracao)
        self.btn_sel_zips.pack(pady=10)

        self.btn_sel_dest_ext = ctk.CTkButton(self.tab_extrair, text="2. Selecionar Pasta de Destino", command=self.selecionar_destino_extracao)
        self.btn_sel_dest_ext.pack(pady=10)

        self.entrada_senha_ext = ctk.CTkEntry(self.tab_extrair, placeholder_text="Senha do ZIP (se houver, deixe em branco se não)", show="*")
        self.entrada_senha_ext.pack(pady=15, padx=40, fill="x")

        self.btn_iniciar_ext = ctk.CTkButton(self.tab_extrair, text="3. Iniciar Extração", command=self.iniciar_thread_extracao, fg_color="#8e44ad", hover_color="#9b59b6")
        self.btn_iniciar_ext.pack(pady=20)

        self.label_status_ext = ctk.CTkLabel(self.tab_extrair, text="Aguardando seleção de arquivos...", text_color="gray")
        self.label_status_ext.pack(pady=5)

    def selecionar_zips_extracao(self):
        arquivos = filedialog.askopenfilenames(title="Selecione um ou mais arquivos ZIP", filetypes=[("Arquivos ZIP", "*.zip")])
        if arquivos:
            self.arquivos_zip_extracao = list(arquivos)
            qtd = len(self.arquivos_zip_extracao)
            self.label_status_ext.configure(text=f"{qtd} arquivo(s) ZIP selecionado(s).", text_color="white")

    def selecionar_destino_extracao(self):
        pasta = filedialog.askdirectory(title="Selecione onde salvar os arquivos extraídos")
        if pasta:
            self.pasta_destino_extracao = pasta
            self.label_status_ext.configure(text=f"Destino: {os.path.basename(self.pasta_destino_extracao)}", text_color="white")

    def iniciar_thread_extracao(self):
        if not self.arquivos_zip_extracao:
            self.label_status_ext.configure(text="Erro: Selecione pelo menos um arquivo ZIP!", text_color="#e74c3c")
            return
        if not self.pasta_destino_extracao:
            self.label_status_ext.configure(text="Erro: Selecione uma pasta de destino!", text_color="#e74c3c")
            return

        self.btn_iniciar_ext.configure(state="disabled")
        self.label_status_ext.configure(text="Iniciando extração...", text_color="#f1c40f")
        threading.Thread(target=self.processar_extracao, daemon=True).start()

    def processar_extracao(self):
        senha = self.entrada_senha_ext.get()
        erros = 0
        
        try:
            for zip_path in self.arquivos_zip_extracao:
                nome_arq = os.path.basename(zip_path)
                self.label_status_ext.configure(text=f"Extraindo: {nome_arq[:30]}...", text_color="white")
                
                try:
                    with pyzipper.AESZipFile(zip_path, 'r') as zf:
                        if senha:
                            zf.setpassword(senha.encode('utf-8'))
                        zf.extractall(path=self.pasta_destino_extracao)
                except RuntimeError as e:
                    if 'password' in str(e).lower() or 'bad password' in str(e).lower():
                        self.label_status_ext.configure(text=f"Erro: Senha incorreta no arquivo {nome_arq}!", text_color="#e74c3c")
                        erros += 1
                        break
                    else:
                        raise e
                        
            if erros == 0:
                self.label_status_ext.configure(text="Sucesso! Extração concluída.", text_color="#2ecc71")
                
        except Exception as e:
            self.label_status_ext.configure(text=f"Erro na extração: {str(e)}", text_color="#e74c3c")
        finally:
            self.btn_iniciar_ext.configure(state="normal")

if __name__ == "__main__":
    app = DivisorApp()
    app.mainloop()
