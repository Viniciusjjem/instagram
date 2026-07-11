import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading

class MovimentadorArquivos:
    def __init__(self, root):
        self.root = root
        self.root.title("Movimentador de Arquivos")
        self.root.geometry("500x250")
        self.root.resizable(False, False)

        self.pasta_origem = ""
        self.pasta_destino = ""

        self.criar_interface()

    def criar_interface(self):
        # Frame principal
        frame = tk.Frame(self.root, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        # Seleção de Origem
        tk.Label(frame, text="Pasta de Origem:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.lbl_origem = tk.Label(frame, text="Nenhuma selecionada", fg="blue", width=35, anchor="w")
        self.lbl_origem.grid(row=0, column=1, padx=5, pady=5)
        tk.Button(frame, text="Procurar", command=self.selecionar_origem).grid(row=0, column=2, pady=5)

        # Seleção de Destino
        tk.Label(frame, text="Pasta de Destino:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.lbl_destino = tk.Label(frame, text="Nenhuma selecionada", fg="blue", width=35, anchor="w")
        self.lbl_destino.grid(row=1, column=1, padx=5, pady=5)
        tk.Button(frame, text="Procurar", command=self.selecionar_destino).grid(row=1, column=2, pady=5)

        # Barra de progresso e Status
        self.progresso = ttk.Progressbar(frame, orient=tk.HORIZONTAL, length=400, mode='determinate')
        self.progresso.grid(row=2, column=0, columnspan=3, pady=20)
        
        self.lbl_status = tk.Label(frame, text="Aguardando...")
        self.lbl_status.grid(row=3, column=0, columnspan=3)

        # Botão Mover
        self.btn_mover = tk.Button(frame, text="Mover Arquivos", command=self.iniciar_movimentacao, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.btn_mover.grid(row=4, column=0, columnspan=3, pady=10)

    def selecionar_origem(self):
        pasta = filedialog.askdirectory(title="Selecione a Origem")
        if pasta:
            self.pasta_origem = pasta
            self.lbl_origem.config(text=pasta)

    def selecionar_destino(self):
        pasta = filedialog.askdirectory(title="Selecione o Destino")
        if pasta:
            self.pasta_destino = pasta
            self.lbl_destino.config(text=pasta)

    def iniciar_movimentacao(self):
        if not self.pasta_origem or not self.pasta_destino:
            messagebox.showwarning("Aviso", "Por favor, selecione as pastas de origem e destino.")
            return
        if self.pasta_origem == self.pasta_destino:
            messagebox.showerror("Erro", "As pastas de origem e destino não podem ser iguais.")
            return

        self.btn_mover.config(state=tk.DISABLED)
        self.progresso["value"] = 0
        
        # Executa em uma thread separada para não travar a interface
        threading.Thread(target=self.mover_arquivos_thread, daemon=True).start()

    def mover_arquivos_thread(self):
        try:
            itens = os.listdir(self.pasta_origem)
            total_itens = len(itens)
            
            if total_itens == 0:
                self.root.after(0, self.atualizar_status, "A pasta de origem está vazia.", 0)
                messagebox.showinfo("Informação", "Não há arquivos para mover.")
                self.root.after(0, lambda: self.btn_mover.config(state=tk.NORMAL))
                return

            self.progresso["maximum"] = total_itens
            movidos = 0

            for item in itens:
                caminho_origem = os.path.join(self.pasta_origem, item)
                caminho_destino = os.path.join(self.pasta_destino, item)

                # Proteção contra arquivos com o mesmo nome no destino
                if os.path.exists(caminho_destino):
                    nome, ext = os.path.splitext(item)
                    caminho_destino = os.path.join(self.pasta_destino, f"{nome}_copia{ext}")

                shutil.move(caminho_origem, caminho_destino)
                movidos += 1
                
                # Atualiza a interface gráfica com o progresso atual
                self.root.after(0, self.atualizar_status, f"Movendo: {item}", movidos)

            self.root.after(0, self.finalizar_com_sucesso, movidos)

        except Exception as e:
            self.root.after(0, self.mostrar_erro, str(e))

    def atualizar_status(self, texto, valor_progresso):
        self.lbl_status.config(text=texto)
        self.progresso["value"] = valor_progresso

    def finalizar_com_sucesso(self, total):
        self.lbl_status.config(text="Concluído!")
        messagebox.showinfo("Sucesso", f"{total} item(ns) movido(s) com sucesso!")
        self.btn_mover.config(state=tk.NORMAL)
        # Limpa as seleções para uma nova operação
        self.pasta_origem = ""
        self.lbl_origem.config(text="Nenhuma selecionada")
        self.progresso["value"] = 0

    def mostrar_erro(self, erro):
        self.lbl_status.config(text="Erro na operação!")
        messagebox.showerror("Erro", f"Ocorreu um problema:\n{erro}")
        self.btn_mover.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = MovimentadorArquivos(root)
    root.mainloop()