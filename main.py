# main.py
# (Versão corrigida, V7 - Sem Dev Mode, ícones corretos, login @salc.com)

import flet as ft
# Importa AMBOS os clientes
from supabase_client import supabase, supabase_admin 
# Importação correta da biblioteca de auth
from supabase_auth.errors import AuthApiError 

# Importa as nossas "views" (abas)
from views.dashboard_view import create_dashboard_view
from views.ncs_view import create_ncs_view
from views.nes_view import create_nes_view
from views.relatorios_view import create_relatorios_view
from views.admin_view import create_admin_view

def main(page: ft.Page):
    
    page.title = "SISTEMA DE CONTROLE DE NOTAS DE CRÉDITO - SALC" 
    
    # --- DEV MODE REMOVIDO ---
    
    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary="green800",
            primary_container="green900",
            background="grey100",
            surface="white",
        )
    )

    # --- Campos de Login (Plano B) ---
    username_field = ft.TextField(
        label="Utilizador", 
        prefix_icon="PERSON", # Ícone como string
        width=350,
        hint_text="ex: joao.silva",
        autofocus=True,
        on_submit=lambda e: handle_login(e) 
    )
    password_field = ft.TextField(
        label="Senha", 
        prefix_icon="LOCK", # Ícone como string
        width=350,
        password=True, 
        can_reveal_password=True,
        on_submit=lambda e: handle_login(e) 
    )

    def show_main_layout(e=None):
        """ 
        Constrói a interface principal da aplicação (Abas) após o login.
        """
        page.clean() 
        page.vertical_alignment = ft.MainAxisAlignment.START 

        page.appbar = ft.AppBar(
            title=ft.Text("SALC - Sistema de Controle de Notas de Crédito"), 
            bgcolor="green800",
            color="white",
            actions=[
                ft.Text(f"Utilizador: {page.session.get('user_email')}"),
                ft.IconButton(
                    icon="LOGOUT", # Ícone como string
                    tooltip="Sair",
                    on_click=handle_logout,
                    icon_color="white"
                )
            ]
        )

        # --- Carregar o conteúdo de cada aba ---
        view_dashboard = create_dashboard_view(page)
        view_ncs = create_ncs_view(page)
        view_nes = create_nes_view(page)
        view_relatorios = create_relatorios_view(page)
        
        abas_principais = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            expand=True,
            tabs=[
                ft.Tab(
                    text="Dashboard",
                    icon="DASHBOARD", # Ícone como string
                    content=view_dashboard
                ),
                ft.Tab(
                    text="Notas de Crédito",
                    icon="PAYMENT", # Ícone como string
                    content=view_ncs
                ),
                ft.Tab(
                    text="Notas de Empenho",
                    icon="RECEIPT", # Ícone como string
                    content=view_nes
                ),
                ft.Tab(
                    text="Relatórios",
                    icon="PRINT", # Ícone como string
                    content=view_relatorios
                ),
            ]
        )
        
        # --- LÓGICA DE ADMIN ---
        if page.session.get("user_funcao") == "admin":
            view_admin = create_admin_view(page)
            abas_principais.tabs.append(
                ft.Tab(
                    text="Administração",
                    icon="ADMIN_PANEL_SETTINGS", # Ícone como string
                    content=view_admin
                )
            )

        page.add(abas_principais)
        page.update()

    def handle_login(e):
        """Tenta fazer login com o Supabase (Lógica do Plano B)."""
        username = username_field.value
        password = password_field.value

        if not username or not password:
            show_snackbar("Preencha o utilizador e a senha.")
            return

        try:
            # --- O "TRUQUE" @SALC.COM ---
            email_formatado = f"{username.strip()}@salc.com"
            # -----------------------------
            
            print(f"Tentativa de login como: {email_formatado}") # Debug

            auth_response = supabase.auth.sign_in_with_password({
                "email": email_formatado,
                "password": password
            })
            
            user = auth_response.user
            page.session.set("user_email", user.email) 
            page.session.set("user_id", user.id)
            page.session.set("access_token", auth_response.session.access_token)

            supabase.auth.set_session(
                access_token=auth_response.session.access_token,
                refresh_token=auth_response.session.refresh_token
            )
            
            # --- Buscar a Função (Role) do Utilizador ---
            # (Corrigido pela política SQL V7, já não dá erro de recursão)
            try:
                resposta_perfil = supabase.table('perfis_usuarios') \
                                          .select('funcao') \
                                          .eq('id_usuario', user.id) \
                                          .single() \
                                          .execute()
                
                funcao = resposta_perfil.data['funcao']
                page.session.set("user_funcao", funcao) 
                print(f"Login OK: {user.email} (Função: {funcao})")
                
            except Exception as ex_perfil:
                print(f"Erro ao buscar perfil: {ex_perfil}")
                show_snackbar(f"Erro ao carregar perfil de utilizador: {ex_perfil}")
                supabase.auth.sign_out() 
                return

            show_main_layout()

        except AuthApiError as ex:
            print(f"Erro de Login: {ex.message}")
            show_snackbar(f"Utilizador ou senha inválidos.")
        except Exception as ex:
            print(f"Erro inesperado: {ex}")
            show_snackbar("Ocorreu um erro inesperado.")
            
    # --- FUNÇÃO handle_register() REMOVIDA ---

    def handle_logout(e):
        """Limpa a sessão e volta para a tela de login."""
        try:
            supabase.auth.sign_out()
        except Exception as ex_logout:
            print(f"Erro ao fazer logout no Supabase: {ex_logout}")
            
        page.session.clear()
        page.appbar = None 
        page.clean()
        
        page.vertical_alignment = ft.MainAxisAlignment.CENTER 
        page.add(build_login_view())
        page.update()


    def show_snackbar(message, color="red"):
        """Mostra uma mensagem de feedback."""
        page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=color
        )
        page.snack_bar.open = True
        page.update()


    def build_login_view():
        """Constrói a tela de login inicial (Versão Plano B)."""
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        
        return ft.Column(
            [
                ft.Text("SISTEMA DE CONTROLE DE NOTAS DE CRÉDITO", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("SALC", size=20, weight=ft.FontWeight.W_500),
                ft.Container(height=30), 
                
                username_field,
                password_field,
                
                ft.Container(height=10), 
                
                ft.Row(
                    [
                        ft.ElevatedButton(
                            "Login", 
                            on_click=handle_login, 
                            expand=True, 
                            icon="LOGIN" # Ícone como string
                        ),
                    ],
                    width=350
                )
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            expand=True
        )

    # --- Estado Inicial (DEV MODE DESATIVADO) ---
    # Mostra a tela de login primeiro
    page.add(build_login_view()) 

# --- Executar a Aplicação ---
if __name__ == "__main__":
    ft.app(
        target=main, 
        view=ft.AppView.FLET_APP, 
        assets_dir="assets" 
    )