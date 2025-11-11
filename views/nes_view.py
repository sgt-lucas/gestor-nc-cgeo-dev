# views/nes_view.py
# (Versão 7.3 - Lote 5.4: Corrige "AssertionError")

import flet as ft
from supabase_client import supabase # Cliente 'anon'
from datetime import datetime
import traceback # <-- (NOVO) ADICIONADO PARA DEBUG

class NesView(ft.Column):
    """
    Representa o conteúdo da aba Notas de Empenho (CRUD).
    Versão 7.3 (Lote 5.4):
    - (BUGFIX) Corrige "AssertionError" ao carregar filtros.
    - Chamadas de 'load_...' movidas do '__init__' para 'on_mount'.
    - (Item 1) ADICIONA MÁSCARA DE MOEDA
    """
    def __init__(self, page, on_data_changed=None, error_modal=None):
        super().__init__()
        self.page = page
        self.id_ne_sendo_editada = None
        self.on_data_changed_callback = on_data_changed
        self.error_modal = error_modal 
        
        self.saldos_ncs_ativas = {}
        
        self.alignment = ft.MainAxisAlignment.START
        self.spacing = 20
        self.padding = 20

        self.progress_ring = ft.ProgressRing(visible=True, width=32, height=32)
        
        # --- TABELA ---
        self.tabela_nes = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Nº Empenho", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("NC Vinculada", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Data", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Valor Empenhado", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Descrição", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Ações", weight=ft.FontWeight.BOLD)),
            ],
            rows=[],
            expand=True,
            border=ft.border.all(1, "grey200"),
            border_radius=8,
        )

        # --- Modais (Lote 5) ---
        self.modal_dropdown_nc = ft.Dropdown(label="Vincular à NC (Obrigatório)")
        
        self.modal_txt_numero_ne = ft.TextField(
            label="Número da NE (6 dígitos)", 
            prefix_text="2025NE",
            input_filter=ft.InputFilter(r"[0-9]"), 
            max_length=6,                           
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        self.modal_txt_data_empenho = ft.TextField(
            label="Data Empenho", 
            hint_text="AAAA-MM-DD", 
            read_only=True, 
            expand=True
        )
        self.btn_abrir_data_empenho = ft.IconButton(
            icon="CALENDAR_MONTH", 
            tooltip="Selecionar Data", 
            on_click=lambda e: self.open_datepicker(self.date_picker_empenho)
        )
        self.date_picker_empenho = ft.DatePicker(
            on_change=self.handle_date_empenho_change,
            first_date=datetime(2020, 1, 1),
            last_date=datetime(2030, 12, 31)
        )
        
        self.modal_txt_valor_empenhado = ft.TextField(
            label="Valor Empenhado", 
            prefix="R$", 
            on_change=self.format_currency_input, 
            keyboard_type=ft.KeyboardType.NUMBER   
        )
        
        self.modal_txt_descricao = ft.TextField(label="Descrição (Opcional)")
        
        self.modal_form_loading_ring = ft.ProgressRing(visible=False, width=24, height=24)
        self.modal_form_btn_cancelar = ft.TextButton("Cancelar", on_click=self.close_modal)
        self.modal_form_btn_salvar = ft.ElevatedButton("Salvar", on_click=self.save_ne, icon="SAVE")
        
        self.modal_form = ft.AlertDialog(
            modal=True, title=ft.Text("Adicionar Nova Nota de Empenho"),
            content=ft.Column(
                [
                    self.modal_dropdown_nc,
                    self.modal_txt_numero_ne,
                    ft.Row(
                        [
                            self.modal_txt_data_empenho, 
                            self.btn_abrir_data_empenho
                        ], 
                        spacing=10
                    ),
                    self.modal_txt_valor_empenhado,
                    self.modal_txt_descricao,
                ], 
                height=450,
                width=500, 
                scroll=ft.ScrollMode.ADAPTIVE,
            ),
            actions=[
                self.modal_form_loading_ring,
                self.modal_form_btn_cancelar,
                self.modal_form_btn_salvar,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.confirm_delete_dialog = ft.AlertDialog(
            modal=True, title=ft.Text("Confirmar Exclusão"),
            content=ft.Text("Tem a certeza de que deseja excluir esta Nota de Empenho? Esta ação não pode ser desfeita."),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.close_confirm_delete(None)),
                ft.ElevatedButton("Excluir", color="white", bgcolor="red", on_click=self.confirm_delete),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        # --- CONTROLOS DE FILTRO ---
        self.filtro_pesquisa_ne = ft.TextField(
            label="Pesquisar por Nº NE", 
            hint_text="Digite parte do número...",
            expand=True,
            on_submit=self.load_nes_data_wrapper
        )
        self.filtro_nc_vinculada = ft.Dropdown(
            label="Filtrar por NC Vinculada",
            options=[ft.dropdown.Option(text="Carregando...", disabled=True)],
            expand=True,
            on_change=self.load_nes_data_wrapper
        )
        
        self.filtro_pi = ft.Dropdown(
            label="Filtrar por PI", 
            options=[ft.dropdown.Option(text="Carregando...", disabled=True)], 
            expand=True, 
            on_change=self.on_pi_filter_change
        )
        self.filtro_nd = ft.Dropdown(
            label="Filtrar por ND", 
            options=[ft.dropdown.Option(text="Carregando...", disabled=True)], 
            expand=True, 
            on_change=self.load_nes_data_wrapper
        )
        
        self.btn_limpar_filtros = ft.IconButton(
            icon="CLEAR_ALL", 
            tooltip="Limpar Filtros",
            on_click=self.limpar_filtros
        )

        # --- LAYOUT ATUALIZADO (com filtros Lote 1) ---
        self.controls = [
            ft.Row(
                [
                    ft.Text("Gestão de Notas de Empenho", size=20, weight=ft.FontWeight.W_600),
                    ft.Row([
                        ft.IconButton(icon="REFRESH", on_click=self.load_nes_data_wrapper, tooltip="Recarregar e Aplicar Filtros"),
                        self.progress_ring,
                    ])
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            ft.ElevatedButton("Adicionar Nova NE", icon="ADD", on_click=self.open_add_modal),
            
            ft.Row([
                self.filtro_pesquisa_ne,
                self.filtro_nc_vinculada,
            ]),
            ft.Row([
                self.filtro_pi,
                self.filtro_nd,
                self.btn_limpar_filtros
            ]),
            
            ft.Divider(),
            ft.Container(
                content=self.tabela_nes,
                expand=True
            )
        ]

        self.page.overlay.append(self.modal_form)
        self.page.overlay.append(self.confirm_delete_dialog)
        self.page.overlay.append(self.date_picker_empenho) 
        
        # --- (CORREÇÃO LOTE 5.4) ---
        # 1. Adicionamos o evento 'on_mount'
        self.on_mount = self.on_view_mount
        
        # 2. As chamadas de 'load' foram MOVIDAS
        # self.load_nc_filter_options()
        # self.load_pi_nd_filter_options() 
        # self.load_nes_data()
        # --- FIM DA CORREÇÃO ---

    # --- (NOVA FUNÇÃO LOTE 5.4) ---
    def on_view_mount(self, e):
        """Chamado pelo Flet DEPOIS que o controlo é adicionado à página."""
        print("NesView: Controlo montado. A carregar dados...")
        self.load_nc_filter_options()
        self.load_pi_nd_filter_options() 
        self.load_nes_data()

    def open_datepicker(self, picker: ft.DatePicker):
        if picker and self.page: 
             if picker not in self.page.overlay:
                 self.page.overlay.append(picker)
                 self.page.update()
             picker.visible = True
             picker.open = True
             self.page.update()

    def handle_date_empenho_change(self, e):
        selected_date = e.control.value
        self.modal_txt_data_empenho.value = selected_date.strftime('%Y-%m-%d') if selected_date else ""
        e.control.open = False
        self.modal_txt_data_empenho.update()

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
        
        if "duplicate key value violates unique constraint" in msg and "notas_de_empenho_numero_ne_key" in msg:
            self.show_error("Erro: Já existe uma Nota de Empenho com este número (2025NE...).")
        elif "duplicate key value violates unique constraint" in msg:
            self.show_error("Erro: Já existe um registo com este identificador único.")
        elif "fetch failed" in msg or "Connection refused" in msg:
            self.show_error("Erro de Rede: Não foi possível conectar ao banco de dados. Verifique sua internet.")
        else:
            self.show_error(f"Erro inesperado ao {context}: {msg}")

    def show_success_snackbar(self, message):
        """Mostra uma mensagem de sucesso (verde)."""
        self.page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor="green")
        self.page.snack_bar.open = True
        self.page.update()

    def formatar_moeda(self, valor):
        try:
            val = float(valor)
            return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, TypeError):
            return "R$ 0,00"
            
    def formatar_valor_para_campo(self, valor):
        try:
            val = float(valor)
            return f"{val:.2f}".replace(".", ",")
        except (ValueError, TypeError):
            return "0,00"
            
    # (LOTE 5)
    def format_currency_input(self, e: ft.ControlEvent):
        """Formata o valor monetário_automaticamente ao digitar."""
        try:
            current_value = e.control.value or ""
            digits = "".join(filter(str.isdigit, current_value))

            if not digits:
                e.control.value = ""
                if self.page: self.page.update()
                return

            int_value = int(digits)
            val_float = int_value / 100.0
            formatted_value = f"{val_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            if e.control.value != formatted_value:
                e.control.value = formatted_value
                e.control.update()
                
        except Exception as ex:
            print(f"Erro ao formatar moeda: {ex}")

    def load_nc_filter_options(self):
        """
        (LOTE 1, Item 3 - CORRIGIDO)
        """
        print("NEs: A carregar NCs para o filtro...")
        try:
            resposta_ncs = supabase.table('ncs_com_saldos') \
                                   .select('id, numero_nc') \
                                   .order('numero_nc', desc=False) \
                                   .execute()

            self.filtro_nc_vinculada.options.clear()
            self.filtro_nc_vinculada.options.append(ft.dropdown.Option(text="Todas as NCs", key=None))
            
            if resposta_ncs.data:
                for nc in resposta_ncs.data:
                    self.filtro_nc_vinculada.options.append(
                        ft.dropdown.Option(key=nc['id'], text=nc['numero_nc'])
                    )
            else:
                 self.filtro_nc_vinculada.options.append(ft.dropdown.Option(text="Nenhuma NC encontrada", disabled=True))

            print("NEs: Opções de filtro NC carregadas.")
            self.update()

        except Exception as ex:
            # (NOVO) Adiciona traceback para debug
            print("--- ERRO CRÍTICO (TRACEBACK) NO NES [load_nc_filter_options] ---")
            traceback.print_exc()
            print("----------------------------------------------------------------")
            
            print(f"Erro ao carregar NCs para filtro: {ex}")
            self.handle_db_error(ex, "carregar filtros de NC")

    def load_pi_nd_filter_options(self, pi_selecionado=None):
        try:
            if pi_selecionado is None:
                print("NEs: A carregar opções de filtro (PIs e NDs)...")
                pis = supabase.rpc('get_distinct_pis').execute()
                self.filtro_pi.options.clear()
                self.filtro_pi.options.append(ft.dropdown.Option(text="Todos os PIs", key=None)) 
                if pis.data:
                    for pi in sorted(pis.data): 
                        if pi: self.filtro_pi.options.append(ft.dropdown.Option(text=pi, key=pi))
                
                nds = supabase.rpc('get_distinct_nds').execute()
                self.filtro_nd.options.clear()
                self.filtro_nd.options.append(ft.dropdown.Option(text="Todas as NDs", key=None)) 
                if nds.data:
                    for nd in sorted(nds.data): 
                        if nd: self.filtro_nd.options.append(ft.dropdown.Option(text=nd, key=nd))
                print("NEs: Opções de filtro PI/ND iniciais carregadas.")
            else:
                print(f"NEs: A carregar NDs para o PI: {pi_selecionado}...")
                self.filtro_nd.disabled = True 
                self.filtro_nd.update()
                nds = supabase.rpc('get_distinct_nds_for_pi', {'p_pi': pi_selecionado}).execute()
                self.filtro_nd.options.clear()
                self.filtro_nd.options.append(ft.dropdown.Option(text="Todas as NDs", key=None))
                if nds.data:
                    for nd in sorted(nds.data):
                         if nd: self.filtro_nd.options.append(ft.dropdown.Option(text=nd, key=nd))
                print("NEs: Filtro ND atualizado.")
                
            self.filtro_nd.disabled = False 
            
            # (CORREÇÃO LOTE 5.4)
            if pi_selecionado is None:
                self.update() 
                
        except Exception as ex: 
            # (NOVO) Adiciona traceback para debug
            print("--- ERRO CRÍTICO (TRACEBACK) NO NES [load_pi_nd_filter_options] ---")
            traceback.print_exc()
            print("---------------------------------------------------------------------")
            
            print(f"Erro ao carregar opções de filtro PI/ND: {ex}")
            self.handle_db_error(ex, "carregar filtros PI/ND")

    def on_pi_filter_change(self, e):
        pi_val = self.filtro_pi.value if self.filtro_pi.value else None
        self.filtro_nd.value = None 
        self.load_pi_nd_filter_options(pi_selecionado=pi_val) 
        self.load_nes_data() 

    def load_nes_data_wrapper(self, e):
        self.load_nes_data()

    def load_nes_data(self):
        print("NEs: A carregar dados com filtros...")
        self.progress_ring.visible = True
        
        # (CORREÇÃO LOTE 5.4)
        self.page.update()

        try:
            query = supabase.table('notas_de_empenho') \
                           .select('*, notas_de_credito(numero_nc, pi, natureza_despesa)')

            if self.filtro_pesquisa_ne.value:
                query = query.ilike('numero_ne', f"%{self.filtro_pesquisa_ne.value}%")
            if self.filtro_nc_vinculada.value:
                query = query.eq('id_nc', self.filtro_nc_vinculada.value)
            if self.filtro_pi.value:
                query = query.eq('notas_de_credito.pi', self.filtro_pi.value)
            if self.filtro_nd.value:
                query = query.eq('notas_de_credito.natureza_despesa', self.filtro_nd.value)

            resposta = query.order('data_empenho', desc=True).execute()

            self.tabela_nes.rows.clear()
            if resposta.data:
                for ne in resposta.data:
                    data_emp = datetime.fromisoformat(ne['data_empenho']).strftime('%d/%m/%Y')
                    nc_vinculada = ne.get('notas_de_credito', {})
                    numero_nc = nc_vinculada.get('numero_nc', 'Erro - NC não encontrada')
                    
                    self.tabela_nes.rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(ne['numero_ne'])),
                                ft.DataCell(ft.Text(numero_nc)),
                                ft.DataCell(ft.Text(data_emp)),
                                ft.DataCell(ft.Text(self.formatar_moeda(ne['valor_empenhado']))),
                                ft.DataCell(ft.Text(ne['descricao'])),
                                ft.DataCell(
                                    ft.Row([
                                        ft.IconButton(
                                            icon="EDIT", 
                                            tooltip="Editar NE",
                                            icon_color="blue700",
                                            on_click=lambda e, ne_obj=ne: self.open_edit_modal(ne_obj)
                                        ),
                                        ft.IconButton(
                                            icon="DELETE", 
                                            tooltip="Excluir NE",
                                            icon_color="red700",
                                            on_click=lambda e, ne_obj=ne: self.open_confirm_delete(ne_obj)
                                        )
                                    ])
                                ),
                            ]
                        )
                    )
            else:
                self.tabela_nes.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text("Nenhuma Nota de Empenho encontrada com estes filtros.", italic=True)),
                        ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")),
                        ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")),
                        ft.DataCell(ft.Text("")),
                    ])
                )
            print("NEs: Dados carregados com sucesso.")

        except Exception as ex:
            # (NOVO) Adiciona traceback para debug
            print("--- ERRO CRÍTICO (TRACEBACK) NO NES [load_nes_data] ---")
            traceback.print_exc()
            print("---------------------------------------------------------")
            
            print(f"Erro ao carregar NEs: {ex}")
            self.handle_db_error(ex, "carregar Notas de Empenho")
        
        self.progress_ring.visible = False
        self.page.update()

    def limpar_filtros(self, e):
        print("NEs: A limpar filtros...")
        self.filtro_pesquisa_ne.value = ""
        self.filtro_nc_vinculada.value = None
        self.filtro_pi.value = None     
        self.filtro_nd.value = None     
        self.load_pi_nd_filter_options(pi_selecionado=None) 
        self.load_nes_data()
        self.page.update()

    def carregar_ncs_para_dropdown_modal(self):
        """Busca NCs 'Ativas' para o dropdown do MODAL e armazena seus saldos."""
        print("NEs Modal: A carregar NCs ativas...")
        try:
            resposta_ncs = supabase.table('ncs_com_saldos') \
                                   .select('id, numero_nc, saldo_disponivel') \
                                   .filter('status_calculado', 'eq', 'Ativa') \
                                   .execute()
            
            self.modal_dropdown_nc.options.clear()
            self.saldos_ncs_ativas.clear() 
            
            if not resposta_ncs.data:
                self.page.snack_bar = ft.SnackBar(ft.Text("Nenhuma NC 'Ativa' encontrada para vincular."), bgcolor="orange")
                self.page.snack_bar.open = True
                self.page.update()
                return False
                
            for nc in resposta_ncs.data:
                saldo_float = float(nc['saldo_disponivel'])
                saldo_formatado = self.formatar_moeda(saldo_float)
                texto_opcao = f"{nc['numero_nc']} (Saldo: {saldo_formatado})"
                
                self.modal_dropdown_nc.options.append(
                    ft.dropdown.Option(key=nc['id'], text=texto_opcao)
                )
                self.saldos_ncs_ativas[nc['id']] = saldo_float
                
            return True
        except Exception as ex:
            print(f"Erro ao carregar NCs para dropdown do modal: {ex}")
            self.handle_db_error(ex, "carregar NCs ativas")
            return False

    def open_add_modal(self, e):
        print("A abrir modal de ADIÇÃO de NE...")
        if not self.carregar_ncs_para_dropdown_modal():
            return 
        self.id_ne_sendo_editada = None
        self.modal_form.title = ft.Text("Adicionar Nova Nota de Empenho")
        self.modal_form_btn_salvar.text = "Salvar"
        self.modal_form_btn_salvar.icon = "SAVE"
        
        self.modal_txt_numero_ne.value = ""
        self.modal_txt_data_empenho.value = ""
        self.modal_txt_valor_empenhado.value = ""
        self.modal_txt_descricao.value = ""
        self.modal_dropdown_nc.value = None
        for campo in [self.modal_dropdown_nc, self.modal_txt_numero_ne, self.modal_txt_data_empenho, self.modal_txt_valor_empenhado]:
            campo.error_text = None
        self.modal_form.open = True
        self.page.update()
        self.modal_txt_numero_ne.focus()

    def open_edit_modal(self, ne):
        print(f"A abrir modal de EDIÇÃO para NE: {ne['numero_ne']}")
        self.carregar_ncs_para_dropdown_modal() 
        self.id_ne_sendo_editada = ne['id']
        self.modal_form.title = ft.Text(f"Editar NE: {ne['numero_ne']}")
        self.modal_form_btn_salvar.text = "Atualizar"
        self.modal_form_btn_salvar.icon = "UPDATE"
        
        self.modal_dropdown_nc.value = ne['id_nc'] 
        
        numero_ne_sem_prefixo = ne.get('numero_ne', '').upper().replace("2025NE", "")
        self.modal_txt_numero_ne.value = numero_ne_sem_prefixo
        
        self.modal_txt_data_empenho.value = ne['data_empenho']
        self.modal_txt_valor_empenhado.value = self.formatar_valor_para_campo(ne['valor_empenhado'])
        self.modal_txt_descricao.value = ne['descricao']
        for campo in [self.modal_dropdown_nc, self.modal_txt_numero_ne, self.modal_txt_data_empenho, self.modal_txt_valor_empenhado]:
            campo.error_text = None
        self.modal_form.open = True
        self.page.update()

    def close_modal(self, e):
        self.modal_form.open = False
        self.id_ne_sendo_editada = None 
        self.page.update()

    def save_ne(self, e):
        
        # 1. Validação
        try:
            print("A validar dados da NE...")
            campos_obrigatorios = {
                self.modal_dropdown_nc: "É obrigatório vincular uma NC.",
                self.modal_txt_numero_ne: "Campo obrigatório.",
                self.modal_txt_data_empenho: "Campo obrigatório.",
                self.modal_txt_valor_empenhado: "Campo obrigatório."
            }
            has_error = False
            for campo, msg_erro in campos_obrigatorios.items():
                campo.error_text = None 
                if not campo.value:
                    campo.error_text = msg_erro
                    has_error = True
            
            if not self.modal_txt_numero_ne.value or len(self.modal_txt_numero_ne.value) != 6:
                self.modal_txt_numero_ne.error_text = "Deve ter 6 dígitos"
                has_error = True

            if has_error:
                print("Erro de validação.")
                self.modal_form.update()
                return 
            
            valor_limpo_str = self.modal_txt_valor_empenhado.value.replace(".", "").replace(",", ".")
            valor_empenhado_float = float(valor_limpo_str)
            id_nc_selecionada = self.modal_dropdown_nc.value
            
            if self.id_ne_sendo_editada is None: 
                if id_nc_selecionada not in self.saldos_ncs_ativas:
                    self.show_error("Erro: NC selecionada não encontrada ou não está ativa. Recarregue a lista.")
                    return
                
                saldo_disponivel_nc = self.saldos_ncs_ativas[id_nc_selecionada]
                
                if valor_empenhado_float > saldo_disponivel_nc:
                    msg_erro_saldo = f"Valor do empenho ({self.formatar_moeda(valor_empenhado_float)}) é maior que o saldo disponível da NC ({self.formatar_moeda(saldo_disponivel_nc)})."
                    self.show_error(msg_erro_saldo)
                    self.modal_txt_valor_empenhado.error_text = "Valor excede o saldo"
                    self.modal_form.update()
                    return
            
            numero_formatado = f"2025NE{self.modal_txt_numero_ne.value.strip().upper()}"
            
            dados_para_salvar = {
                "id_nc": id_nc_selecionada,
                "numero_ne": numero_formatado, 
                "data_empenho": self.modal_txt_data_empenho.value,
                "valor_empenhado": valor_empenhado_float,
                "descricao": self.modal_txt_descricao.value,
            }
        except Exception as ex_validation:
            print(f"Erro na validação de dados: {ex_validation}")
            self.show_error(f"Erro nos dados: {ex_validation}")
            return

        # 2. Feedback de Loading
        self.modal_form_loading_ring.visible = True
        self.modal_form_btn_cancelar.disabled = True
        self.modal_form_btn_salvar.disabled = True
        self.modal_form.update()

        # 3. Execução
        try:
            if self.id_ne_sendo_editada is None:
                print(f"A inserir nova NE no Supabase como: {numero_formatado}...")
                supabase.table('notas_de_empenho').insert(dados_para_salvar).execute()
                msg_sucesso = f"NE {numero_formatado} salva com sucesso!"
            else:
                print(f"A atualizar NE ID: {self.id_ne_sendo_editada} como: {numero_formatado}...")
                supabase.table('notas_de_empenho').update(dados_para_salvar).eq('id', self.id_ne_sendo_editada).execute()
                msg_sucesso = f"NE {numero_formatado} atualizada com sucesso!"
            
            print("NE salva com sucesso.")
            self.show_success_snackbar(msg_sucesso)
            
            self.close_modal(None) 
            self.load_nes_data() 
            if self.on_data_changed_callback:
                self.on_data_changed_callback(None) 

        except Exception as ex:
            print(f"Erro ao salvar NE: {ex}")
            self.handle_db_error(ex, f"salvar NE {numero_formatado}")
            
        finally:
            self.modal_form_loading_ring.visible = False
            self.modal_form_btn_cancelar.disabled = False
            self.modal_form_btn_salvar.disabled = False
            self.modal_form.update()
            
    def open_confirm_delete(self, ne):
        print(f"A pedir confirmação para excluir NE: {ne['numero_ne']}")
        self.confirm_delete_dialog.data = ne['id'] 
        self.page.dialog = self.confirm_delete_dialog 
        self.confirm_delete_dialog.open = True
        self.page.update()

    def close_confirm_delete(self, e):
        self.confirm_delete_dialog.open = False
        self.page.update()

    def confirm_delete(self, e):
        id_para_excluir = self.confirm_delete_dialog.data
        if not id_para_excluir:
            self.show_error("Erro: ID da NE para exclusão não encontrado.")
            self.close_confirm_delete(None)
            return

        try:
            print(f"A excluir NE ID: {id_para_excluir}...")
            supabase.table('notas_de_empenho').delete().eq('id', id_para_excluir).execute()
            print("NE excluída com sucesso.")
            
            self.show_success_snackbar("Nota de Empenho excluída com sucesso.")
            
            self.close_confirm_delete(None)
            self.load_nes_data() 
            if self.on_data_changed_callback:
                self.on_data_changed_callback(None) 
                
        except Exception as ex:
            print(f"Erro ao excluir NE: {ex}")
            self.handle_db_error(ex, "excluir NE")
            self.close_confirm_delete(None)

def create_nes_view(page: ft.Page, on_data_changed=None, error_modal=None): 
    """
    Exporta a nossa NesView como um controlo Flet padrão.
    """
    return NesView(page, on_data_changed=on_data_changed, error_modal=error_modal)