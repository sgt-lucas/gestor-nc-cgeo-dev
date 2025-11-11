# views/admin_view.py
# (Versão 8.2 - Lote 5: Corrige "Tela Branca" / "AssertionError")

import flet as ft
# Importamos AMBOS os clientes
from supabase_client import supabase, supabase_admin
from supabase_auth.errors import AuthApiError

class AdminView(ft.Column):
    """
    Representa o conteúdo da aba Administração.
    Versão 8.2 (Lote 5):
    - (BUGFIX) Corrige "Tela Branca" (AssertionError) ao logar como admin.
    - 'load_users()' agora é chamado pelo 'on_mount' em vez do '__init__',
      garantindo que o controlo exista na página antes de 'update()'.
    """
    
    def __init__(self, page, error_modal=None):
        super().__init__()
        self.page = page
        self.alignment = ft.MainAxisAlignment.START
        self.spacing = 20
        self.padding = 20
        self.error_modal = error_modal
        
        self.progress_ring = ft.ProgressRing(visible=True, width=32, height=32)
        
        self.tabela_users = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID do Utilizador (UUID)", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Nome Completo", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Função", weight=ft.FontWeight.BOLD)), 
                ft.DataColumn(ft.Text("Ações", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            expand=True,
            border=ft.border.all(1, "grey200"),
            border_radius=8,
        )
        
        self.controls = [
            ft.Row(
                [
                    ft.Text("Gestão de Utilizadores", size=20, weight=ft.FontWeight.W_600),
                    ft.Row([
                        ft.IconButton(icon="REFRESH", on_click=self.load_users_wrapper, tooltip="Recarregar Lista"),
                        self.progress_ring,
                    ])
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            ft.ElevatedButton(
                "Adicionar Novo Utilizador", 
                icon="ADD", 
                on_click=self.open_add_modal
            ),
            ft.Divider(),
            ft.Container(
                content=self.tabela_users,
                expand=True
            )
        ]

        # --- (CORREÇÃO LOTE 5.2) ---
        # 1. Removemos o 'load_users()' daqui
        # self.load_users() 
        
        # 2. Adicionamos o evento 'on_mount'
        self.on_mount = self.on_view_mount
        # --- FIM DA CORREÇÃO ---

    # --- (NOVA FUNÇÃO LOTE 5.2) ---
    def on_view_mount(self, e):
        """Chamado pelo Flet DEPOIS que o controlo é adicionado à página."""
        print("AdminView: Controlo montado. A carregar utilizadores...")
        self.load_users()

    def load_users_wrapper(self, e):
        """Wrapper para o botão de refresh."""
        self.load_users()

    def load_users(self):
        """
        Busca TODOS os perfis da tabela 'perfis_usuarios'.
        (V8.1 - Usa supabase_admin para ignorar RLS)
        """
        print("AdminView: A carregar lista de utilizadores (Modo Admin)...")
        self.progress_ring.visible = True
        
        # (CORREÇÃO LOTE 5.2) - Chamada de 'update()'
        # Agora é seguro chamar 'update()' porque 'load_users' 
        # só é chamado 'on_mount'.
        self.update() 
        
        try:
            resposta_perfis = supabase_admin.table('perfis_usuarios').select('*').execute()
            
            self.tabela_users.rows.clear()
            
            if resposta_perfis.data:
                for profile in resposta_perfis.data:
                    user_id = profile.get('id_usuario') 

                    self.tabela_users.rows.append(
                        ft.DataRow(
                            data=user_id, # Guarda o UUID
                            cells=[
                                ft.DataCell(ft.Text(user_id)), 
                                ft.DataCell(ft.Text(profile.get('nome_completo', '---'))), 
                                ft.DataCell(ft.Text(profile.get('funcao', 'N/A'))), 
                                ft.DataCell(
                                    ft.Row([
                                        ft.IconButton(icon="EDIT", tooltip="Editar Função", icon_color="blue700"),
                                        ft.IconButton(icon="DELETE", tooltip="Excluir Utilizador", icon_color="red700"),
                                    ])
                                ),
                            ]
                        )
                    )
            else:
                self.tabela_users.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text("Nenhum perfil de utilizador encontrado.", italic=True)),
                        ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")),
                    ])
                )
            
            print("AdminView: Utilizadores carregados com sucesso (Modo Admin).")

        except Exception as ex:
            print(f"Erro CRÍTICO ao carregar perfis: {ex}") 
            import traceback
            traceback.print_exc()
            self.handle_db_error(ex, "carregar utilizadores")
        
        self.progress_ring.visible = False
        self.update()

    def open_add_modal(self, e):
        """(Ainda não implementado)"""
        self.show_snackbar("Função 'Adicionar' ainda não implementada.", "orange")

    def show_error(self, message):
        """Exibe o modal de erro global."""
        if self.error_modal:
            self.error_modal.show(message)
        else:
            print(f"ERRO CRÍTICO (Modal não encontrado): {message}")
            
    def handle_db_error(self, ex, context=""):
        """Traduz erros comuns do Supabase/PostgREST para mensagens amigáveis."""
        msg = str(ex)
        print(f"Erro de DB Bruto ({context}): {msg}") # Manter no log
        
        if "fetch failed" in msg or "Connection refused" in msg:
            self.show_error("Erro de Rede: Não foi possível conectar ao banco de dados. Verifique sua internet.")
        # (NOVO) - Captura o erro de chave de API inválida
        elif "Invalid API key" in msg or "invalid JWT" in msg:
             self.show_error("Erro de Autenticação de Admin: A Chave de Serviço (service_role) está incorreta. Verifique o ficheiro supabase_client.py.")
        else:
            self.show_error(f"Erro inesperado ao {context}: {msg}")

    def show_snackbar(self, message, color="red"):
        """Mostra uma mensagem de feedback (Usado apenas para AVISOS)."""
        self.page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor=color)
        self.page.snack_bar.open = True
        self.page.update()

# --- Função de Nível Superior (Obrigatória) ---
def create_admin_view(page: ft.Page, error_modal=None):
    """
    Exporta a nossa AdminView como um controlo Flet padrão.
    """
    return AdminView(page, error_modal=error_modal)