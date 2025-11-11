# views/admin_view.py
# (Versão 7.0 - Usa o cliente 'supabase' normal, confiando no RLS V13)

import flet as ft
# Importamos AMBOS os clientes
from supabase_client import supabase, supabase_admin
from supabase_auth.errors import AuthApiError

class AdminView(ft.Column):
    """
    Representa o conteúdo da aba Administração.
    Versão 7.0: Usa o cliente 'supabase' (não-admin) para ler,
    confiando na política RLS "Admins podem LER TODOS os perfis".
    """
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.alignment = ft.MainAxisAlignment.START
        self.spacing = 20
        self.padding = 20
        
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
            # --- CORREÇÃO (V7): Usando o cliente 'supabase' (não-admin) ---
            # A nossa política SQL V13 "Admins podem LER TODOS os perfis"
            # permite que esta chamada funcione para admins.
            
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
            self.show_snackbar(f"Erro ao carregar utilizadores: {ex}")
        
        self.progress_ring.visible = False
        self.update()

    def open_add_modal(self, e):
        """(Ainda não implementado)"""
        self.show_snackbar("Função 'Adicionar' ainda não implementada.", "orange")

    def show_snackbar(self, message, color="red"):
        """Mostra uma mensagem de feedback."""
        self.page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor=color)
        self.page.snack_bar.open = True
        self.page.update()

# --- Função de Nível Superior (Obrigatória) ---
def create_admin_view(page: ft.Page):
    """
    Exporta a nossa AdminView como um controlo Flet padrão.
    """
    return AdminView(page)