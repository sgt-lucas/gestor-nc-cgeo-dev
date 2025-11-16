# views/admin_view.py
# (Versão Refatorada v1.5 - Layout Moderno)
# (Corrige a lógica de exibição de 'Quem' nos logs)

import flet as ft
from supabase_client import supabase, supabase_admin
from supabase_auth.errors import AuthApiError
import traceback
from datetime import datetime

class AdminView(ft.Row): 
    """
    Representa o conteúdo da aba Administração.
    (v1.5) Corrige exibição de 'Quem' nos logs.
    """
    
    def __init__(self, page, error_modal=None):
        super().__init__()
        self.page = page
        self.alignment = ft.MainAxisAlignment.START
        self.vertical_alignment = ft.CrossAxisAlignment.START 
        self.spacing = 20
        self.error_modal = error_modal
        
        self.user_id_to_login_map = {}
        
        # --- Controlos de Utilizadores ---
        self.progress_ring_users = ft.ProgressRing(visible=True, width=32, height=32)
        self.tabela_users = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Login (Email)", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Nome Completo", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Função", weight=ft.FontWeight.BOLD)), 
                ft.DataColumn(ft.Text("Ações", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            expand=True,
            border=ft.border.all(1, "grey200"),
            border_radius=8,
        )
        
        # --- Controlos de Seções ---
        self.progress_ring_secoes = ft.ProgressRing(visible=True, width=32, height=32)
        self.txt_nova_secao = ft.TextField(label="Nome da Nova Seção", expand=True)
        self.btn_add_secao = ft.IconButton(
            icon="ADD", 
            on_click=self.add_secao,
            tooltip="Adicionar Seção"
        )
        self.lista_secoes_view = ft.ListView(
            expand=True, 
            spacing=10
        )
        
        # --- Controlos de Logs ---
        self.progress_ring_logs = ft.ProgressRing(visible=True, width=32, height=32)
        self.tabela_logs = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Quando", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Quem", weight=ft.FontWeight.BOLD)), 
                ft.DataColumn(ft.Text("Ação", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            expand=True,
            border=ft.border.all(1, "grey200"),
            border_radius=8,
        )
        
        # --- Modais ---
        self.modal_add_login = ft.TextField(label="Login (ex: joao.silva)", prefix_text="@salc.com", hint_text="joao.silva", autofocus=True)
        self.modal_add_senha = ft.TextField(label="Senha Temporária", password=True, can_reveal_password=True)
        self.modal_add_nome = ft.TextField(label="Nome Completo")
        self.modal_add_funcao = ft.Dropdown(
            label="Função (Permissão)",
            options=[
                ft.dropdown.Option("usuario", text="Utilizador Padrão"),
                ft.dropdown.Option("admin", text="Administrador"),
            ],
            value="usuario"
        )
        self.modal_add_loading_ring = ft.ProgressRing(visible=False, width=24, height=24)
        self.modal_add_btn_cancelar = ft.TextButton("Cancelar", on_click=self.close_add_modal)
        self.modal_add_btn_salvar = ft.ElevatedButton("Criar Utilizador", on_click=self.save_new_user, icon="ADD")
        self.modal_add_user = ft.AlertDialog(
            modal=True, 
            title=ft.Text("Adicionar Novo Utilizador"),
            content=ft.Column(
                [
                    self.modal_add_login,
                    self.modal_add_senha,
                    self.modal_add_nome,
                    self.modal_add_funcao,
                ],
                height=320,
                width=400,
                scroll=ft.ScrollMode.ADAPTIVE,
            ),
            actions=[
                self.modal_add_loading_ring,
                self.modal_add_btn_cancelar,
                self.modal_add_btn_salvar,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.confirm_delete_user_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar Exclusão de Utilizador"),
            content=ft.Text("Atenção!\nTem a certeza de que deseja excluir este utilizador?\nEsta ação não pode ser desfeita."),
            actions=[
                ft.TextButton("Cancelar", on_click=self.close_confirm_delete_user),
                ft.ElevatedButton("Excluir Utilizador", color="white", bgcolor="red", on_click=self.confirm_delete_user),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        # --- Layout ---
        
        # Card 1: Gestão de Utilizadores
        self.layout_gestao_users = ft.Card(
            elevation=4,
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("Gestão de Utilizadores", size=20, weight=ft.FontWeight.W_600),
                                ft.Row([
                                    ft.IconButton(icon="REFRESH", on_click=self.load_users_wrapper, tooltip="Recarregar Lista"),
                                    self.progress_ring_users,
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
                        ft.Column(
                            [self.tabela_users],
                            scroll=ft.ScrollMode.ADAPTIVE,
                            expand=True
                        )
                    ],
                    height=450, 
                    spacing=15
                ),
                padding=20,
            )
        )
        
        # Card 2: Gestão de Seções
        self.layout_gestao_secoes = ft.Card(
            elevation=4,
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("Gestão de Seções", size=20, weight=ft.FontWeight.W_600),
                                ft.Row([
                                    ft.IconButton(icon="REFRESH", on_click=self.load_secoes_wrapper, tooltip="Recarregar Lista"),
                                    self.progress_ring_secoes,
                                ])
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Row(
                            [
                                self.txt_nova_secao,
                                self.btn_add_secao,
                            ]
                        ),
                        ft.Divider(),
                        self.lista_secoes_view,
                    ],
                    height=300, 
                    spacing=15
                ),
                padding=20,
            )
        )

        # Card 3: Logs de Auditoria
        self.layout_gestao_logs = ft.Card(
            elevation=4,
            expand=True, 
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("Logs de Auditoria", size=20, weight=ft.FontWeight.W_600),
                                ft.Row([
                                    ft.IconButton(icon="REFRESH", on_click=self.load_logs_wrapper, tooltip="Recarregar Logs"),
                                    self.progress_ring_logs,
                                ])
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Divider(),
                        ft.Column(
                            [self.tabela_logs],
                            scroll=ft.ScrollMode.ADAPTIVE,
                            expand=True
                        )
                    ],
                    expand=True,
                    spacing=15
                ),
                padding=20,
            )
        )

        self.controls = [
            # Coluna da Esquerda (60%)
            ft.Column(
                [
                    self.layout_gestao_users,
                    self.layout_gestao_secoes
                ],
                expand=6,
                spacing=20,
                scroll=ft.ScrollMode.ADAPTIVE
            ),
            # Coluna da Direita (40%)
            ft.Column(
                [
                    self.layout_gestao_logs
                ],
                expand=4
            )
        ]

        self.page.overlay.append(self.modal_add_user)
        self.page.overlay.append(self.confirm_delete_user_dialog)
        
        self.on_mount = self.on_view_mount
        
    def on_view_mount(self, e):
        """Chamado pelo Flet DEPOIS que o controlo é adicionado à página."""
        print("AdminView: Controlo montado. A carregar dados...")
        self.load_users()
        self.load_secoes()
        self.load_logs() 

    def on_action_not_implemented(self, e):
        self.page.snack_bar = ft.SnackBar(ft.Text("Esta funcionalidade (Editar Utilizador) ainda não foi implementada."), bgcolor="orange")
        self.page.snack_bar.open = True
        self.page.update()

    def load_users_wrapper(self, e):
        """Wrapper para o botão de refresh."""
        self.load_users()

    def load_users(self):
        print("AdminView: A carregar lista de utilizadores (Modo Admin)...")
        self.progress_ring_users.visible = True
        self.update()
        
        try:
            auth_users_response = supabase_admin.auth.admin.list_users()
            auth_users_map = {user.id: user.email for user in auth_users_response}
            
            resposta_perfis = supabase_admin.table('perfis_usuarios').select('*').execute()
            
            self.tabela_users.rows.clear()
            self.user_id_to_login_map.clear() 
            
            if resposta_perfis.data:
                for profile in resposta_perfis.data:
                    user_id = profile.get('id_usuario')
                    user_email = auth_users_map.get(user_id, "Email não encontrado")
                    login_name = user_email.replace("@salc.com", "")
                    nome_completo = profile.get('nome_completo', 'Nome Desconhecido')
                    
                    # Popula o mapa com o LOGIN
                    self.user_id_to_login_map[user_id] = login_name 

                    self.tabela_users.rows.append(
                        ft.DataRow(
                            data=user_id, 
                            cells=[
                                ft.DataCell(ft.Text(login_name, tooltip=user_email)), 
                                ft.DataCell(ft.Text(nome_completo)), 
                                ft.DataCell(ft.Text(profile.get('funcao', 'N/A'))), 
                                ft.DataCell(
                                    ft.Row([
                                        ft.IconButton(
                                            icon="EDIT", 
                                            tooltip="Editar Função", 
                                            icon_color="blue700", 
                                            on_click=self.on_action_not_implemented
                                        ),
                                        ft.IconButton(
                                            icon="DELETE", 
                                            tooltip="Excluir Utilizador", 
                                            icon_color="red700", 
                                            on_click=lambda e, u_id=user_id, u_login=login_name: self.open_confirm_delete_user(u_id, u_login)
                                        ),
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
            traceback.print_exc()
            self.handle_db_error(ex, "carregar utilizadores")
        
        finally:
            self.progress_ring_users.visible = False
            self.update()

    # --- Funções de Gestão de Seções (sem alteração) ---
    def load_secoes_wrapper(self, e):
        self.load_secoes()

    def load_secoes(self):
        print("AdminView: A carregar lista de seções...")
        self.progress_ring_secoes.visible = True
        self.update()
        
        try:
            resposta = supabase_admin.table('secoes').select('*').order('nome').execute()
            
            self.lista_secoes_view.controls.clear()
            if resposta.data:
                for secao in resposta.data:
                    self.lista_secoes_view.controls.append(
                        ft.Row(
                            [
                                ft.Text(secao['nome'], expand=True),
                                ft.IconButton(
                                    icon="DELETE_OUTLINE", 
                                    icon_color="red700",
                                    tooltip="Excluir Seção",
                                    data=secao['id'], 
                                    on_click=self.delete_secao
                                )
                            ]
                        )
                    )
            else:
                self.lista_secoes_view.controls.append(ft.Text("Nenhuma seção cadastrada.", italic=True))
                
            print("AdminView: Seções carregadas com sucesso.")

        except Exception as ex:
            print(f"Erro CRÍTICO ao carregar seções: {ex}") 
            traceback.print_exc()
            self.handle_db_error(ex, "carregar seções")
        
        finally:
            self.progress_ring_secoes.visible = False
            self.update()

    def add_secao(self, e):
        nome_secao = self.txt_nova_secao.value.strip()
        if not nome_secao:
            self.show_error("Por favor, digite um nome para a seção.")
            return

        print(f"AdminView: A adicionar seção: {nome_secao}")
        self.progress_ring_secoes.visible = True
        self.update()

        try:
            supabase_admin.table('secoes').insert({"nome": nome_secao}).execute()
            
            self.show_success_snackbar(f"Seção '{nome_secao}' adicionada!")
            self.txt_nova_secao.value = ""
            self.load_secoes() 
            self.load_logs() # Recarrega os logs
        except Exception as ex:
            print(f"Erro ao adicionar seção: {ex}")
            traceback.print_exc()
            self.handle_db_error(ex, "adicionar seção")
        finally:
            self.progress_ring_secoes.visible = False
            self.update()

    def delete_secao(self, e):
        secao_id = e.control.data
        
        print(f"AdminView: A apagar seção ID: {secao_id}")
        self.progress_ring_secoes.visible = True
        self.update()
        
        try:
            supabase_admin.table('secoes').delete().eq('id', secao_id).execute()
            self.show_success_snackbar("Seção apagada com sucesso.")
            self.load_secoes()
            self.load_logs() # Recarrega os logs
            
        except Exception as ex:
            print(f"Erro ao apagar seção: {ex}")
            traceback.print_exc()
            self.handle_db_error(ex, "apagar seção")
            self.progress_ring_secoes.visible = False 
            self.update()

    # --- (INÍCIO DA CORREÇÃO v1.5) ---
    def load_logs_wrapper(self, e):
        # Garante que o mapa de utilizadores está atualizado antes de carregar os logs
        self.load_users()
        self.load_logs()
        
    def load_logs(self):
        """Carrega os logs de auditoria mais recentes."""
        # Esta função AGORA assume que 'self.user_id_to_login_map' está preenchido
        print("AdminView: A carregar logs de auditoria...")
        self.progress_ring_logs.visible = True
        self.update()
        
        # Garante que o mapa não está vazio, caso esta função seja chamada diretamente
        if not self.user_id_to_login_map:
            print("AdminView: Mapa de utilizadores vazio. A pré-carregar...")
            self.load_users() # Garante que o mapa está populado
        
        try:
            resposta = supabase_admin.table('audit_logs') \
                                     .select('*') \
                                     .order('created_at', desc=True) \
                                     .limit(50) \
                                     .execute()
            
            self.tabela_logs.rows.clear()
            
            if resposta.data:
                for log in resposta.data:
                    quando_dt = datetime.fromisoformat(log['created_at'])
                    quando_str = quando_dt.strftime('%d/%m/%y %H:%M')
                    
                    user_id = log.get('user_id')
                    
                    # Lógica de 'Quem' melhorada
                    if user_id:
                        # Tenta buscar o login no mapa
                        quem_str = self.user_id_to_login_map.get(user_id, f"ID: ...{str(user_id)[-6:]}") # Mostra ID encurtado se não achar
                    else:
                        # Se user_id for None
                        quem_str = "Sistema" # Ação provavelmente foi via service_role
                    
                    acao_str = f"{log.get('action', 'AÇÃO')} em {log.get('target_table', 'tabela')}"
                    
                    self.tabela_logs.rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(quando_str)),
                                ft.DataCell(ft.Text(quem_str)),
                                ft.DataCell(ft.Text(acao_str, tooltip=f"Record ID: {log.get('record_id')}")),
                            ]
                        )
                    )
            else:
                self.tabela_logs.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text("Nenhum log de auditoria encontrado.", italic=True)),
                        ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")),
                    ])
                )
            
            print("AdminView: Logs carregados com sucesso.")

        except Exception as ex:
            print(f"Erro CRÍTICO ao carregar logs: {ex}") 
            traceback.print_exc()
            self.handle_db_error(ex, "carregar logs de auditoria")
        
        finally:
            self.progress_ring_logs.visible = False
            self.update()
    # --- (FIM DA CORREÇÃO v1.5) ---

    # --- Funções do Modal de Adicionar Utilizador (sem alteração) ---
    def open_add_modal(self, e):
        self.modal_add_login.value = ""
        self.modal_add_senha.value = ""
        self.modal_add_nome.value = ""
        self.modal_add_funcao.value = "usuario"
        self.modal_add_login.error_text = None
        self.modal_add_senha.error_text = None
        self.modal_add_nome.error_text = None
        self.modal_add_user.open = True
        self.page.update()
        self.modal_add_login.focus()

    def close_add_modal(self, e):
        self.modal_add_user.open = False
        self.page.update()

    def save_new_user(self, e):
        login = self.modal_add_login.value.strip()
        senha = self.modal_add_senha.value
        nome = self.modal_add_nome.value.strip()
        funcao = self.modal_add_funcao.value
        
        has_error = False
        if not login:
            self.modal_add_login.error_text = "Obrigatório"
            has_error = True
        if not senha:
            self.modal_add_senha.error_text = "Obrigatório"
            has_error = True
        if not nome:
            self.modal_add_nome.error_text = "Obrigatório"
            has_error = True
            
        if has_error:
            self.modal_add_user.update()
            return
            
        email_formatado = f"{login}@salc.com"

        self.modal_add_loading_ring.visible = True
        self.modal_add_btn_cancelar.disabled = True
        self.modal_add_btn_salvar.disabled = True
        self.modal_add_user.update()

        try:
            print(f"AdminView: A criar utilizador de Auth: {email_formatado}...")
            user_response = supabase_admin.auth.admin.create_user({
                "email": email_formatado,
                "password": senha,
                "email_confirm": True
            })
            
            novo_user_id = user_response.user.id
            print(f"AdminView: Utilizador de Auth criado com ID: {novo_user_id}")

            print("AdminView: A inserir perfil na tabela 'perfis_usuarios'...")
            supabase_admin.table('perfis_usuarios').insert({
                "id_usuario": novo_user_id,
                "nome_completo": nome,
                "funcao": funcao
            }).execute()
            
            print("AdminView: Perfil inserido com sucesso.")
            
            self.show_success_snackbar(f"Utilizador '{login}' criado com sucesso!")
            self.close_add_modal(None)
            self.load_users() 
            self.load_logs() # Recarrega os logs

        except AuthApiError as ex_auth:
            print(f"Erro de Autenticação ao criar utilizador: {ex_auth.message}")
            self.show_error(f"Erro ao criar utilizador: {ex_auth.message}")
        except Exception as ex:
            print(f"Erro inesperado ao criar utilizador: {ex}")
            traceback.print_exc()
            self.handle_db_error(ex, "criar novo utilizador")

        finally:
            self.modal_add_loading_ring.visible = False
            self.modal_add_btn_cancelar.disabled = False
            self.modal_add_btn_salvar.disabled = False
            self.modal_add_user.update()
            
    # --- Funções de Exclusão de Utilizador ---
    def open_confirm_delete_user(self, user_id, user_login):
        """Abre o modal de confirmação de exclusão."""
        print(f"A pedir confirmação para excluir utilizador: {user_login} (ID: {user_id})")
        self.confirm_delete_user_dialog.data = {"id": user_id, "login": user_login} 
        self.confirm_delete_user_dialog.content = ft.Text(f"Atenção!\nTem a certeza de que deseja excluir o utilizador '{user_login}'?\nEsta ação não pode ser desfeita.")
        self.page.dialog = self.confirm_delete_user_dialog 
        self.confirm_delete_user_dialog.open = True
        self.page.update()

    def close_confirm_delete_user(self, e):
        self.confirm_delete_user_dialog.open = False
        self.page.update()

    def confirm_delete_user(self, e):
        """Exclui o utilizador do Auth e do DB."""
        if not self.confirm_delete_user_dialog.data:
            self.show_error("Erro: ID do utilizador para exclusão não encontrado.")
            self.close_confirm_delete_user(None)
            return
            
        user_id = self.confirm_delete_user_dialog.data.get("id")
        user_login = self.confirm_delete_user_dialog.data.get("login")

        print(f"A excluir utilizador ID: {user_id}...")
        self.progress_ring_users.visible = True
        self.update()
        
        try:
            # (v1.4) Exclui primeiro o perfil, depois o utilizador
            # Isto evita erros de FK se a RLS/Triggers falharem
            supabase_admin.table('perfis_usuarios').delete().eq('id_usuario', user_id).execute()
            print(f"Perfil do utilizador {user_login} excluído.")
            
            # Exclui o utilizador do Supabase Auth
            supabase_admin.auth.admin.delete_user(user_id)
            print(f"Utilizador {user_login} excluído do Auth.")
            
            self.show_success_snackbar(f"Utilizador '{user_login}' excluído com sucesso.")
            
            self.close_confirm_delete_user(None)
            self.load_users() # Recarrega a lista de utilizadores
            self.load_logs() # Recarrega os logs
                
        except Exception as ex:
            print(f"Erro ao excluir utilizador: {ex}")
            self.handle_db_error(ex, f"excluir utilizador {user_login}")
            self.close_confirm_delete_user(None)
        finally:
            self.progress_ring_users.visible = False
            self.update()

    def show_error(self, message):
        if self.error_modal:
            self.error_modal.show(message)
        else:
            print(f"ERRO CRÍTICO (Modal não encontrado): {message}")
            
    def handle_db_error(self, ex, context=""):
        msg = str(ex)
        print(f"Erro de DB Bruto ({context}): {msg}") 
        
        if "violates foreign key constraint" in msg and "on table \"audit_logs\"" in msg:
             self.show_error("Erro: Não é possível excluir este utilizador pois ele possui registos nos logs de auditoria. (Considere anonimizar o utilizador em vez de excluir).")
        elif "violates foreign key constraint" in msg:
             self.show_error("Erro de Base de Dados: Não é possível apagar este item pois ele está a ser usado por outro registo (ex: uma NC a usar esta Seção).")
        elif "duplicate key value violates unique constraint" in msg:
            if "perfis_usuarios_id_usuario_key" in msg:
                 self.show_error("Erro de Base de Dados: Este ID de utilizador já existe na tabela de perfis.")
            elif "secoes_nome_key" in msg:
                 self.show_error("Erro: Já existe uma seção com este nome.")
            else:
                self.show_error("Erro: Já existe um registo com este identificador único.")
        elif "fetch failed" in msg or "Connection refused" in msg or "Server disconnected" in msg:
            self.show_error("Erro de Rede: Não foi possível conectar ao banco de dados. Tente atualizar a aba.")
        elif "Invalid API key" in msg or "invalid JWT" in msg:
             self.show_error("Erro de Autenticação de Admin: A Chave de Serviço (service_role) está incorreta. Verifique o ficheiro .env ou as variáveis do servidor.")
        else:
            self.show_error(f"Erro inesperado ao {context}: {msg}")

    def show_success_snackbar(self, message):
        self.page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor="green")
        self.page.snack_bar.open = True
        self.page.update()

# --- Função de Nível Superior (Obrigatória) ---
def create_admin_view(page: ft.Page, error_modal=None):
    """
    Exporta a nossa AdminView como um controlo Flet padrão.
    """
    return AdminView(page, error_modal=error_modal)