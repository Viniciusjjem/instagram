import os
import hashlib
import json
import threading
import subprocess
import time
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

# Tratamento de erro na importação das bibliotecas externas para não fechar silenciosamente
try:
    import customtkinter as ctk
    from PIL import Image, ImageTk, UnidentifiedImageError
    import imagehash
    import send2trash
except ImportError as e:
    print(f"\n[ERRO FATAL] Uma biblioteca necessária não está instalada: {e}")
    print("Execute o comando: pip install customtkinter Pillow imagehash send2trash")
    sys.exit(1)

# --- Configurações Globais ---
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv'}
CACHE_FILE = 'dup_cache.json'

# --- Classes de Dados ---
class DuplicateGroup:
    def __init__(self, media_type, group_id, similarity):
        self.media_type = media_type
        self.group_id = group_id
        self.similarity = similarity
        self.files = []

class DuplicateFile:
    def __init__(self, path, size_bytes, hash_val, is_original=False):
        self.path = path
        self.size_bytes = size_bytes
        self.size_str = self._format_size(size_bytes)
        self.hash_val = hash_val
        self.is_original = is_original

    def _format_size(self, size_bytes):
        if size_bytes < 1024: return f"{size_bytes} B"
        elif size_bytes < 1024**2: return f"{size_bytes/1024:.2f} KB"
        elif size_bytes < 1024**3: return f"{size_bytes/1024**2:.2f} MB"
        else: return f"{size_bytes/1024**3:.2f} GB"

# --- Funções de Processamento ---
def calculate_hashes(directory, progress_callback):
    files_list = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in IMAGE_EXTENSIONS or ext in VIDEO_EXTENSIONS:
                files_list.append(os.path.join(root, file))
    
    num_files = len(files_list)
    cache = load_cache()
    new_hashes = {}
    found_groups = []
    
    image_hashes = {}
    video_hashes = {}

    start_time = time.time()

    for i, path in enumerate(files_list):
        progress_callback((i + 1) / max(1, num_files), f"Processando: {os.path.basename(path)}")
        try:
            stat = os.stat(path)
            size = stat.st_size
            mtime = stat.st_mtime
            file_ext = os.path.splitext(path)[1].lower()
            
            if path in cache and cache[path]['mtime'] == mtime:
                h = cache[path]['hash']
            else:
                if file_ext in IMAGE_EXTENSIONS:
                    h = str(imagehash.phash(Image.open(path)))
                elif file_ext in VIDEO_EXTENSIONS:
                    h = get_video_sample_hash(path)
                else:
                    h = None
                    
                cache[path] = {'mtime': mtime, 'hash': h}
            
            if h:
                if file_ext in IMAGE_EXTENSIONS:
                    if h not in image_hashes: image_hashes[h] = []
                    image_hashes[h].append((path, size, h))
                elif file_ext in VIDEO_EXTENSIONS:
                    if h not in video_hashes: video_hashes[h] = []
                    video_hashes[h].append((path, size, h))
        except Exception as e:
            print(f"Erro ao processar {path}: {e}")
            
    for h, files in image_hashes.items():
        if len(files) > 1:
            group = DuplicateGroup("image", h, "95%")
            original_idx = files.index(max(files, key=lambda x: x[1]))
            for i, (path, size, hash_val) in enumerate(files):
                group.files.append(DuplicateFile(path, size, hash_val, is_original=(i == original_idx)))
            found_groups.append(group)
            
    for h, files in video_hashes.items():
        if len(files) > 1:
            group = DuplicateGroup("video", h, "100%")
            original_idx = files.index(max(files, key=lambda x: x[1]))
            for i, (path, size, hash_val) in enumerate(files):
                group.files.append(DuplicateFile(path, size, hash_val, is_original=(i == original_idx)))
            found_groups.append(group)
            
    save_cache(cache)
    return found_groups, time.time() - start_time

def get_video_sample_hash(path):
    try:
        # Tenta usar ffprobe silenciando os erros de arquivos corrompidos (stderr=subprocess.DEVNULL)
        probe_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', path]
        duration_str = subprocess.check_output(probe_cmd, stderr=subprocess.DEVNULL).decode('utf-8').strip()
        
        if not duration_str or duration_str == 'N/A':
            raise ValueError("Duração inválida ou arquivo corrompido")
            
        duration = float(duration_str)
        samples = [duration * 0.25, duration * 0.50, duration * 0.75]
        combined_samples = b""
        
        for sample_time in samples:
            ffmpeg_cmd = ['ffmpeg', '-ss', str(sample_time), '-i', path, '-vf', 'scale=320:180', '-frames:v', '1', '-f', 'image2', 'pipe:1']
            sample_frame = subprocess.check_output(ffmpeg_cmd, stderr=subprocess.DEVNULL)
            combined_samples += sample_frame
            
        if not combined_samples:
            raise ValueError("Nenhum frame extraído")
            
        return hashlib.sha256(combined_samples).hexdigest()
        
    except Exception as e:
        # PLANO B (Fallback): Se o vídeo for inválido/corrompido para o FFmpeg, 
        # faz a leitura rápida do primeiro 1MB do arquivo bruto em vez de ignorá-lo.
        try:
            hasher = hashlib.sha256()
            with open(path, 'rb') as f:
                chunk = f.read(1024 * 1024) # Lê apenas o primeiro 1MB
                hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return None

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=4)

# --- Classe da Aplicação Principal ---
class DuplicateFinderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Localizador Pro de Duplicatas")
        self.geometry("1024x768")
        ctk.set_appearance_mode("dark")
        
        self.selected_directory = tk.StringVar(value="/home/user")
        self.scan_thread = None
        self.duplicate_groups = []
        self.file_vars = {}
        
        self._build_ui()
        
    def _build_ui(self):
        self.top_panel = ctk.CTkFrame(self)
        self.top_panel.pack(fill=tk.X, padx=10, pady=10)
        
        self.dir_label = ctk.CTkLabel(self.top_panel, text="Diretório Selecionado:", font=("Arial", 12))
        self.dir_label.pack(side=tk.LEFT, padx=10)
        
        self.dir_entry = ctk.CTkEntry(self.top_panel, textvariable=self.selected_directory, width=300)
        self.dir_entry.pack(side=tk.LEFT, padx=10)
        
        self.select_button = ctk.CTkButton(self.top_panel, text="Selecionar Diretório", command=self._select_directory)
        self.select_button.pack(side=tk.LEFT, padx=10)
        
        self.scan_button = ctk.CTkButton(self.top_panel, text="Iniciar Varredura", command=self._start_scan)
        self.scan_button.pack(side=tk.RIGHT, padx=10)
        
        self.results_frame = ctk.CTkScrollableFrame(self, label_text="Resultados (Revisão)")
        self.results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.bottom_panel = ctk.CTkFrame(self)
        self.bottom_panel.pack(fill=tk.X, padx=10, pady=10)
        
        self.status_label = ctk.CTkLabel(self.bottom_panel, text="Status: Aguardando varredura...", font=("Arial", 12))
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.progress_bar = ctk.CTkProgressBar(self.bottom_panel, width=400)
        self.progress_bar.set(0)
        self.progress_bar.pack(side=tk.LEFT, padx=10)
        
        self.action_button = ctk.CTkButton(self.bottom_panel, text="Excluir Selecionados (Lixeira)", fg_color="#d35400", command=self._delete_selected)
        self.action_button.pack(side=tk.RIGHT, padx=10)
        
    def _select_directory(self):
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.selected_directory.set(dir_path)
            
    def _start_scan(self):
        directory = self.selected_directory.get()
        if not directory or not os.path.isdir(directory):
            messagebox.showerror("Erro", "Por favor, selecione um diretório válido.")
            return
            
        self.status_label.configure(text="Iniciando varredura...")
        self.progress_bar.set(0)
        self._clear_results()
        
        self.scan_button.configure(state=tk.DISABLED)
        self.scan_thread = threading.Thread(target=self._scan_thread, args=(directory,), daemon=True)
        self.scan_thread.start()
        
    def _scan_thread(self, directory):
        def progress_callback(progress, status_text):
            self.progress_bar.set(progress)
            self.status_label.configure(text=f"Processando: {status_text}")
            
        groups, duration = calculate_hashes(directory, progress_callback)
        self.duplicate_groups = groups
        self.after(0, self._scan_completed, duration)
        
    def _scan_completed(self, duration):
        self.scan_button.configure(state=tk.NORMAL)
        self.status_label.configure(text=f"Varredura concluída em {duration:.2f}s. Encontrados {len(self.duplicate_groups)} grupos.")
        self.progress_bar.set(1)
        self._render_results()
        
    def _render_results(self):
        if not self.duplicate_groups:
            ctk.CTkLabel(self.results_frame, text="Nenhuma duplicata encontrada.", font=("Arial", 16)).pack(pady=20)
            return
            
        for group in self.duplicate_groups:
            group_frame = ctk.CTkFrame(self.results_frame, fg_color="#2b2b2b")
            group_frame.pack(fill=tk.X, padx=10, pady=10)
            
            group_title = f"Grupo: {os.path.basename(group.files[0].path)} (Similaridade: {group.similarity})"
            ctk.CTkLabel(group_frame, text=group_title, font=("Arial", 14, "bold")).pack(pady=5)
            
            group_content = ctk.CTkFrame(group_frame, fg_color="transparent")
            group_content.pack(fill=tk.X, expand=True, padx=5, pady=5)
            
            preview_panel = ctk.CTkFrame(group_content, width=350, height=200, fg_color="#1e1e1e")
            preview_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
            preview_panel.pack_propagate(False)
            
            if group.media_type == "image":
                preview_label = ctk.CTkLabel(preview_panel, text="Carregando visualização...")
                preview_label.pack(fill=tk.BOTH, expand=True)
                threading.Thread(target=self._load_group_preview, args=(group, preview_label), daemon=True).start()
            elif group.media_type == "video":
                ctk.CTkLabel(preview_panel, text="[ Vídeo: Reprodução Simulada ]").pack(expand=True)
            
            file_list_panel = ctk.CTkFrame(group_content, fg_color="transparent")
            file_list_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            for file_info in group.files:
                file_item = ctk.CTkFrame(file_list_panel, fg_color="transparent")
                file_item.pack(fill=tk.X, pady=2)
                
                var = tk.BooleanVar(value=not file_info.is_original)
                self.file_vars[file_info.path] = var
                ctk.CTkCheckBox(file_item, text="", variable=var, width=15).pack(side=tk.LEFT, padx=5)
                
                icon_text = "Visto" if file_info.is_original else "Cópia"
                icon_color = "#3498db" if file_info.is_original else "#e67e22"
                ctk.CTkLabel(file_item, text=icon_text, text_color=icon_color, font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
                
                filename = os.path.basename(file_info.path)
                short_path = file_info.path if len(file_info.path) < 60 else file_info.path[:30] + "..." + file_info.path[-27:]
                ctk.CTkLabel(file_item, text=f"{short_path} ({file_info.size_str})", font=("Arial", 10)).pack(side=tk.LEFT, padx=10)

    def _load_group_preview(self, group, label):
        try:
            path = group.files[0].path
            img = Image.open(path)
            img.thumbnail((320, 180))
            photo = ImageTk.PhotoImage(img)
            self.after(0, self._update_image_preview, label, photo)
        except Exception:
            self.after(0, lambda: label.configure(text="Falha no preview"))
            
    def _update_image_preview(self, label, photo):
        label.configure(image=photo, text="")
        label.image = photo
        
    def _clear_results(self):
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        self.file_vars = {}
        self.duplicate_groups = []
        
    def _delete_selected(self):
        paths_to_delete = [path for path, var in self.file_vars.items() if var.get()]
        if not paths_to_delete: return
            
        if messagebox.askyesno("Confirmar Exclusão", f"Mover {len(paths_to_delete)} arquivos para a lixeira?"):
            num_deleted = 0
            for path in paths_to_delete:
                try:
                    send2trash.send2trash(path)
                    num_deleted += 1
                except Exception as e:
                    print(f"Erro ao excluir {path}: {e}")
            messagebox.showinfo("Sucesso", f"{num_deleted} arquivos movidos para a lixeira!")
            self._start_scan()

if __name__ == "__main__":
    try:
        app = DuplicateFinderApp()
        app.mainloop()
    except Exception as e:
        print(f"\n[ERRO DE INICIALIZAÇÃO] A interface gráfica falhou ao iniciar: {e}")
        print("Se o erro mencionar 'tkinter' ou '_tkinter', abra o terminal do Pop!_OS e instale o pacote de sistema:")
        print("-> sudo apt update && sudo apt install python3-tk")