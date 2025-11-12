# views/admin_view.py
# (Versão 9.7 - Lote 8.4: Corrige Scroll Global do Admin)

import flet as ft
# Importamos AMBOS os clientes
from supabase_client import supabase, supabase_admin
from supabase_auth.errors import AuthApiError
import traceback

class AdminView(ft.Column):
    """
    Representa o conteúdo da aba Administração.
    Versão 9.7 (Lote 8.4):
    - (BUGFIX) Adiciona 'self.scroll = ft.ScrollMode.ADAPTIVE' à classe principal.
    - (BUGFIX) Remove 'expand=True' dos containers internos e da tabela
      para permitir que o scroll global da aba funcione.
    - (BUGFIX) Substitui o Row(expand=True) por um ResponsiveRow.
    """
    
    def __init__(self, page, error_modal=None):
        super().__init__()
        self.page = page
        self.alignment = ft.MainAxisAlignment.START
        self.spacing = 20
        self.padding = 20
        self.error_modal = error_modal
        
        # --- (CORREÇÃO LOTE 8.4) ---
        self.scroll = ft.ScrollMode.ADAPTIVE # <-- ADICIONADO
        # --- FIM DA CORREÇÃO ---
        
        self.progress_ring_users = ft.ProgressRing(visible=True, width=32, height=32)
        
        # (Ponto 5) Controlos para Seções
        self.progress_ring_secoes = ft.ProgressRing(visible=True, width=32, height=32)
        self.txt_nova_secao = ft.TextField(label="Nome da Nova Seção", expand=True)
        
        self.btn_add_secao = ft.IconButton(
            icon="ADD", 
            on_click=self.add_secao,
            tooltip="Adicionar Seção"
        )
        
        # (Lote 8.3) - Corrigido, 'expand' é necessário para a rolagem INTERNA da lista
        self.lista_secoes_view = ft.ListView(
            expand=True, 
            spacing=10
        )
        
        self.tabela_users = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Login (Email)", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Nome Completo", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Função", weight=ft.FontWeight.BOLD)), 
                ft.DataColumn(ft.Text("Ações", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            # (CORREÇÃO LOTE 8.4) - 'expand' removido
            border=ft.border.all(1, "grey200"),
            border_radius=8,
        )
        
        # --- (Ponto 1c) Modal de Adicionar Utilizador ---
        self.modal_add_login = ft.TextField(
            label="Login (ex: joao.silva)", 
            prefix_text="@salc.com", 
            hint_text="joao.silva",
            autofocus=True
        )
        self.modal_add_senha = ft.TextField(
            label="Senha Temporária", 
            password=True, 
            can_reveal_password=True
        )
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
        # --- Fim do Modal ---
        
        # --- (Ponto 5) Layout da Página ---
        self.layout_gestao_users = ft.Container(
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
                    # (CORREÇÃO LOTE 8.4) - 'expand' removido
                    ft.Container(
                        content=self.tabela_users,
                        # expand=True <-- REMOVIDO
                    )
                ],
                # (CORREÇÃO LOTE 8.4) - 'expand' removido
            ),
            padding=20,
            border=ft.border.all(1, "grey200"),
            border_radius=8
        )
        
        self.layout_gestao_secoes = ft.Container(
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
                    # (CORREÇÃO LOTE 8.4) 
                    # O expand=True aqui (no ListView) está correto, 
                    # mas precisamos de um 'height' no container-pai 
                    # para que ele saiba rolar internamente.
                    ft.Container(
                        content=self.lista_secoes_view, 
                        height=400 # Altura fixa para a lista de seções
                    )
                ],
                # (CORREÇÃO LOTE 8.4) - 'expand' removido
            ),
            padding=20,
            border=ft.border.all(1, "grey200"),
            border_radius=8
        )

        # (CORREÇÃO LOTE 8.4) - Substituído Row(expand=True) por ResponsiveRow
        self.controls = [
            ft.ResponsiveRow(
                [
                    # Layout dividido 60/40 (em telas 'large') e 100% (em telas 'small')
                    ft.Column(col={"sm": 12, "lg": 7}, controls=[self.layout_gestao_users]),
                    ft.Column(col={"sm": 12, "lg": 5}, controls=[self.layout_gestao_secoes]),
                ]
            )
        ]
        # --- Fim (Ponto 5) ---

        self.page.overlay.append(self.modal_add_user)
        self.on_mount = self.on_view_mount
        
    def on_view_mount(self, e):
        """Chamado pelo Flet DEPOIS que o controlo é adicionado à página."""
        print("AdminView: Controlo montado. A carregar dados...")
        self.load_users()
        self.load_secoes() # (NOVO - Ponto 5)

    def load_users_wrapper(self, e):
        """Wrapper para o botão de refresh."""
        self.load_users()

    def load_users(self):
        """
        Busca TODOS os perfis E utilizadores (para o email).
        (V9.1 - Corrigido AttributeError)
        """
        print("AdminView: A carregar lista de utilizadores (Modo Admin)...")
        self.progress_ring_users.visible = True
        self.update()
        
        try:
            # 1. A lista de utilizadores AUTENTICADOS (para os emails)
            auth_users_response = supabase_admin.auth.admin.list_users()
            auth_users_map = {user.id: user.email for user in auth_users_response}
            
            # 2. A lista de PERFIS (para nome e função)
            resposta_perfis = supabase_admin.table('perfis_usuarios').select('*').execute()
            
            self.tabela_users.rows.clear()
            
            if resposta_perfis.data:
                for profile in resposta_perfis.data:
                    user_id = profile.get('id_usuario')
                    user_email = auth_users_map.get(user_id, "Email não encontrado")
                    login_name = user_email.replace("@salc.com", "")

                    self.tabela_users.rows.append(
                        ft.DataRow(
                            data=user_id, 
                            cells=[
                                ft.DataCell(ft.Text(login_name, tooltip=user_email)), 
                                ft.DataCell(ft.Text(profile.get('nome_completo', '---'))), 
                                ft.DataCell(ft.Text(profile.get('funcao', 'N/A'))), 
                                ft.DataCell(
                                    ft.Row([
                                        ft.IconButton(icon="EDIT", tooltip="Editar Função (Brevemente)", icon_color="blue700", disabled=True),
                                        ft.IconButton(icon="DELETE", tooltip="Excluir Utilizador (Brevemente)", icon_color="red700", disabled=True),
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

    # --- (NOVO - Ponto 5) Funções de Gestão de Seções ---

    def load_secoes_wrapper(self, e):
        self.load_secoes()

    def load_secoes(self):
        """Carrega a lista de seções da nova tabela 'secoes'."""
        print("AdminView: A carregar lista de seções...")
        self.progress_ring_secoes.visible = True
        self.update()
        
        try:
            # Usamos o cliente 'admin' para ler, pois só admins acedem esta página
            resposta = supabase_admin.table('secoes').select('*').order('nome').execute()
            
            self.lista_secoes_view.controls.clear()
            if resposta.data:
                for secao in resposta.data:
                    self.lista_secoes_view.controls.append(
                        ft.Row(
                            [
                                ft.Text(secao['nome'], expand=True),
                                ft.IconButton(
                                    icon="DELETE_OUTLINE", # Ícone como string
                                    icon_color="red700",
                                    tooltip="Excluir Seção",
                                    data=secao['id'], # Guarda o ID para a função
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
        """Adiciona uma nova seção."""
        nome_secao = self.txt_nova_secao.value.strip()
        if not nome_secao:
            self.show_error("Por favor, digite um nome para a seção.")
            return

        print(f"AdminView: A adicionar seção: {nome_secao}")
        self.progress_ring_secoes.visible = True
        self.update()

        try:
            # Usamos o cliente 'admin' (service_role) para escrever
            supabase_admin.table('secoes').insert({"nome": nome_secao}).execute()
            
            self.show_success_snackbar(f"Seção '{nome_secao}' adicionada!")
            self.txt_nova_secao.value = ""
            self.load_secoes() # Recarrega a lista

        except Exception as ex:
            print(f"Erro ao adicionar seção: {ex}")
            traceback.print_exc()
            self.handle_db_error(ex, "adicionar seção")
        
        finally:
            self.progress_ring_secoes.visible = False
            self.update()

    def delete_secao(self, e):
        """Apaga uma seção (usa o ID guardado no 'data' do botão)."""
        secao_id = e.control.data
        
        print(f"AdminView: A apagar seção ID: {secao_id}")
        self.progress_ring_secoes.visible = True
        self.update()
        
        try:
            supabase_admin.table('secoes').delete().eq('id', secao_id).execute()
            self.show_success_snackbar("Seção apagada com sucesso.")
            self.load_secoes() # Recarrega a lista
            
        except Exception as ex:
            print(f"Erro ao apagar seção: {ex}")
            traceback.print_exc()
            self.handle_db_error(ex, "apagar seção")
            self.progress_ring_secoes.visible = False # Garante que o anel desaparece em caso de erro
            self.update()

    # --- Fim (Ponto 5) ---


    # --- (Ponto 1c) Funções do Modal de Adicionar Utilizador ---

    def open_add_modal(self, e):
        """Abre o modal para adicionar um novo utilizador."""
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
        """Cria o utilizador no Supabase Auth e insere o perfil."""
        
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
            self.load_users() # Recarrega a lista

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

    # --- Fim (Ponto 1c) ---

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
        
        # (LOTE 7.2) Traduz 'duplicate key'
        if "duplicate key value violates unique constraint" in msg:
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
        """Mostra uma mensagem de sucesso (verde)."""
        self.page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor="green")
        self.page.snack_bar.open = True
        self.page.update()

# --- Função de Nível Superior (Obrigatória) ---
def create_admin_view(page: ft.Page, error_modal=None):
    """
    Exporta a nossa AdminView como um controlo Flet padrão.
    """
    return AdminView(page, error_modal=error_modal)