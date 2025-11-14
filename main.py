# main.py
# (Versão Lote 6 - Pronto para Web)
# (REVERTIDO: Removemos toda a lógica de passar 'pickers' como argumento)

import flet as ft
import os 
import traceback 
# import datetime # (Não é mais necessário aqui)

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

# (LOTE 3, Item 11) - Classe de Modal de Erro Reutilizável
class ErrorModal:
    """
    Gestor de Modal de Erro.
    Substitui o SnackBar para garantir que o utilizador veja o erro.
    """
    def __init__(self, page: ft.Page):
        self.page = page
        self.dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(name="ERROR_OUTLINE", color="red"), 
                ft.Text("Ocorreu um Erro")
            ]),
            content=ft.Text("Mensagem de erro padrão."),
            actions=[
                ft.TextButton("OK", on_click=self.close)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        if self.dialog not in self.page.overlay:
             self.page.overlay.append(self.dialog)

    def show(self, error_message):
        """Mostra o modal de erro com uma mensagem específica."""
        print(f"[Modal de Erro] A ser mostrado: {error_message}")
        self.dialog.content = ft.Text(str(error_message))
        self.dialog.open = True
        self.page.update()

    def close(self, e=None):
        """Fecha o modal de erro."""
        self.dialog.open = False
        self.page.update()

# --- Fim (LOTE 3) ---


def main(page: ft.Page):
    
    page.title = "SISTEMA DE CONTROLE DE NOTAS DE CRÉDITO - SALC" 
    
    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary="green800",
            primary_container="green900",
            background="grey100",
            surface="white",
        )
    )
    
    error_modal_global = ErrorModal(page)

    # --- Campos de Login (Plano B) ---
    username_field = ft.TextField(
        label="Utilizador", 
        prefix_icon="PERSON",
        width=350,
        hint_text="ex: joao.silva",
        autofocus=True,
        on_submit=lambda e: handle_login(e) 
    )
    password_field = ft.TextField(
        label="Senha", 
        prefix_icon="LOCK",
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
                    icon="LOGOUT",
                    tooltip="Sair",
                    on_click=handle_logout,
                    icon_color="white"
                )
            ]
        )

        view_dashboard = create_dashboard_view(page, error_modal=error_modal_global)
        view_ncs = create_ncs_view(page, error_modal=error_modal_global)
        
        def on_data_changed_master(e):
            print("Callback Mestre: Recarregando Dashboard e NCs...")
            if view_dashboard: view_dashboard.load_dashboard_data(None)
            if view_ncs: view_ncs.load_ncs_data()
        
        view_ncs.on_data_changed_callback = on_data_changed_master
        view_nes = create_nes_view(page, on_data_changed=on_data_changed_master, error_modal=error_modal_global)
        
        # --- (REVERTIDO) Chamada simples e original ---
        view_relatorios = create_relatorios_view(page, error_modal=error_modal_global)
        
        abas_principais = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            expand=True,
            tabs=[
                ft.Tab(
                    text="Dashboard",
                    icon="DASHBOARD",
                    content=view_dashboard
                ),
                ft.Tab(
                    text="Notas de Crédito",
                    icon="PAYMENT",
                    content=view_ncs
                ),
                ft.Tab(
                    text="Notas de Empenho",
                    icon="RECEIPT",
                    content=view_nes
                ),
                ft.Tab(
                    text="Relatórios",
                    icon="PRINT",
                    content=view_relatorios
                ),
            ]
        )
        
        if page.session.get("user_funcao") == "admin":
            view_admin = create_admin_view(page, error_modal=error_modal_global)
            abas_principais.tabs.append(
                ft.Tab(
                    text="Administração",
                    icon="ADMIN_PANEL_SETTINGS",
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
            error_modal_global.show("Preencha o utilizador e a senha.")
            return
            
        username_field.disabled = True
        password_field.disabled = True
        page.update()

        try:
            email_formatado = f"{username.strip()}@salc.com"
            print(f"Tentativa de login como: {email_formatado}") 

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
            
            try:
                resposta_perfil = supabase.table('perfis_usuarios') \
                                          .select('funcao') \
                                          .eq('id_usuario', user.id) \
                                          .single() \
                                          .execute()
                
                if not resposta_perfil.data:
                    print("Erro: Login bem-sucedido mas perfil não encontrado.")
                    supabase.auth.sign_out()
                    username_field.disabled = False
                    password_field.disabled = False
                    error_modal_global.show("Erro: O seu utilizador autenticou, mas não tem um perfil (função) definido.")
                    return

                funcao = resposta_perfil.data['funcao']
                page.session.set("user_funcao", funcao) 
                print(f"Login OK: {user.email} (Função: {funcao})")
                
            except Exception as ex_perfil:
                print(f"Erro ao buscar perfil: {ex_perfil}")
                supabase.auth.sign_out() 
                username_field.disabled = False
                password_field.disabled = False
                error_modal_global.show(f"Erro ao carregar perfil de utilizador: {ex_perfil}")
                return

            show_main_layout()

        except AuthApiError as ex:
            print(f"Erro de Login: {ex.message}")
            username_field.disabled = False
            password_field.disabled = False
            error_modal_global.show(f"Utilizador ou senha inválidos.")
        except Exception as ex:
            # (LOTE 5.2) Adiciona traceback para apanhar erros de "crash"
            print("--- ERRO CRÍTICO INESPERADO (TRACEBACK) ---")
            traceback.print_exc()
            print("---------------------------------------------")
            
            username_field.disabled = False
            password_field.disabled = False
            error_modal_global.show(f"Ocorreu um erro inesperado: {ex}")
            
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
                            icon="LOGIN"
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
    page.add(build_login_view()) 

# --- (MODIFICADO LOTE 6) Executar a Aplicação (Modo Web) ---
if __name__ == "__main__":
    
    # Define a porta. O Render espera a porta 10000.
    # Para testes locais, usa 8550 se a porta do Render não estiver definida.
    port = int(os.environ.get("PORT", 8550))
    
    print(f"A iniciar aplicação web na porta: {port}")
    
    ft.app(
        target=main, 
        view=ft.AppView.WEB_BROWSER, # <-- MUITO IMPORTANTE
        assets_dir="assets",
        port=port
    )