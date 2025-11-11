# views/admin_view.py
# (Versão 8.0 - Lote 3 Revisado: Implementa ErrorModal)

import flet as ft
# Importamos AMBOS os clientes
from supabase_client import supabase, supabase_admin
from supabase_auth.errors import AuthApiError

class AdminView(ft.Column):
    """
    Representa o conteúdo da aba Administração.
    Versão 8.0 (Lote 3 Revisado):
    - (Item 11) Substitui show_snackbar (para erros) pelo novo self.error_modal.
    - (Item 11 / Erro #4) Adiciona 'handle_db_error' para traduzir erros.
    """
    
    # (LOTE 3, Item 11) - Aceita o error_modal
    def __init__(self, page, error_modal=None):
        super().__init__()
        self.page = page
        self.alignment = ft.MainAxisAlignment.START
        self.spacing = 20
        self.padding = 20
        self.error_modal = error_modal # (LOTE 3)
        
        self.progress_ring = ft.ProgressRing(visible=True, width=32, height=32)
        
        self.tabela_users = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID do Utilizador (UUID)", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Nome Completo", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Função", weight=ft.FontWeight.BOLD)), #
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
                on_click=self.open_add_modal # (Ainda não implementado)
            ),
            ft.Divider(),
            ft.Container(
                content=self.tabela_users,
                expand=True
            )
        ]

        # Carrega os dados assim que a vista é criada
        self.load_users()

    def load_users_wrapper(self, e):
        """Wrapper para o botão de refresh."""
        self.load_users()

    def load_users(self):
        """
        Busca TODOS os perfis da tabela 'perfis_usuarios'.
        (V7 - Usa o cliente 'supabase' normal, confiando no RLS)
        """
        print("AdminView: A carregar lista de utilizadores (Modo RLS)...")
        self.progress_ring.visible = True
        self.update()
        
        try:
            resposta_perfis = supabase.table('perfis_usuarios').select('*').execute()
            
            self.tabela_users.rows.clear()
            
            if resposta_perfis.data:
                for profile in resposta_perfis.data:
                    user_id = profile.get('id_usuario') #

                    self.tabela_users.rows.append(
                        ft.DataRow(
                            data=user_id, # Guarda o UUID
                            cells=[
                                ft.DataCell(ft.Text(user_id)), 
                                ft.DataCell(ft.Text(profile.get('nome_completo', '---'))), 
                                ft.DataCell(ft.Text(profile.get('funcao', 'N/A'))), #
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
            
            print("AdminView: Utilizadores carregados com sucesso (Modo RLS).")

        except Exception as ex:
            print(f"Erro CRÍTICO ao carregar perfis: {ex}") 
            import traceback
            traceback.print_exc()
            # (LOTE 3, Erro #4) - Usa o tradutor de erros
            self.handle_db_error(ex, "carregar utilizadores")
        
        self.progress_ring.visible = False
        self.update()

    def open_add_modal(self, e):
        """(Ainda não implementado)"""
        # (LOTE 3) - Mantém o snackbar laranja para AVISOS
        self.show_snackbar("Função 'Adicionar' ainda não implementada.", "orange")

    # (LOTE 3, Item 11) - Função de conveniência para mostrar erro
    def show_error(self, message):
        """Exibe o modal de erro global."""
        if self.error_modal:
            self.error_modal.show(message)
        else:
            print(f"ERRO CRÍTICO (Modal não encontrado): {message}")
            
    # (LOTE 3, Erro #4) - Função para traduzir erros de DB
    def handle_db_error(self, ex, context=""):
        """Traduz erros comuns do Supabase/PostgREST para mensagens amigáveis."""
        msg = str(ex)
        print(f"Erro de DB Bruto ({context}): {msg}") # Manter no log
        
        if "fetch failed" in msg or "Connection refused" in msg:
            self.show_error("Erro de Rede: Não foi possível conectar ao banco de dados. Verifique sua internet.")
        else:
            self.show_error(f"Erro inesperado ao {context}: {msg}")

    def show_snackbar(self, message, color="red"):
        """Mostra uma mensagem de feedback (Usado apenas para AVISOS)."""
        self.page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor=color)
        self.page.snack_bar.open = True
        self.page.update()

# --- Função de Nível Superior (Obrigatória) ---
# (LOTE 3, Item 11) - Aceita o error_modal
def create_admin_view(page: ft.Page, error_modal=None):
    """
    Exporta a nossa AdminView como um controlo Flet padrão.
    """
    return AdminView(page, error_modal=error_modal)