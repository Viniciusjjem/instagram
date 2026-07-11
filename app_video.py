import customtkinter as ctk
from tkinter import filedialog, StringVar
import subprocess
import threading
import os
import shutil
import json

# Configuração visual do CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class VideoConverterApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("VideoTool Pro - Ultimate Edition")
        self.geometry("800x680")
        self.resizable(False, False)

        self.tabview = ctk.CTkTabview(self, width=760, height=640)
        self.tabview.pack(padx=20, pady=20)

        self.tab_convert = self.tabview.add("Conversor de Vídeo")
        self.tab_enhance = self.tabview.add("Melhoria de Qualidade Pro")
        self.tab_scan = self.tabview.add("Filtro de Lote (Scan)") # NOVA ABA

        self.build_convert_tab()
        self.build_enhance_tab()
        self.build_scan_tab()

    # ==========================================
    # ABA 1: CONVERSOR SIMPLES
    # ==========================================
    def build_convert_tab(self):
        self.file_path_conv = StringVar(value="Nenhum arquivo selecionado")

        ctk.CTkLabel(self.tab_convert, text="1. Selecione o vídeo de origem:", font=("Arial", 15, "bold")).pack(pady=(15, 5))
        ctk.CTkButton(self.tab_convert, text="Procurar Arquivo", command=lambda: self.select_file(self.file_path_conv)).pack(pady=5)
        ctk.CTkLabel(self.tab_convert, textvariable=self.file_path_conv, text_color="gray").pack(pady=(0, 15))

        ctk.CTkLabel(self.tab_convert, text="2. Formato de saída:", font=("Arial", 15, "bold")).pack(pady=(5, 5))
        self.format_combobox = ctk.CTkComboBox(self.tab_convert, values=[".mp4", ".mkv", ".avi", ".mov", ".webm"])
        self.format_combobox.pack(pady=5)

        ctk.CTkLabel(self.tab_convert, text="3. Aceleração por Hardware (GPU):", font=("Arial", 15, "bold")).pack(pady=(15, 5))
        self.gpu_combobox_conv = ctk.CTkComboBox(self.tab_convert, values=["Desativado (CPU)", "NVIDIA (NVENC)", "Intel/AMD (VAAPI)"])
        self.gpu_combobox_conv.pack(pady=5)

        self.status_label_conv = ctk.CTkLabel(self.tab_convert, text="", font=("Arial", 14))
        self.status_label_conv.pack(pady=15)

        ctk.CTkButton(self.tab_convert, text="Iniciar Conversão", fg_color="green", hover_color="darkgreen", 
                      command=self.start_conversion_thread).pack(side="bottom", pady=15)

    # ==========================================
    # ABA 2: MELHORIA DE QUALIDADE
    # ==========================================
    def build_enhance_tab(self):
        self.file_path_enh = StringVar(value="Nenhum arquivo selecionado")

        ctk.CTkLabel(self.tab_enhance, text="1. Selecione o vídeo para tratamento:", font=("Arial", 15, "bold")).pack(pady=(15, 5))
        ctk.CTkButton(self.tab_enhance, text="Procurar Arquivo", command=lambda: self.select_file(self.file_path_enh)).pack(pady=5)
        ctk.CTkLabel(self.tab_enhance, textvariable=self.file_path_enh, text_color="gray").pack(pady=(0, 15))

        ctk.CTkLabel(self.tab_enhance, text="2. Configurações de Resolução:", font=("Arial", 15, "bold")).pack(pady=(5, 5))
        self.resolution_combobox = ctk.CTkComboBox(
            self.tab_enhance, 
            values=["Manter Original", "1080p (Full HD)", "1440p (2K)", "2160p (4K)", "4320p (8K)"],
            width=200
        )
        self.resolution_combobox.pack(pady=5)

        self.clean_var = ctk.StringVar(value="off")
        ctk.CTkCheckBox(self.tab_enhance, text="Otimizar Nitidez e Remover Ruído/Granulação", variable=self.clean_var, onvalue="on", offvalue="off").pack(pady=10)

        ctk.CTkLabel(self.tab_enhance, text="3. Processador de Renderização:", font=("Arial", 15, "bold")).pack(pady=(15, 5))
        self.gpu_combobox_enh = ctk.CTkComboBox(self.tab_enhance, values=["Desativado (CPU)", "NVIDIA (NVENC)", "Intel/AMD (VAAPI)"])
        self.gpu_combobox_enh.pack(pady=5)

        self.status_label_enh = ctk.CTkLabel(self.tab_enhance, text="", font=("Arial", 14))
        self.status_label_enh.pack(pady=10)

        ctk.CTkButton(self.tab_enhance, text="Aplicar Filtros", fg_color="purple", hover_color="darkmagenta", 
                      command=self.start_enhance_thread).pack(side="bottom", pady=15)

    # ==========================================
    # ABA 3: FILTRO DE LOTE (SCANNER)
    # ==========================================
    def build_scan_tab(self):
        self.dir_source = StringVar(value="Nenhuma pasta de origem selecionada")
        self.dir_dest = StringVar(value="Nenhuma pasta de destino selecionada")

        # Seleção de Pastas
        ctk.CTkLabel(self.tab_scan, text="1. Pastas de Trabalho:", font=("Arial", 15, "bold")).pack(pady=(10, 5))
        
        frame_dirs = ctk.CTkFrame(self.tab_scan, fg_color="transparent")
        frame_dirs.pack(pady=5, fill="x", padx=20)
        
        ctk.CTkButton(frame_dirs, text="Pasta Origem (Onde estão os vídeos)", command=lambda: self.select_directory(self.dir_source)).pack(pady=2)
        ctk.CTkLabel(frame_dirs, textvariable=self.dir_source, text_color="gray", font=("Arial", 12)).pack(pady=(0, 10))
        
        ctk.CTkButton(frame_dirs, text="Pasta Destino (Para onde enviar)", command=lambda: self.select_directory(self.dir_dest)).pack(pady=2)
        ctk.CTkLabel(frame_dirs, textvariable=self.dir_dest, text_color="gray", font=("Arial", 12)).pack(pady=(0, 10))

        # Critério de Qualidade
        ctk.CTkLabel(self.tab_scan, text="2. O que é 'Baixa Qualidade' para você?", font=("Arial", 15, "bold")).pack(pady=(10, 5))
        self.threshold_combobox = ctk.CTkComboBox(
            self.tab_scan, 
            values=["Menor que 720p (HD)", "Menor que 1080p (Full HD)", "Menor que 1440p (2K)", "Menor que 4K"],
            width=250
        )
        self.threshold_combobox.pack(pady=5)

        # Log de Atividade
        ctk.CTkLabel(self.tab_scan, text="Progresso:", font=("Arial", 12, "bold")).pack(pady=(10, 0))
        self.log_box = ctk.CTkTextbox(self.tab_scan, width=600, height=150, state="disabled")
        self.log_box.pack(pady=5)

        self.status_label_scan = ctk.CTkLabel(self.tab_scan, text="", font=("Arial", 14))
        self.status_label_scan.pack(pady=5)

        ctk.CTkButton(self.tab_scan, text="Iniciar Varredura", fg_color="#b8860b", hover_color="#8b6508", 
                      command=self.start_scan_thread).pack(side="bottom", pady=10)

    # ==========================================
    # FUNÇÕES DE APOIO E LÓGICA
    # ==========================================
    def select_file(self, string_var):
        filepath = filedialog.askopenfilename(title="Selecione um vídeo")
        if filepath: string_var.set(filepath)

    def select_directory(self, string_var):
        dirpath = filedialog.askdirectory(title="Selecione uma pasta")
        if dirpath: string_var.set(dirpath)

    def log_message(self, message):
        """Escreve mensagens na caixa de texto da aba Scan"""
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def get_video_resolution(self, filepath):
        """Usa o ffprobe para ler a altura (height) do vídeo silenciosamente"""
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=height", "-of", "json", filepath
        ]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            info = json.loads(result.stdout)
            if 'streams' in info and len(info['streams']) > 0:
                return int(info['streams'][0]['height'])
        except Exception:
            return None
        return None

    def get_gpu_args(self, selection):
        if selection == "NVIDIA (NVENC)": return ["-c:v", "h264_nvenc"]
        elif selection == "Intel/AMD (VAAPI)": return ["-c:v", "h264_vaapi"]
        return ["-c:v", "libx264"]

    def run_ffmpeg_command(self, command, status_label):
        try:
            status_label.configure(text="Processando... Aguarde.", text_color="yellow")
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            status_label.configure(text="Concluído com sucesso!", text_color="green")
        except subprocess.CalledProcessError:
            status_label.configure(text="Erro de codificação/GPU.", text_color="red")
        except FileNotFoundError:
            status_label.configure(text="Erro: FFmpeg não encontrado.", text_color="red")

    # ==========================================
    # THREADS (AÇÕES EM SEGUNDO PLANO)
    # ==========================================
    def start_conversion_thread(self):
        input_file = self.file_path_conv.get()
        if not os.path.isfile(input_file): return
        target_ext = self.format_combobox.get()
        output_file = f"{os.path.splitext(input_file)[0]}_convertido{target_ext}"
        
        gpu_choice = self.gpu_combobox_conv.get()
        command = ["ffmpeg", "-y"]
        if gpu_choice == "Intel/AMD (VAAPI)": command.extend(["-vaapi_device", "/dev/dri/renderD128"])
        command.extend(["-i", input_file])
        command.extend(self.get_gpu_args(gpu_choice))
        command.append(output_file)
        
        threading.Thread(target=self.run_ffmpeg_command, args=(command, self.status_label_conv), daemon=True).start()

    def start_enhance_thread(self):
        input_file = self.file_path_enh.get()
        if not os.path.isfile(input_file): return
        output_file = f"{os.path.splitext(input_file)[0]}_masterizado{os.path.splitext(input_file)[1]}"

        gpu_choice = self.gpu_combobox_enh.get()
        command = ["ffmpeg", "-y"]
        if gpu_choice == "Intel/AMD (VAAPI)": command.extend(["-vaapi_device", "/dev/dri/renderD128"])
        command.extend(["-i", input_file])
        
        video_filters = []
        res_choice = self.resolution_combobox.get()
        if res_choice != "Manter Original":
            res_map = {"1080p (Full HD)": ("1920", "1080"), "1440p (2K)": ("2560", "1440"), "2160p (4K)": ("3840", "2160"), "4320p (8K)": ("7680", "4320")}
            w, h = res_map[res_choice]
            video_filters.append(f"scale={w}:{h}:flags=lanczos:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2")
            
        if self.clean_var.get() == "on":
            video_filters.extend(["hqdn3d", "unsharp=5:5:0.7:5:5:0.0"])
            
        if video_filters: command.extend(["-vf", ",".join(video_filters)])

        if gpu_choice == "Desativado (CPU)": command.extend(["-c:v", "libx264", "-crf", "18", "-preset", "slow", "-c:a", "copy"])
        elif gpu_choice == "NVIDIA (NVENC)": command.extend(["-c:v", "h264_nvenc", "-cq", "19", "-preset", "slow", "-c:a", "copy"])
        elif gpu_choice == "Intel/AMD (VAAPI)":
            if video_filters:
                command.pop(-1) 
                command.extend(["-vf", ",".join(video_filters) + ",format=nv12,hwupload"])
            command.extend(["-c:v", "h264_vaapi", "-qp", "19", "-c:a", "copy"])

        command.append(output_file)
        threading.Thread(target=self.run_ffmpeg_command, args=(command, self.status_label_enh), daemon=True).start()

    def start_scan_thread(self):
        source = self.dir_source.get()
        dest = self.dir_dest.get()
        
        if not os.path.isdir(source) or not os.path.isdir(dest):
            self.status_label_scan.configure(text="Selecione pastas válidas!", text_color="red")
            return
            
        threshold_map = {
            "Menor que 720p (HD)": 720,
            "Menor que 1080p (Full HD)": 1080,
            "Menor que 1440p (2K)": 1440,
            "Menor que 4K": 2160
        }
        max_height = threshold_map[self.threshold_combobox.get()]

        self.status_label_scan.configure(text="Analisando pasta...", text_color="yellow")
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

        threading.Thread(target=self.run_scan_process, args=(source, dest, max_height), daemon=True).start()

    def run_scan_process(self, source, dest, max_height):
        extensoes_suportadas = ('.mp4', '.mkv', '.avi', '.mov', '.webm')
        arquivos_movidos = 0

        for filename in os.listdir(source):
            if filename.lower().endswith(extensoes_suportadas):
                filepath = os.path.join(source, filename)
                
                # Lê a resolução
                height = self.get_video_resolution(filepath)
                
                if height is not None:
                    if height < max_height:
                        self.log_message(f"Baixa Qualidade detectada ({height}p): {filename}")
                        
                        # Copia o arquivo para a pasta de destino (estou usando copy2 para não deletar seu arquivo original sem querer)
                        dest_path = os.path.join(dest, filename)
                        shutil.copy2(filepath, dest_path)
                        self.log_message(f"-> Arquivo copiado para o destino.\n")
                        arquivos_movidos += 1
                    else:
                        self.log_message(f"Ignorado (Qualidade OK - {height}p): {filename}\n")
                else:
                    self.log_message(f"Erro ao ler metadados: {filename}\n")

        msg_final = f"Varredura concluída! {arquivos_movidos} arquivos separados."
        self.log_message(msg_final)
        self.status_label_scan.configure(text=msg_final, text_color="green")

if __name__ == "__main__":
    app = VideoConverterApp()
    app.mainloop()