# launcher.py
# (Versão 1.0 - Lote 6: Implementa Auto-Updater)

import os
import sys
import json
import requests
import subprocess
import shutil
import threading
import tkinter as tk
from tkinter import ttk, messagebox

# --- CONFIGURAÇÃO ---
# (Obrigatório) Cole aqui o URL "Raw" do seu Gist 'versao.json'
GIST_URL = "https://gist.githubusercontent.com/sgt-lucas/5eeb81023db3b85957f179eb4889f67d/raw/a393359c5c57d5c6b09eda7fdff3d32618bbc9a4/gistfile1.txt" 
# --------------------

# Define os caminhos com base na localização do launcher.exe
if getattr(sys, 'frozen', False):
    # Estamos a correr num .exe compilado
    APP_DIR = os.path.dirname(sys.executable)
else:
    # Estamos a correr num script .py
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

MAIN_APP_EXE = os.path.join(APP_DIR, "main.exe")
VERSION_FILE = os.path.join(APP_DIR, "local_version.json")
TEMP_EXE = os.path.join(APP_DIR, "main_new.exe")


class UpdateLauncher(tk.Tk):
    """
    Interface gráfica simples (Tkinter) para o atualizador.
    Mostra o progresso e não deixa o utilizador a olhar para o vazio.
    """
    def __init__(self):
        super().__init__()
        self.title("Gestor NC - Atualizador")
        self.geometry("350x100")
        self.resizable(False, False)
        
        # Centra a janela
        self.withdraw() # Esconde a janela por agora
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_reqwidth()) / 2
        y = (self.winfo_screenheight() - self.winfo_reqheight()) / 2
        self.geometry(f"+{int(x)}+{int(y)}")
        self.deiconify() # Mostra a janela na posição correta

        self.label_status = ttk.Label(self, text="A verificar atualizações...", font=("Helvetica", 10))
        self.label_status.pack(pady=10, padx=20)
        
        self.progress_bar = ttk.Progressbar(self, mode='indeterminate', length=300)
        self.progress_bar.pack(pady=10)
        self.progress_bar.start(10)
        
        # Inicia a verificação numa thread separada para não congelar a UI
        self.check_thread = threading.Thread(target=self.iniciar_verificacao, daemon=True)
        self.check_thread.start()

    def get_local_version(self):
        """Lê a versão guardada localmente."""
        try:
            with open(VERSION_FILE, 'r') as f:
                data = json.load(f)
                return data.get("versao", "0.0.0")
        except FileNotFoundError:
            return "0.0.0" # Versão inicial se o ficheiro não existir

    def set_local_version(self, versao):
        """Guarda a nova versão localmente após a atualização."""
        try:
            with open(VERSION_FILE, 'w') as f:
                json.dump({"versao": versao}, f)
        except Exception as e:
            print(f"Erro ao guardar versão local: {e}")

    def iniciar_aplicacao(self):
        """Inicia o main.exe e fecha o launcher."""
        if not os.path.exists(MAIN_APP_EXE):
            self.label_status.config(text="Erro!")
            messagebox.showerror("Erro", f"Ficheiro principal 'main.exe' não encontrado!\nPor favor, reinstale a aplicação.")
            self.destroy()
            return
            
        try:
            self.label_status.config(text="A iniciar aplicação...")
            subprocess.Popen([MAIN_APP_EXE]) # Inicia o processo principal
            self.destroy() # Fecha o launcher
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível iniciar a aplicação: {e}")
            self.destroy()

    def baixar_e_substituir(self, url, nova_versao):
        """Baixa o novo .exe e substitui o antigo."""
        try:
            self.label_status.config(text=f"A baixar nova versão {nova_versao}...")
            self.progress_bar.stop()
            self.progress_bar.config(mode='determinate', maximum=100, value=0)

            # 1. Baixar para um ficheiro temporário
            r = requests.get(url, stream=True)
            r.raise_for_status()
            
            total_size = int(r.headers.get('content-length', 0))
            bytes_baixados = 0
            
            with open(TEMP_EXE, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    bytes_baixados += len(chunk)
                    if total_size > 0:
                        progresso = (bytes_baixados / total_size) * 100
                        self.progress_bar['value'] = progresso
                        self.update_idletasks()

            # 2. Substituir o ficheiro antigo
            self.label_status.config(text="A instalar atualização...")
            self.progress_bar.config(mode='indeterminate')
            self.progress_bar.start(10)
            
            # Tenta substituir. Se 'main.exe' estiver em uso, falhará.
            shutil.move(TEMP_EXE, MAIN_APP_EXE) 
            
            # 3. Guardar a nova versão
            self.set_local_version(nova_versao)
            
            self.label_status.config(text="Atualização concluída!")
            self.iniciar_aplicacao()

        except requests.exceptions.RequestException as e:
            messagebox.showerror("Erro de Download", f"Falha ao baixar a atualização: {e}\nA iniciar a versão local.")
            if os.path.exists(TEMP_EXE): os.remove(TEMP_EXE) # Limpa
            self.iniciar_aplicacao()
        except OSError as e:
            messagebox.showerror("Erro de Instalação", f"Falha ao instalar a atualização (o ficheiro 'main.exe' pode estar em uso): {e}\nA iniciar a versão local.")
            if os.path.exists(TEMP_EXE): os.remove(TEMP_EXE) # Limpa
            self.iniciar_aplicacao()
        except Exception as e:
            messagebox.showerror("Erro Inesperado", f"Ocorreu um erro: {e}\nA iniciar a versão local.")
            if os.path.exists(TEMP_EXE): os.remove(TEMP_EXE) # Limpa
            self.iniciar_aplicacao()


    def iniciar_verificacao(self):
        """Lógica principal de verificação (corre em thread)."""
        if GIST_URL == "URL_RAW_DO_SEU_GIST_AQUI":
            messagebox.showwarning("Configuração", "O Launcher não está configurado.\nA iniciar a aplicação local.")
            self.iniciar_aplicacao()
            return

        try:
            versao_local = self.get_local_version()
            
            # 1. Tentar obter a versão remota
            r = requests.get(GIST_URL, timeout=5) # Timeout de 5s
            r.raise_for_status()
            dados_remotos = r.json()
            versao_remota = dados_remotos["versao"]
            
            # 2. Comparar
            if versao_local == versao_remota:
                # Versões iguais, iniciar app
                self.iniciar_aplicacao()
            else:
                # Versão nova encontrada, iniciar download
                self.baixar_e_substituir(dados_remotos["url_download"], versao_remota)
                
        except requests.exceptions.RequestException:
            # Falha de rede (sem internet, Gist offline, etc.)
            print("Falha de rede. A iniciar aplicação local.")
            self.iniciar_aplicacao()
        except Exception as e:
            print(f"Erro inesperado no launcher: {e}")
            self.iniciar_aplicacao() # Falha segura

# --- Ponto de Entrada ---
if __name__ == "__main__":
    if not os.path.exists(MAIN_APP_EXE):
        messagebox.showerror("Ficheiro não encontrado", f"O ficheiro 'main.exe' não foi encontrado nesta pasta.\nO launcher não pode funcionar.")
    else:
        app = UpdateLauncher()
        app.mainloop()