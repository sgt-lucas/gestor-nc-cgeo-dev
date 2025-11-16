# main.py
# (Versão Refatorada v2.2 - Performance)
# (Corrige o callback 'on_data_changed_master' para apenas atualizar caches)

import flet as ft
import os 
import traceback 

os.environ["FLET_SECRET_KEY"] = os.environ.get("FLET_SECRET_KEY", "chave_secreta_local_padrao_12345!")

from supabase_client import supabase, supabase_admin 
from supabase_auth.errors import AuthApiError 

from views.dashboard_view import create_dashboard_view
from views.ncs_view import create_ncs_view
from views.nes_view import create_nes_view
from views.relatorios_view import create_relatorios_view
from views.admin_view import create_admin_view

class ErrorModal:
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
        print(f"[Modal de Erro] A ser mostrado: {error_message}")
        self.dialog.content = ft.Text(str(error_message))
        self.dialog.open = True
        self.page.update()

    def close(self, e=None):
        self.dialog.open = False
        self.page.update()

def _load_global_caches(page: ft.Page):
    """
    Busca todos os dados de filtro comuns UMA VEZ e armazena na sessão.
    Chamado no login.
    """
    print("A carregar caches globais (PIs, NDs, Seções, NCs)...")
    try:
        # 1. Buscar PIs
        pis_data = supabase.rpc('get_distinct_pis').execute().data
        page.session.set("cache_pis", pis_data or [])
        print(f"Cache: {len(pis_data or [])} PIs carregados.")

        # 2. Buscar NDs
        nds_data = supabase.rpc('get_distinct_nds').execute().data
        page.session.set("cache_nds", nds_data or [])
        print(f"Cache: {len(nds_data or [])} NDs carregados.")

        # 3. Buscar Seções (como um mapa/dict para acesso rápido)
        secoes_resp = supabase.table('secoes').select('id, nome').execute()
        secoes_map = {}
        if secoes_resp.data:
            secoes_map = {secao['id']: secao['nome'] for secao in secoes_resp.data}
        page.session.set("cache_secoes_map", secoes_map)
        print(f"Cache: {len(secoes_map)} Seções carregadas.")

        # 4. Buscar Lista de NCs (para filtros de NE)
        ncs_resp = supabase.table('notas_de_credito').select('id, numero_nc').order('numero_nc').execute()
        page.session.set("cache_ncs_lista", ncs_resp.data or [])
        print(f"Cache: {len(ncs_resp.data or [])} NCs carregadas.")
        
        print("Caches globais carregados com sucesso.")
        return True
        
    except Exception as e:
        print(f"--- ERRO CRÍTICO AO CARREGAR CACHES GLOBAIS ---")
        traceback.print_exc()
        print("--------------------------------------------------")
        return e 
        

def main(page: ft.Page):
    
    page.title = "SISTEMA DE CONTROLE DE NOTAS DE CRÉDITO - SALC" 
    
    page.theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary="blue700",
            primary_container="blue800",
            background="grey100",
            surface="white", 
        )
    )
    page.dark_theme = ft.Theme(
        color_scheme=ft.ColorScheme(
            primary="blue300",       
            primary_container="blue700",
            background="grey900",    
            surface="grey800",     
        )
    )
    
    page.theme_mode = "light"

    error_modal_global = ErrorModal(page)

    username_field = ft.TextField(
        label="Utilizador", 
        prefix_icon="PERSON",
        hint_text="ex: joao.silva",
        autofocus=True,
        on_submit=lambda e: handle_login(e) 
    )
    password_field = ft.TextField(
        label="Senha", 
        prefix_icon="LOCK",
        password=True, 
        can_reveal_password=True,
        on_submit=lambda e: handle_login(e) 
    )
    
    def toggle_theme(e):
        if page.theme_mode == "light":
            page.theme_mode = "dark"
            e.control.icon = "DARK_MODE"
            e.control.tooltip = "Mudar para Modo Escuro"
        else:
            page.theme_mode = "light"
            e.control.icon = "LIGHT_MODE"
            e.control.tooltip = "Mudar para Modo Claro"
        page.update()

    theme_toggle_button = ft.IconButton(
        icon="LIGHT_MODE",
        tooltip="Mudar para Modo Claro",
        on_click=toggle_theme,
        icon_color="white" 
    )

    def show_main_layout(e=None):
        page.clean() 
        page.vertical_alignment = ft.MainAxisAlignment.START 
        page.padding = 0 

        page.appbar = ft.AppBar(
            title=ft.Text("SALC - Sistema de Controle de Notas de Crédito"), 
            bgcolor="blue700", 
            color="white",
            actions=[
                ft.Text(f"Utilizador: {page.session.get('user_email')}"),
                theme_toggle_button, 
                ft.IconButton(
                    icon="LOGOUT",
                    tooltip="Sair",
                    on_click=handle_logout,
                    icon_color="white"
                )
            ]
        )

        # --- (INÍCIO DA CORREÇÃO v2.2) ---
        # Instancia as views, mas NÃO as armazena em variáveis
        # O 'create_..._view' já as regista internamente
        
        # O 'on_data_changed_master' agora é mais inteligente
        def on_data_changed_master(e):
            """
            Chamado quando uma NE ou NC é salva/excluída.
            Recarrega APENAS os caches que podem ter mudado.
            """
            print("Callback Mestre: Recarregando caches voláteis...")
            try:
                # Recarrega caches que MUDAM (lista de NCs)
                ncs_resp = supabase.table('notas_de_credito').select('id, numero_nc').order('numero_nc').execute()
                page.session.set("cache_ncs_lista", ncs_resp.data or [])
                
                # Recarrega PIs/NDs
                pis_data = supabase.rpc('get_distinct_pis').execute().data
                page.session.set("cache_pis", pis_data or [])
                nds_data = supabase.rpc('get_distinct_nds').execute().data
                page.session.set("cache_nds", nds_data or [])
                
                print("Caches voláteis atualizados após alteração.")
            except Exception as ex:
                print(f"Erro ao atualizar caches voláteis: {ex}")
            
            # NÃO chama mais 'view_dashboard.load_dashboard_data()'
            # NÃO chama mais 'view_ncs.load_ncs_data()'
            # A view VISÍVEL já fará isso (ex: nes_view.load_nes_data())
            # A view invisível (ex: dashboard) carregará quando for clicada.
        
        # Cria as views
        all_views = [
            create_dashboard_view(page, error_modal=error_modal_global),
            create_ncs_view(page, on_data_changed=on_data_changed_master, error_modal=error_modal_global),
            create_nes_view(page, on_data_changed=on_data_changed_master, error_modal=error_modal_global),
            create_relatorios_view(page, error_modal=error_modal_global)
        ]
        
        navigation_destinations = [
            ft.NavigationRailDestination(
                icon="DASHBOARD_OUTLINED",
                selected_icon="DASHBOARD",
                label="Dashboard"
            ),
            ft.NavigationRailDestination(
                icon="PAYMENT_OUTLINED",
                selected_icon="PAYMENT",
                label="Notas de Crédito"
            ),
            ft.NavigationRailDestination(
                icon="RECEIPT_OUTLINED",
                selected_icon="RECEIPT",
                label="Notas de Empenho"
            ),
            ft.NavigationRailDestination(
                icon="PRINT_OUTLINED",
                selected_icon="PRINT",
                label="Relatórios"
            ),
        ]
        
        if page.session.get("user_funcao") == "admin":
            all_views.append(create_admin_view(page, error_modal=error_modal_global))
            navigation_destinations.append(
                ft.NavigationRailDestination(
                    icon="ADMIN_PANEL_SETTINGS_OUTLINED",
                    selected_icon="ADMIN_PANEL_SETTINGS",
                    label="Administração"
                )
            )

        view_container = ft.Container(
            content=all_views[0], 
            expand=True,
            padding=20, 
            alignment=ft.alignment.top_left
        )
        
        def switch_view(e):
            index = e.control.selected_index
            view_container.content = all_views[index]
            
            # O Flet irá chamar o 'on_mount' da view automaticamente
            # DEPOIS que a linha 'view_container.update()' for executada.
            
            view_container.update()
        # --- (FIM DA CORREÇÃO v2.2) ---
            
        navigation_rail = ft.NavigationRail(
            selected_index=0,
            label_type="all", 
            min_width=100,
            min_extended_width=200,
            group_alignment=-0.9, 
            destinations=navigation_destinations,
            on_change=switch_view
        )
        
        page.add(
            ft.Row(
                [
                    navigation_rail,
                    ft.VerticalDivider(width=1, thickness=1, color="grey300"),
                    view_container
                ],
                expand=True
            )
        )
        page.update()

    def handle_login(e):
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
                    raise Exception("O seu utilizador autenticou, mas não tem um perfil (função) definido.")

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

            cache_result = _load_global_caches(page)
            if cache_result is not True:
                supabase.auth.sign_out() 
                username_field.disabled = False
                password_field.disabled = False
                error_modal_global.show(f"Erro ao carregar dados iniciais (caches): {cache_result}")
                return

            show_main_layout()

        except AuthApiError as ex:
            print(f"Erro de Login: {ex.message}")
            username_field.disabled = False
            password_field.disabled = False
            error_modal_global.show(f"Utilizador ou senha inválidos.")
        except Exception as ex:
            print("--- ERRO CRÍTICO INESPERADO (TRACEBACK) ---")
            traceback.print_exc()
            print("---------------------------------------------")
            
            username_field.disabled = False
            password_field.disabled = False
            error_modal_global.show(f"Ocorreu um erro inesperado: {ex}")
            
    def handle_logout(e):
        try:
            supabase.auth.sign_out()
        except Exception as ex_logout:
            print(f"Erro ao fazer logout no Supabase: {ex_logout}")
            
        page.session.clear()
        page.appbar = None 
        page.clean()
        
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.padding = 10 
        
        page.add(build_login_view())
        page.update()

    def build_login_view():
        """Constrói a tela de login moderna com ft.Card."""
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        
        return ft.Card(
            width=450,
            elevation=10,
            content=ft.Container(
                padding=30,
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(name="ANCHOR", size=30), 
                                ft.Text("SALC", size=24, weight=ft.FontWeight.BOLD),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        ft.Text(
                            "Sistema de Controle de Notas de Crédito",
                            size=16,
                            weight=ft.FontWeight.W_500,
                            text_align=ft.TextAlign.CENTER
                        ),
                        ft.Divider(height=20),
                        
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
                        )
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        )

    page.add(build_login_view()) 

if __name__ == "__main__":
    
    port = int(os.environ.get("PORT", 8550))
    
    print(f"A iniciar aplicação web na porta: {port}")
    
    ft.app(
        target=main, 
        view=ft.AppView.WEB_BROWSER, 
        assets_dir="assets",
        upload_dir="uploads", 
        port=port
    )