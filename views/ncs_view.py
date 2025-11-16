# views/ncs_view.py
# (Versão Refatorada v1.6 - Layout Moderno)
# (Adiciona todos os campos orçamentários ao modal "Quick View")

import flet as ft
from supabase_client import supabase # Cliente 'anon'
from datetime import datetime
import traceback 

import io       
import httpx    
import os       

# --- IMPORTAÇÕES PARA PDF ---
import pdfplumber
import re
# ----------------------------

class NcsView(ft.Column):
    """
    Representa o conteúdo da aba Notas de Crédito (CRUD).
    (v1.6) Modal "Quick View" exibe todos os dados.
    """
    
    def __init__(self, page, on_data_changed=None, error_modal=None):
        super().__init__()
        self.page = page
        self.id_sendo_editado = None
        self.id_nc_para_recolhimento = None
        self.on_data_changed_callback = on_data_changed
        self.error_modal = error_modal
        
        self.secoes_cache = {} 
        
        self.alignment = ft.MainAxisAlignment.START
        self.spacing = 20
        
        self.progress_ring = ft.ProgressRing(visible=True, width=32, height=32)
        
        self.file_picker_import = ft.FilePicker(
            on_result=self.on_file_picker_result,
            on_upload=self.on_upload_progress 
        )
        
        self.tabela_ncs = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Número NC", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("PI", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("ND", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Valor Inicial", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Saldo Disp.", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Ações", weight=ft.FontWeight.BOLD)),
            ], 
            rows=[], 
            expand=True, 
            border=ft.border.all(1, "grey200"), 
            border_radius=8,
        )

        # --- (INÍCIO DA ATUALIZAÇÃO v1.6) ---
        # --- Novo Modal "Quick View" ---
        self.quick_view_title = ft.Text("Detalhes da NC", size=20, weight=ft.FontWeight.BOLD)
        self.qv_status = ft.Text(size=16)
        self.qv_pi_nd = ft.Text(selectable=True)
        # Novos campos para info orçamentária
        self.qv_ptres_fonte = ft.Text(selectable=True)
        self.qv_ug_secao = ft.Text(selectable=True)
        
        self.qv_valor_inicial = ft.Text(selectable=True)
        self.qv_saldo = ft.Text(selectable=True)
        self.qv_percent_empenhado = ft.Text(selectable=True)
        self.qv_prazo = ft.Text(selectable=True)
        self.qv_observacao = ft.Text(selectable=True, max_lines=5, overflow=ft.TextOverflow.ELLIPSIS)

        self.quick_view_modal = ft.AlertDialog(
            modal=True,
            title=self.quick_view_title,
            content=ft.Column(
                [
                    self.qv_status,
                    ft.Divider(),
                    ft.Text("Informação Orçamentária:", weight=ft.FontWeight.BOLD),
                    self.qv_pi_nd,
                    self.qv_ptres_fonte, # Adicionado
                    self.qv_ug_secao,   # Adicionado
                    ft.Divider(),
                    ft.Text("Valores:", weight=ft.FontWeight.BOLD),
                    self.qv_valor_inicial,
                    self.qv_saldo,
                    self.qv_percent_empenhado,
                    ft.Divider(),
                    ft.Text("Prazos:", weight=ft.FontWeight.BOLD),
                    self.qv_prazo,
                    ft.Divider(),
                    ft.Text("Observação:", weight=ft.FontWeight.BOLD),
                    self.qv_observacao,
                ],
                height=450, # Aumenta a altura para os novos campos
                width=500,
                scroll=ft.ScrollMode.ADAPTIVE
            ),
            actions=[
                ft.TextButton("Fechar", on_click=self.close_quick_view_modal)
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        # --- (FIM DA ATUALIZAÇÃO v1.6) ---

        # --- Modais (Sem alteração) ---
        self.modal_txt_numero_nc = ft.TextField(label="Número da NC (6 dígitos)", prefix_text="2025NC", input_filter=ft.InputFilter(r"[0-9]"), max_length=6, keyboard_type=ft.KeyboardType.NUMBER)
        self.modal_dd_secao = ft.Dropdown(label="Seção (Opcional)", options=[ft.dropdown.Option(text="Carregando...", disabled=True)],)
        self.modal_txt_data_recebimento = ft.TextField(label="Data Recebimento", hint_text="AAAA-MM-DD", read_only=True, expand=True)
        self.btn_abrir_data_recebimento = ft.IconButton(icon="CALENDAR_MONTH", tooltip="Selecionar Data Recebimento", on_click=lambda e: self.open_datepicker(self.date_picker_recebimento))
        self.modal_txt_data_validade = ft.TextField(label="Prazo Empenho", hint_text="AAAA-MM-DD", read_only=True, expand=True)
        self.btn_abrir_data_validade = ft.IconButton(icon="CALENDAR_MONTH", tooltip="Selecionar Prazo Empenho", on_click=lambda e: self.open_datepicker(self.date_picker_validade))
        self.date_picker_recebimento = ft.DatePicker(on_change=self.handle_date_recebimento_change, first_date=datetime(2020, 1, 1), last_date=datetime(2030, 12, 31))
        self.date_picker_validade = ft.DatePicker(on_change=self.handle_date_validade_change, first_date=datetime(2020, 1, 1), last_date=datetime(2030, 12, 31))
        self.modal_txt_valor_inicial = ft.TextField(label="Valor Inicial", prefix="R$", on_change=self.format_currency_input, keyboard_type=ft.KeyboardType.NUMBER)
        self.modal_txt_ptres = ft.TextField(label="PTRES", width=150)
        self.modal_txt_nd = ft.TextField(label="Natureza Despesa (ND)", width=150)
        self.modal_txt_fonte = ft.TextField(label="Fonte", width=150)
        self.modal_txt_pi = ft.TextField(label="PI", width=150)
        self.modal_txt_ug_gestora = ft.TextField(label="UG Gestora", width=150)
        self.modal_txt_observacao = ft.TextField(label="Observação (Opcional)", multiline=True, min_lines=3, max_lines=5)
        self.history_modal_title = ft.Text("Extrato da NC")
        self.history_nes_list = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, height=150)
        self.history_recolhimentos_list = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, height=150)
        self.recolhimento_modal_title = ft.Text("Recolher Saldo da NC")
        self.modal_rec_data = ft.TextField(label="Data do Recolhimento", hint_text="AAAA-MM-DD", autofocus=True)
        self.modal_rec_valor = ft.TextField(label="Valor Recolhido", prefix="R$", on_change=self.format_currency_input, keyboard_type=ft.KeyboardType.NUMBER)
        self.modal_rec_descricao = ft.TextField(label="Descrição (Opcional)")
        self.modal_form_loading_ring = ft.ProgressRing(visible=False, width=24, height=24)
        self.modal_form_btn_cancelar = ft.TextButton("Cancelar", on_click=self.close_modal)
        self.modal_form_btn_salvar = ft.ElevatedButton("Salvar", on_click=self.save_nc, icon="SAVE")
        self.modal_rec_loading_ring = ft.ProgressRing(visible=False, width=24, height=24)
        self.modal_rec_btn_cancelar = ft.TextButton("Cancelar", on_click=self.close_recolhimento_modal)
        self.modal_rec_btn_salvar = ft.ElevatedButton("Confirmar Recolhimento", on_click=self.save_recolhimento, icon="KEYBOARD_RETURN")
        self.modal_form = ft.AlertDialog(modal=True, title=ft.Text("Adicionar Nova Nota de Crédito"), content=ft.Column([self.modal_txt_numero_nc, self.modal_dd_secao, ft.Row([self.modal_txt_data_recebimento, self.btn_abrir_data_recebimento,], spacing=10), ft.Row([self.modal_txt_data_validade, self.btn_abrir_data_validade,], spacing=10), self.modal_txt_valor_inicial, ft.Row([self.modal_txt_ptres, self.modal_txt_nd, self.modal_txt_fonte]), ft.Row([self.modal_txt_pi, self.modal_txt_ug_gestora]), self.modal_txt_observacao,], height=600, width=500, scroll=ft.ScrollMode.ADAPTIVE,), actions=[self.modal_form_loading_ring, self.modal_form_btn_cancelar, self.modal_form_btn_salvar,], actions_alignment=ft.MainAxisAlignment.END,)
        self.history_modal = ft.AlertDialog(modal=True, title=self.history_modal_title, content=ft.Column([ft.Text("Notas de Empenho (NEs) Vinculadas:", weight=ft.FontWeight.BOLD), ft.Container(content=self.history_nes_list, border=ft.border.all(1, "grey300"), border_radius=5, padding=10), ft.Divider(height=10), ft.Text("Recolhimentos de Saldo Vinculados:", weight=ft.FontWeight.BOLD), ft.Container(content=self.history_recolhimentos_list, border=ft.border.all(1, "grey300"), border_radius=5, padding=10),], height=400, width=600,), actions=[ft.TextButton("Fechar", on_click=self.close_history_modal)], actions_alignment=ft.MainAxisAlignment.END,)
        self.recolhimento_modal = ft.AlertDialog(modal=True, title=self.recolhimento_modal_title, content=ft.Column([self.modal_rec_data, self.modal_rec_valor, self.modal_rec_descricao,], height=250, width=400,), actions=[self.modal_rec_loading_ring, self.modal_rec_btn_cancelar, self.modal_rec_btn_salvar,], actions_alignment=ft.MainAxisAlignment.END,)
        self.confirm_delete_nc_dialog = ft.AlertDialog(modal=True, title=ft.Text("Confirmar Exclusão de Nota de Crédito"), content=ft.Text("Atenção!\nTem a certeza de que deseja excluir esta Nota de Crédito?\nTodas as Notas de Empenho e Recolhimentos vinculados também serão excluídos.\nEsta ação não pode ser desfeita."), actions=[ft.TextButton("Cancelar", on_click=lambda e: self.close_confirm_delete_nc(None)), ft.ElevatedButton("Excluir NC", color="white", bgcolor="red", on_click=self.confirm_delete_nc),], actions_alignment=ft.MainAxisAlignment.END,)

        # --- Filtros (Sem alteração) ---
        self.filtro_pesquisa_nc = ft.TextField(label="Pesquisar por Nº NC", hint_text="Digite parte do número...", expand=True, on_submit=self.load_ncs_data_wrapper)
        self.filtro_pi = ft.Dropdown(label="Filtrar por PI", options=[ft.dropdown.Option(text="Carregando...", disabled=True)], expand=True, on_change=self.on_pi_filter_change)
        self.filtro_nd = ft.Dropdown(label="Filtrar por ND", options=[ft.dropdown.Option(text="Carregando...", disabled=True)], expand=True, on_change=self.load_ncs_data_wrapper)
        self.filtro_status = ft.Dropdown(label="Filtrar por Status", options=[ft.dropdown.Option(text="Ativa", key="Ativa"), ft.dropdown.Option(text="Sem Saldo", key="Sem Saldo"), ft.dropdown.Option(text="Vencida", key="Vencida"), ft.dropdown.Option(text="Cancelada", key="Cancelada"),], width=200, on_change=self.load_ncs_data_wrapper)
        self.btn_limpar_filtros = ft.IconButton(icon="CLEAR_ALL", tooltip="Limpar Filtros", on_click=self.limpar_filtros)

        # --- Layout (v1.5) ---
        
        # Card 1: Ações e Filtros
        card_acoes_e_filtros = ft.Card(
            elevation=4,
            content=ft.Container(
                padding=20,
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("Gestão de Notas de Crédito", size=20, weight=ft.FontWeight.W_600),
                                ft.Row(
                                    [
                                        ft.ElevatedButton(
                                            "Adicionar Nova NC", 
                                            icon="ADD", 
                                            on_click=self.open_add_modal
                                        ),
                                        ft.OutlinedButton(
                                            "Importar NC (SIAFI)",
                                            icon="UPLOAD_FILE",
                                            tooltip="Adicionar NC a partir de um PDF do SIAFI",
                                            on_click=self.open_file_picker
                                        )
                                    ],
                                    spacing=10
                                )
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        
                        ft.Divider(),
                        ft.Text("Filtros de Exibição:", weight=ft.FontWeight.BOLD),
                        ft.Row(
                            [
                                self.filtro_pesquisa_nc,
                                self.filtro_status, 
                                self.btn_limpar_filtros,
                                ft.IconButton(
                                    icon="REFRESH", 
                                    on_click=self.load_ncs_data_wrapper, 
                                    tooltip="Recarregar e Aplicar Filtros"
                                ),
                                self.progress_ring,
                            ],
                            alignment=ft.MainAxisAlignment.START
                        ),
                        ft.Row(
                            [
                                self.filtro_pi, 
                                self.filtro_nd
                            ]
                        ),
                    ],
                    spacing=15
                )
            )
        )
        
        # Card 2: Tabela de Dados
        card_tabela_ncs = ft.Card(
            elevation=4,
            expand=True, 
            content=ft.Container(
                padding=20,
                content=ft.Column(
                    [
                        ft.Container(
                            content=self.tabela_ncs,
                            expand=True
                        )
                    ],
                    expand=True
                )
            )
        )

        self.controls = [
            card_acoes_e_filtros,
            card_tabela_ncs
        ]

        self.page.overlay.append(self.modal_form)
        self.page.overlay.append(self.history_modal)
        self.page.overlay.append(self.recolhimento_modal)
        self.page.overlay.append(self.confirm_delete_nc_dialog)
        self.page.overlay.append(self.quick_view_modal) # (v1.5) Adiciona o novo modal
        self.page.overlay.append(self.file_picker_import) 
        self.page.overlay.append(self.date_picker_recebimento) 
        self.page.overlay.append(self.date_picker_validade)   
        
        self.on_mount = self.on_view_mount
        
    def on_view_mount(self, e):
        print("NcsView: Controlo montado. A carregar dados...")
        self.load_secoes_cache() 
        self.load_filter_options()
        self.load_ncs_data()
        
    # --- (INÍCIO DA ATUALIZAÇÃO v1.6) ---
    def open_quick_view_modal(self, e, nc_obj):
        """Abre o modal de 'Quick View' com os dados completos da NC."""
        
        # Calcula o percentual
        valor_ini = float(nc_obj.get('valor_inicial', 0))
        total_emp = float(nc_obj.get('total_empenhado', 0)) 
        if valor_ini > 0:
            percentual_str = f"{(total_emp / valor_ini) * 100:.1f}%"
        else:
            percentual_str = "N/A"
            
        # Formata dados
        data_val_str = datetime.fromisoformat(nc_obj['data_validade_empenho']).strftime('%d/%m/%Y')
        data_rec_str = datetime.fromisoformat(nc_obj['data_recebimento']).strftime('%d/%m/%Y')
        
        # Busca nome da Seção
        secao_id = nc_obj.get('id_secao')
        secao_nome = self.secoes_cache.get(secao_id, "N/A") # Get name from cache
        
        # Preenche os controlos do modal
        self.quick_view_title.value = f"Detalhes: {nc_obj.get('numero_nc')}"
        self.qv_status.value = f"Status: {nc_obj.get('status_calculado')}"
        
        # Info Orçamentária
        self.qv_pi_nd.value = f"PI: {nc_obj.get('pi', 'N/A')}  |  ND: {nc_obj.get('natureza_despesa', 'N/A')}"
        self.qv_ptres_fonte.value = f"PTRES: {nc_obj.get('ptres', 'N/A')}  |  Fonte: {nc_obj.get('fonte', 'N/A')}"
        self.qv_ug_secao.value = f"UG Gestora: {nc_obj.get('ug_gestora', 'N/A')}  |  Seção: {secao_nome}"
        
        # Valores
        self.qv_valor_inicial.value = f"Valor Inicial: {self.formatar_moeda(nc_obj.get('valor_inicial'))}"
        self.qv_saldo.value = f"Saldo Disponível: {self.formatar_moeda(nc_obj.get('saldo_disponivel'))}"
        self.qv_percent_empenhado.value = f"% Empenhado: {percentual_str}"
        
        # Prazos
        self.qv_prazo.value = f"Prazo Empenho: {data_val_str} (Recebido em: {data_rec_str})"
        
        # Observação
        self.qv_observacao.value = nc_obj.get('observacao') or "Nenhuma observação."
        
        self.quick_view_modal.open = True
        self.quick_view_modal.update()
    # --- (FIM DA ATUALIZAÇÃO v1.6) ---

    def close_quick_view_modal(self, e):
        self.quick_view_modal.open = False
        self.page.update()
        
    def show_error(self, message):
        if self.error_modal:
            self.error_modal.show(message)
        else:
            print(f"ERRO CRÍTICO (Modal não encontrado): {message}")
            
    def handle_db_error(self, ex, context=""):
        msg = str(ex)
        print(f"Erro de DB Bruto ({context}): {msg}") 
        
        if "duplicate key value violates unique constraint" in msg and "notas_de_credito_numero_nc_key" in msg:
            self.show_error("Erro: Já existe uma Nota de Crédito com este número (2025NC...).")
        elif "duplicate key value violates unique constraint" in msg:
            self.show_error("Erro: Já existe um registo com este identificador único.")
        elif "fetch failed" in msg or "Connection refused" in msg or "Server disconnected" in msg:
            self.show_error("Erro de Rede: Não foi possível conectar ao banco de dados. Tente atualizar a aba.")
        else:
            self.show_error(f"Erro inesperado ao {context}: {msg}")

    def show_success_snackbar(self, message):
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
            
    def format_currency_input(self, e: ft.ControlEvent):
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
            
    def open_datepicker(self, picker: ft.DatePicker):
        if picker and self.page: 
             if picker not in self.page.overlay:
                 self.page.overlay.append(picker)
                 self.page.update()
             picker.visible = True
             picker.open = True
             self.page.update()

    def handle_date_recebimento_change(self, e):
        selected_date = e.control.value
        self.modal_txt_data_recebimento.value = selected_date.strftime('%Y-%m-%d') if selected_date else ""
        e.control.open = False
        self.modal_txt_data_recebimento.update()

    def handle_date_validade_change(self, e):
        selected_date = e.control.value
        self.modal_txt_data_validade.value = selected_date.strftime('%Y-%m-%d') if selected_date else ""
        e.control.open = False
        self.modal_txt_data_validade.update()

    def open_file_picker(self, e):
        try:
            if self.file_picker_import and self.page:
                if self.file_picker_import not in self.page.overlay:
                    print("A re-adicionar file_picker_import ao overlay...")
                    self.page.overlay.append(self.file_picker_import)
                    self.page.update() 
                
                self.file_picker_import.pick_files(
                    allow_multiple=False,
                    allowed_extensions=["pdf"]
                )
                
                self.page.update() 
            else:
                print("ERRO: file_picker_import ou page não estão disponíveis.")
                self.show_error("Erro: O componente de seleção de ficheiro não foi inicializado.")
        except Exception as ex:
            print(f"Erro em open_file_picker: {ex}")
            traceback.print_exc()
            self.show_error(f"Erro ao tentar abrir diálogo: {ex}")
    
    def load_secoes_cache(self):
        print("NcsView: A carregar cache de seções...")
        try:
            resposta = supabase.table('secoes').select('id, nome').execute()
            if resposta.data:
                self.secoes_cache = {secao['id']: secao['nome'] for secao in resposta.data}
                print("NcsView: Cache de seções carregado.")
        except Exception as ex:
            print("--- ERRO CRÍTICO (TRACEBACK) NO NCS [load_secoes_cache] ---")
            traceback.print_exc()
            self.handle_db_error(ex, "carregar cache de seções")
            
    def load_secoes_para_dropdown(self):
        try:
            self.modal_dd_secao.options.clear()
            self.modal_dd_secao.options.append(ft.dropdown.Option(text="Nenhuma", key=None))
            
            if not self.secoes_cache:
                print("NcsView: Cache de seções vazio, a recarregar...")
                self.load_secoes_cache() 

            for secao_id, secao_nome in self.secoes_cache.items():
                self.modal_dd_secao.options.append(
                    ft.dropdown.Option(text=secao_nome, key=secao_id)
                )
            self.modal_dd_secao.update()
            
        except Exception as ex:
            print(f"Erro ao carregar seções no dropdown: {ex}")
            self.show_error(f"Erro ao carregar seções: {ex}")
            
    def load_filter_options(self, pi_selecionado=None):
        try:
            if pi_selecionado is None:
                print("A carregar opções de filtro (PIs e NDs)...")
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
                print("Opções de filtro iniciais carregadas.")
            else:
                print(f"A carregar NDs para o PI: {pi_selecionado}...")
                self.filtro_nd.disabled = True 
                self.filtro_nd.update()
                nds = supabase.rpc('get_distinct_nds_for_pi', {'p_pi': pi_selecionado}).execute()
                self.filtro_nd.options.clear()
                self.filtro_nd.options.append(ft.dropdown.Option(text="Todas as NDs", key=None))
                if nds.data:
                    for nd in sorted(nds.data):
                         if nd: self.filtro_nd.options.append(ft.dropdown.Option(text=nd, key=nd))
                print("Filtro ND atualizado.")
                
            self.filtro_nd.disabled = False 
            
            if pi_selecionado is None:
                self.update() 
                
        except Exception as ex: 
            print("--- ERRO CRÍTICO (TRACEBACK) NO NCS [load_filter_options] ---")
            traceback.print_exc()
            print("---------------------------------------------------------------")
            
            print(f"Erro ao carregar opções de filtro: {ex}")
            self.handle_db_error(ex, "carregar filtros")
            
    def on_pi_filter_change(self, e):
        pi_val = self.filtro_pi.value if self.filtro_pi.value else None
        self.filtro_nd.value = None 
        self.load_filter_options(pi_selecionado=pi_val) 
        self.load_ncs_data() 

    def limpar_filtros(self, e):
        print("A limpar filtros...")
        self.filtro_pesquisa_nc.value = ""
        self.filtro_status.value = None
        self.filtro_pi.value = None
        self.filtro_nd.value = None
        self.load_filter_options(pi_selecionado=None) 
        self.load_ncs_data() 
        self.page.update() 
        
    def load_ncs_data_wrapper(self, e): 
        self.load_ncs_data()
        
    def load_ncs_data(self):
        print("NCs: A carregar dados com filtros...")
        self.progress_ring.visible = True
        self.page.update()
        
        try:
            # (v1.6) Busca todos os dados para o modal de Quick View
            query = supabase.table('ncs_com_saldos').select(
                'id, numero_nc, pi, natureza_despesa, status_calculado, '
                'valor_inicial, saldo_disponivel, total_empenhado, id_secao, ' 
                'data_validade_empenho, data_recebimento, ptres, fonte, '
                'ug_gestora, observacao'
            )
            
            if self.filtro_pesquisa_nc.value: 
                query = query.ilike('numero_nc', f"%{self.filtro_pesquisa_nc.value}%")
            if self.filtro_status.value: 
                query = query.eq('status_calculado', self.filtro_status.value)
            if self.filtro_pi.value: 
                query = query.eq('pi', self.filtro_pi.value)
            if self.filtro_nd.value: 
                query = query.eq('natureza_despesa', self.filtro_nd.value)
            resposta = query.order('data_recebimento', desc=True).execute()
            
            self.tabela_ncs.rows.clear()
            if resposta.data:
                for nc in resposta.data:
                    
                    self.tabela_ncs.rows.append(
                        ft.DataRow(
                            cells=[
                                # (v1.6) Nº NC como "botão" clicável
                                ft.DataCell(
                                    ft.TextButton(
                                        text=nc.get('numero_nc', ''),
                                        on_click=lambda e, nc_obj=nc: self.open_quick_view_modal(e, nc_obj),
                                        style=ft.ButtonStyle(padding=0)
                                    )
                                ),
                                # (v1.6) Colunas essenciais
                                ft.DataCell(ft.Text(nc.get('pi', ''))),
                                ft.DataCell(ft.Text(nc.get('natureza_despesa', ''))),
                                ft.DataCell(ft.Text(self.formatar_moeda(nc.get('valor_inicial')))),
                                ft.DataCell(ft.Text(self.formatar_moeda(nc.get('saldo_disponivel')), weight=ft.FontWeight.BOLD)),
                                # (v1.6) Ações
                                ft.DataCell(
                                    ft.PopupMenuButton(
                                        icon="MORE_VERT", 
                                        items=[
                                            ft.PopupMenuItem(
                                                text="Editar NC (Detalhes)",
                                                icon="EDIT",
                                                on_click=lambda e, nc_obj=nc: self.open_edit_modal(nc_obj)
                                            ),
                                            ft.PopupMenuItem(
                                                text="Ver Extrato (NEs)",
                                                icon="HISTORY",
                                                on_click=lambda e, nc_obj=nc: self.open_history_modal(nc_obj)
                                            ),
                                            ft.PopupMenuItem(
                                                text="Recolher Saldo",
                                                icon="KEYBOARD_RETURN",
                                                on_click=lambda e, nc_obj=nc: self.open_recolhimento_modal(nc_obj)
                                            ),
                                            ft.PopupMenuItem(), # Divisor
                                            ft.PopupMenuItem(
                                                text="Excluir NC",
                                                icon="DELETE",
                                                on_click=lambda e, nc_obj=nc: self.open_confirm_delete_nc(nc_obj)
                                            ),
                                        ]
                                    )
                                ),
                            ]
                        )
                    )
            else:
                self.tabela_ncs.rows.append(
                    ft.DataRow(cells=[ 
                        ft.DataCell(ft.Text("Nenhuma Nota de Crédito encontrada com estes filtros.", italic=True)), 
                        ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")), 
                        ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")),
                        ft.DataCell(ft.Text("")),
                    ])
                )
            print("NCs: Dados carregados com sucesso.")
            
        except Exception as ex: 
            print("--- ERRO CRÍTICO (TRACEBACK) NO NCS [load_ncs_data] ---")
            traceback.print_exc()
            print("---------------------------------------------------------")
            
            print(f"Erro ao carregar NCs: {ex}")
            self.handle_db_error(ex, "carregar NCs")
            
        finally: 
            self.progress_ring.visible = False
            self.page.update()
        
    def open_add_modal(self, e):
        print("A abrir modal de ADIÇÃO...")
        self.id_sendo_editado = None 
        self.modal_form.title = ft.Text("Adicionar Nova Nota de Crédito")
        self.modal_form_btn_salvar.text = "Salvar"
        self.modal_form_btn_salvar.icon = "SAVE"
        
        self.load_secoes_para_dropdown()
        
        self.modal_txt_numero_nc.value = "" 
        self.modal_txt_data_recebimento.value = ""
        self.modal_txt_data_validade.value = ""
        self.modal_txt_valor_inicial.value = ""
        self.modal_txt_ptres.value = ""
        self.modal_txt_nd.value = ""
        self.modal_txt_fonte.value = ""
        self.modal_txt_pi.value = ""
        self.modal_txt_ug_gestora.value = ""
        self.modal_txt_observacao.value = ""
        self.modal_dd_secao.value = None 
        
        for campo in [self.modal_txt_numero_nc, self.modal_txt_data_recebimento, self.modal_txt_data_validade,
                      self.modal_txt_valor_inicial, self.modal_txt_ptres, self.modal_txt_nd,
                      self.modal_txt_fonte, self.modal_txt_pi, self.modal_txt_ug_gestora,
                      self.modal_txt_observacao, self.modal_dd_secao]: 
            campo.error_text = None
            
        self.modal_form.open = True
        self.page.update()
        self.modal_txt_numero_nc.focus() 

    def open_edit_modal(self, nc_completa):
        print(f"A abrir modal de EDIÇÃO para: {nc_completa['numero_nc']}")
        self.id_sendo_editado = nc_completa['id'] 
        self.modal_form.title = ft.Text(f"Editar NC: {nc_completa['numero_nc']}")
        self.modal_form_btn_salvar.text = "Atualizar"
        self.modal_form_btn_salvar.icon = "UPDATE"
        
        self.load_secoes_para_dropdown()

        numero_nc_sem_prefixo = nc_completa.get('numero_nc', '').upper().replace("2025NC", "")
        self.modal_txt_numero_nc.value = numero_nc_sem_prefixo
        
        self.modal_txt_data_recebimento.value = nc_completa.get('data_recebimento', '')
        self.modal_txt_data_validade.value = nc_completa.get('data_validade_empenho', '')
        self.modal_txt_valor_inicial.value = self.formatar_valor_para_campo(nc_completa.get('valor_inicial'))
        self.modal_txt_ptres.value = nc_completa.get('ptres', '')
        self.modal_txt_nd.value = nc_completa.get('natureza_despesa', '')
        self.modal_txt_fonte.value = nc_completa.get('fonte', '')
        self.modal_txt_pi.value = nc_completa.get('pi', '')
        self.modal_txt_ug_gestora.value = nc_completa.get('ug_gestora', '')
        self.modal_txt_observacao.value = nc_completa.get('observacao', '')
        self.modal_dd_secao.value = nc_completa.get('id_secao') 
        
        for campo in [self.modal_txt_numero_nc, self.modal_txt_data_recebimento, self.modal_txt_data_validade,
                      self.modal_txt_valor_inicial, self.modal_txt_ptres, self.modal_txt_nd,
                      self.modal_txt_fonte, self.modal_txt_pi, self.modal_txt_ug_gestora,
                      self.modal_txt_observacao, self.modal_dd_secao]: 
            campo.error_text = None
            
        self.modal_form.open = True
        self.page.update() 

    def close_modal(self, e):
        self.modal_form.open = False
        self.id_sendo_editado = None 
        self.page.update()

    def save_nc(self, e):
        try:
            print("A validar dados da NC...")
            campos_obrigatorios = [
                self.modal_txt_numero_nc, self.modal_txt_data_recebimento,
                self.modal_txt_data_validade, self.modal_txt_valor_inicial,
                self.modal_txt_ptres, self.modal_txt_nd,
                self.modal_txt_fonte, self.modal_txt_pi, self.modal_txt_ug_gestora
            ]
            has_error = False
            for campo in campos_obrigatorios:
                campo.error_text = None 
                if not campo.value:
                    campo.error_text = "Obrigatório"
                    has_error = True
            
            if not self.modal_txt_numero_nc.value or len(self.modal_txt_numero_nc.value) != 6:
                self.modal_txt_numero_nc.error_text = "Deve ter 6 dígitos"
                has_error = True

            if has_error:
                print("Erro de validação.")
                self.modal_form.update()
                return

            valor_limpo = self.modal_txt_valor_inicial.value.replace(".", "").replace(",", ".")
            numero_formatado = f"2025NC{self.modal_txt_numero_nc.value.strip().upper()}"
            
            dados_para_salvar = {
                "numero_nc": numero_formatado, 
                "data_recebimento": self.modal_txt_data_recebimento.value.strip(),
                "data_validade_empenho": self.modal_txt_data_validade.value.strip(),
                "valor_inicial": float(valor_limpo),
                "ptres": self.modal_txt_ptres.value.strip(),
                "natureza_despesa": self.modal_txt_nd.value.strip(),
                "fonte": self.modal_txt_fonte.value.strip(),
                "pi": self.modal_txt_pi.value.strip(),
                "ug_gestora": self.modal_txt_ug_gestora.value.strip(),
                "observacao": self.modal_txt_observacao.value.strip(),
                "id_secao": self.modal_dd_secao.value, 
            }
        except Exception as ex_validation:
            print(f"Erro na validação de dados: {ex_validation}")
            self.show_error(f"Erro nos dados: {ex_validation}")
            return

        self.modal_form_loading_ring.visible = True
        self.modal_form_btn_cancelar.disabled = True
        self.modal_form_btn_salvar.disabled = True
        self.modal_form.update()

        try:
            if self.id_sendo_editado is None:
                print(f"A inserir nova NC no Supabase como: {numero_formatado}...")
                supabase.table('notas_de_credito').insert(dados_para_salvar).execute()
                msg_sucesso = f"NC {numero_formatado} salva com sucesso!"
            else:
                print(f"A atualizar NC ID: {self.id_sendo_editado} como: {numero_formatado}...")
                supabase.table('notas_de_credito').update(dados_para_salvar).eq('id', self.id_sendo_editado).execute()
                msg_sucesso = f"NC {numero_formatado} atualizada com sucesso!"
            
            print("NC salva com sucesso.")
            self.show_success_snackbar(msg_sucesso)
            
            self.close_modal(None)
            self.load_secoes_cache() 
            self.load_filter_options() 
            self.load_ncs_data() 
            if self.on_data_changed_callback:
                self.on_data_changed_callback(None) 

        except Exception as ex:
            print(f"Erro ao salvar NC: {ex}")
            self.handle_db_error(ex, f"salvar NC {numero_formatado}")
            
        finally:
            self.modal_form_loading_ring.visible = False
            self.modal_form_btn_cancelar.disabled = False
            self.modal_form_btn_salvar.disabled = False
            self.modal_form.update()
                 
    def open_history_modal(self, nc):
        nc_id = nc.get('id')
        nc_numero = nc.get('numero_nc', 'Desconhecido')
        if not nc_id:
             self.show_error("Erro: ID da NC não encontrado para carregar extrato.")
             return
        print(f"A carregar extrato para a NC: {nc_numero} (ID: {nc_id})")
        
        self.history_modal_title.value = f"Extrato: {nc_numero}"
        self.history_nes_list.controls.clear()
        self.history_recolhimentos_list.controls.clear()
        self.history_nes_list.controls.append(ft.ProgressRing())
        self.history_recolhimentos_list.controls.append(ft.ProgressRing())
        self.history_modal.open = True
        self.page.update()
        
        try:
            self.history_nes_list.controls.clear()
            self.history_recolhimentos_list.controls.clear()
            
            resposta_nes = supabase.table('notas_de_empenho').select('*').eq('id_nc', nc_id).order('data_empenho', desc=True).execute()
            if resposta_nes.data:
                for ne in resposta_nes.data:
                    data = datetime.fromisoformat(ne['data_empenho']).strftime('%d/%m/%Y') if ne.get('data_empenho') else '??/??/????'
                    valor = self.formatar_moeda(ne.get('valor_empenhado'))
                    num_ne = ne.get('numero_ne', 'N/A')
                    desc = ne.get('descricao', '')
                    self.history_nes_list.controls.append(ft.Text(f"[{data}] - {num_ne} - {valor} - {desc}"))
            else:
                self.history_nes_list.controls.append(ft.Text("Nenhum empenho registado.", italic=True))
            
            resposta_recolhimentos = supabase.table('recolhimentos_de_saldo').select('*').eq('id_nc', nc_id).order('data_recolhimento', desc=True).execute()
            if resposta_recolhimentos.data:
                for rec in resposta_recolhimentos.data:
                    data = datetime.fromisoformat(rec['data_recolhimento']).strftime('%d/%m/%Y') if rec.get('data_recolhimento') else '??/??/????'
                    valor = self.formatar_moeda(rec.get('valor_recolhido'))
                    desc = rec.get('descricao', '')
                    self.history_recolhimentos_list.controls.append(ft.Text(f"[{data}] - {valor} - {desc}"))
            else:
                self.history_recolhimentos_list.controls.append(ft.Text("Nenhum recolhimento registado.", italic=True))
            
            self.history_modal.update()
            
        except Exception as ex:
            print(f"Erro ao carregar extrato da NC: {ex}")
            self.history_modal.open = False
            self.handle_db_error(ex, "carregar extrato")
            
    def close_history_modal(self, e):
        self.history_modal.open = False
        self.page.update()
        
    def open_recolhimento_modal(self, nc):
        nc_id = nc.get('id')
        nc_numero = nc.get('numero_nc', 'Desconhecido')
        if not nc_id:
             self.show_error("Erro: ID da NC não encontrado para recolhimento.")
             return
        self.id_nc_para_recolhimento = nc_id 
        print(f"A abrir modal de Recolhimento para NC: {nc_numero}")
        self.recolhimento_modal_title.value = f"Recolher Saldo: {nc_numero}"
        self.modal_rec_data.value = ""
        self.modal_rec_valor.value = ""
        self.modal_rec_descricao.value = ""
        self.modal_rec_data.error_text = None
        self.modal_rec_valor.error_text = None
        self.recolhimento_modal.open = True
        self.page.update()
        self.modal_rec_data.focus() 

    def close_recolhimento_modal(self, e):
        self.recolhimento_modal.open = False
        self.id_nc_para_recolhimento = None 
        self.page.update()

    def save_recolhimento(self, e):
        if not self.id_nc_para_recolhimento:
             self.show_error("Erro: Nenhuma NC selecionada para recolhimento.")
             return
             
        try:
            print("A validar dados do Recolhimento...")
            has_error = False
            self.modal_rec_data.error_text = None
            self.modal_rec_valor.error_text = None
            if not self.modal_rec_data.value:
                self.modal_rec_data.error_text = "Obrigatório"
                has_error = True
            if not self.modal_rec_valor.value:
                self.modal_rec_valor.error_text = "Obrigatório"
                has_error = True
            if has_error:
                print("Erro de validação no Recolhimento.")
                self.recolhimento_modal.update()
                return
            
            valor_limpo = self.modal_rec_valor.value.replace(".", "").replace(",", ".")
            dados_para_inserir = {
                "id_nc": self.id_nc_para_recolhimento, 
                "data_recolhimento": self.modal_rec_data.value.strip(),
                "valor_recolhido": float(valor_limpo),
                "descricao": self.modal_rec_descricao.value.strip(),
            }
        except Exception as ex_validation:
            print(f"Erro na validação de dados: {ex_validation}")
            self.show_error(f"Erro nos dados: {ex_validation}")
            return
            
        self.modal_rec_loading_ring.visible = True
        self.modal_rec_btn_cancelar.disabled = True
        self.modal_rec_btn_salvar.disabled = True
        self.recolhimento_modal.update()

        try:
            print("A inserir Recolhimento no Supabase...")
            supabase.table('recolhimentos_de_saldo').insert(dados_para_inserir).execute()
            print("Recolhimento salvo com sucesso.")
            
            self.show_success_snackbar("Recolhimento de saldo registado com sucesso!")
            
            self.close_recolhimento_modal(None)
            self.load_ncs_data() 
            if self.on_data_changed_callback:
                self.on_data_changed_callback(None) 
                
        except Exception as ex:
            print(f"Erro ao salvar Recolhimento: {ex}")
            self.handle_db_error(ex, "salvar recolhimento")
            
        finally:
            self.modal_rec_loading_ring.visible = False
            self.modal_rec_btn_cancelar.disabled = False
            self.modal_rec_btn_salvar.disabled = False
            self.modal_rec_loading_ring.update()
                 
    def open_confirm_delete_nc(self, nc):
        nc_id = nc.get('id')
        nc_numero = nc.get('numero_nc', 'Desconhecida')
        if not nc_id:
             self.show_error("Erro: ID da NC não encontrado para exclusão.")
             return
        print(f"A pedir confirmação para excluir NC: {nc_numero}")
        self.confirm_delete_nc_dialog.data = nc_id 
        self.page.dialog = self.confirm_delete_nc_dialog 
        self.confirm_delete_nc_dialog.open = True
        self.page.update()

    def close_confirm_delete_nc(self, e):
        self.confirm_delete_nc_dialog.open = False
        self.page.update()

    def confirm_delete_nc(self, e):
        id_para_excluir = self.confirm_delete_nc_dialog.data
        if not id_para_excluir:
            self.show_error("Erro: ID da NC para exclusão não encontrado.")
            self.close_confirm_delete_nc(None)
            return

        try:
            print(f"A excluir NC ID: {id_para_excluir}...")
            supabase.table('notas_de_credito').delete().eq('id', id_para_excluir).execute()
            print("NC excluída com sucesso.")
            
            self.show_success_snackbar("Nota de Crédito excluída com sucesso.")
            
            self.close_confirm_delete_nc(None)
            self.load_secoes_cache() 
            self.load_filter_options() 
            self.load_ncs_data() 
            if self.on_data_changed_callback:
                self.on_data_changed_callback(None) 
                
        except Exception as ex:
            print(f"Erro ao excluir NC: {ex}")
            self.handle_db_error(ex, "excluir NC")
            self.close_confirm_delete_nc(None)
            
    def on_file_picker_result(self, e: ft.FilePickerResultEvent):
        if not e.files:
            print("on_file_picker_result: O utilizador cancelou.")
            return

        file_name = e.files[0].name
        print(f"on_file_picker_result: Ficheiro selecionado: {file_name}")

        try:
            upload_url = self.page.get_upload_url(file_name, 60) 
            print(f"on_file_picker_result: URL de upload obtida: {upload_url}")

            upload_list = [
                ft.FilePickerUploadFile(
                    file_name,
                    upload_url,
                    method="PUT" 
                )
            ]

            self.progress_ring.visible = True
            self.page.update()
            print("on_file_picker_result: A iniciar upload...")
            self.file_picker_import.upload(upload_list)

        except Exception as ex:
            print(f"Erro em on_file_picker_result: {ex}")
            traceback.print_exc()
            self.show_error(f"Erro ao iniciar upload: {ex}")
            self.progress_ring.visible = False
            self.page.update()

    def on_upload_progress(self, e: ft.FilePickerUploadEvent):
        if e.error:
            print(f"on_upload_progress: ERRO: {e.error}")
            self.show_error(f"Erro durante o upload: {e.error}")
            self.progress_ring.visible = False
            self.page.update()
            return
        
        if e.progress < 1.0:
            return

        print("on_upload_progress: Upload 100% concluído.")
        
        file_name = e.file_name
        file_path_no_servidor = os.path.join("uploads", file_name)
        
        print(f"on_upload_progress: A processar ficheiro em: {file_path_no_servidor}")
        
        try:
            if not os.path.exists(file_path_no_servidor):
                print(f"Erro: O caminho '{file_path_no_servidor}' não existe no servidor.")
                self.show_error(f"Erro: Ficheiro não encontrado no servidor após upload.")
                return

            dados_extraidos = self._parse_siafi_pdf(file_path_no_servidor) 
            
            if dados_extraidos:
                print("Dados extraídos com sucesso.")
                self.preencher_modal_com_dados(dados_extraidos)
            else:
                self.show_error("Não foi possível extrair dados do PDF. Verifique o console.")
                
        except Exception as ex:
            print(f"Erro ao processar o PDF pós-upload: {ex}")
            traceback.print_exc()
            self.show_error(f"Erro ao ler o ficheiro PDF: {ex}")
        
        finally: 
            self.progress_ring.visible = False
            self.page.update()

    def _parse_siafi_pdf(self, file_path_or_object): 
        texto_completo = ""
        
        with pdfplumber.open(file_path_or_object) as pdf:
            primeira_pagina = pdf.pages[0]
            texto_completo = primeira_pagina.extract_text(layout=True, x_tolerance=2)

        if not texto_completo:
            print("Erro de parsing: Nenhum texto extraído do PDF.")
            return None

        dados_nc = {}

        mapa_meses = {
            'JAN': '01', 'FEV': '02', 'MAR': '03', 'ABR': '04',
            'MAI': '05', 'JUN': '06', 'JUL': '07', 'AGO': '08',
            'SET': '09', 'OUT': '10', 'NOV': '11', 'DEZ': '12'
        }

        def extrair(padrao, texto, nome_campo):
            match = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
            if match:
                valor = match.group(1).strip()
                valor = valor.replace("\n", " ").replace("\r", "")
                valor = re.sub(r'\s+', ' ', valor)
                print(f"Campo <{nome_campo}> encontrado: {valor}")
                return valor
            print(f"Padrão RegEx <{nome_campo}> falhou: {padrao}")
            return None
            
        def formatar_data(data_str, ano_base_str=None):
            if not data_str: return None
            data_str = data_str.upper().replace("0", "O")
            data_str = data_str.replace("UT", "OUT") 
            data_str = data_str.replace(".", "") 
            data_str = data_str.replace(" ", "") 
            try:
                dt = datetime.strptime(data_str, '%d%b%y')
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                try:
                    dt = datetime.strptime(data_str, '%d%b')
                    if ano_base_str:
                        ano = ano_base_str[:4]
                        return dt.replace(year=int(ano)).strftime('%Y-%m-%d')
                    else:
                        print(f"Formato de data sem ano, mas ano_base não fornecido: {data_str}")
                        return None
                except ValueError:
                    print(f"Formato de data inválido: {data_str}")
                    return None

        dados_nc['numero_nc'] = extrair(r'NUMERO\s*:\s*(\d{4}NC\d+)', texto_completo, "Número NC")
        data_emissao_str = extrair(r'DATA EMISSAO\s*:\s*(\S+)', texto_completo, "Data Emissão") 
        dados_nc['data_recebimento'] = formatar_data(data_emissao_str)
        obs_match = re.search(r'OBSERVACAO(.*?)(NUM\. TRANSFERENCIA:|LANCADO POR)', texto_completo, re.DOTALL | re.IGNORECASE)
        if obs_match:
            obs_texto_completo = obs_match.group(1).strip()
            obs_limpa = re.sub(r'\s+', ' ', obs_texto_completo.replace("\n", " ")).strip()
            dados_nc['observacao'] = obs_limpa
            print(f"Campo <Observação> encontrado: {obs_limpa}")
            
            if re.search(r'empenho imediato', obs_texto_completo, re.IGNORECASE):
                dados_nc['data_validade'] = dados_nc['data_recebimento']
                print("Campo <Prazo Empenho> encontrado: empenho imediato")
            else:
                prazo_str = extrair(r'EMPH ATÉ\s*([\d\w\.]+)', obs_texto_completo, "Prazo Empenho")
                if prazo_str:
                    dados_nc['data_validade'] = formatar_data(prazo_str, ano_base_str=dados_nc['data_recebimento'])
        else:
            print("Bloco <OBSERVACAO> não encontrado.")

        padrao_tabela = r'300063\s+\S+\s+(\d+)\s+(\d+)\s+(\d+)\s+\S*\s*(\d+)\s+(\S+)\s+([\d.,]+)'
        match_tabela = re.search(padrao_tabela, texto_completo, re.IGNORECASE)
        
        if match_tabela:
            print("Linha de dados da tabela encontrada e processada.")
            dados_nc['ptres'] = match_tabela.group(1)
            dados_nc['fonte'] = match_tabela.group(2)
            dados_nc['nd'] = match_tabela.group(3)
            dados_nc['ug_gestora_tabela'] = match_tabela.group(4)
            dados_nc['pi'] = match_tabela.group(5)
            dados_nc['valor_inicial'] = match_tabela.group(6)
        else:
            print("Padrão RegEx da linha de dados (300063) falhou.")

        ug_emitente = extrair(r'UG EMITENTE\s*:\s*(\d+)', texto_completo, "UG Gestora (Emitente)")
        if ug_emitente:
            dados_nc['ug_gestora'] = ug_emitente
        elif dados_nc.get('ug_gestora_tabela'):
            dados_nc['ug_gestora'] = dados_nc.get('ug_gestora_tabela')
        
        return dados_nc

    def preencher_modal_com_dados(self, dados_nc):
        self.open_add_modal(None)
        
        print("A preencher modal...")
        
        if dados_nc.get('numero_nc'):
            self.modal_txt_numero_nc.value = dados_nc['numero_nc'].upper().replace("2025NC", "")
            
        if dados_nc.get('data_recebimento'):
            self.modal_txt_data_recebimento.value = dados_nc['data_recebimento']
        if dados_nc.get('data_validade'):
            self.modal_txt_data_validade.value = dados_nc['data_validade']
            
        if dados_nc.get('valor_inicial'):
            valor_pdf_limpo = dados_nc['valor_inicial'].replace(".", "").replace(",", "")
            self.modal_txt_valor_inicial.value = valor_pdf_limpo
            self.format_currency_input(ft.ControlEvent(target=self.modal_txt_valor_inicial, name="change", data=valor_pdf_limpo, control=self.modal_txt_valor_inicial, page=self.page))
            
        if dados_nc.get('ptres'):
            self.modal_txt_ptres.value = dados_nc['ptres']
        if dados_nc.get('nd'):
            self.modal_txt_nd.value = dados_nc['nd']
        if dados_nc.get('fonte'):
            self.modal_txt_fonte.value = dados_nc['fonte']
        if dados_nc.get('pi'):
            self.modal_txt_pi.value = dados_nc['pi']
        if dados_nc.get('ug_gestora'):
            self.modal_txt_ug_gestora.value = dados_nc['ug_gestora']
        if dados_nc.get('observacao'):
            self.modal_txt_observacao.value = dados_nc['observacao']
            
        self.modal_txt_numero_nc.focus()
        self.page.update()
                 
# --- Função de Nível Superior (Obrigatória) ---
def create_ncs_view(page: ft.Page, on_data_changed=None, error_modal=None): 
    """
    Exporta a nossa NcsView como um controlo Flet padrão.
    """
    return NcsView(page, on_data_changed=on_data_changed, error_modal=error_modal)