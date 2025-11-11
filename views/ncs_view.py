# views/ncs_view.py
# (Versão 14.0 - Adiciona DatePickers, campo Observação, e corrige layout)

import flet as ft
from supabase_client import supabase # Cliente 'anon'
from datetime import datetime

# --- IMPORTAÇÕES PARA PDF ---
import pdfplumber
import re
# ----------------------------

class NcsView(ft.Column):
    """
    Representa o conteúdo da aba Notas de Crédito (CRUD).
    Versão 14.0: Adiciona DatePickers e campo Observação.
    """
    
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.id_sendo_editado = None
        self.id_nc_para_recolhimento = None
        
        self.alignment = ft.MainAxisAlignment.START
        self.spacing = 20
        self.padding = 20
        
        self.progress_ring = ft.ProgressRing(visible=True, width=32, height=32)
        
        self.file_picker_import = ft.FilePicker(
            on_result=self.on_file_picker_result
        )
        
        self.tabela_ncs = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Número NC", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("PI", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("ND", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Status", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Valor Inicial", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Saldo", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Prazo Empenho", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Ações", weight=ft.FontWeight.BOLD)),
            ], rows=[], expand=True, border=ft.border.all(1, "grey200"), border_radius=8,
        )

        # --- Modais: Controlos (V14) ---
        self.modal_txt_numero_nc = ft.TextField(label="Número NC", hint_text="Ex: 2025NC000123")
        
        # --- ATUALIZAÇÃO: Campos de Data com DatePicker (como em relatorios_view.py) ---
        self.modal_txt_data_recebimento = ft.TextField(label="Data Recebimento", hint_text="AAAA-MM-DD", read_only=True, expand=True)
        self.btn_abrir_data_recebimento = ft.IconButton(
            icon="CALENDAR_MONTH", 
            tooltip="Selecionar Data Recebimento", 
            on_click=lambda e: self.open_datepicker(self.date_picker_recebimento)
        )
        self.modal_txt_data_validade = ft.TextField(label="Prazo Empenho", hint_text="AAAA-MM-DD", read_only=True, expand=True)
        self.btn_abrir_data_validade = ft.IconButton(
            icon="CALENDAR_MONTH", 
            tooltip="Selecionar Prazo Empenho", 
            on_click=lambda e: self.open_datepicker(self.date_picker_validade)
        )
        
        self.date_picker_recebimento = ft.DatePicker(
            on_change=self.handle_date_recebimento_change,
            first_date=datetime(2020, 1, 1),
            last_date=datetime(2030, 12, 31)
        )
        self.date_picker_validade = ft.DatePicker(
            on_change=self.handle_date_validade_change,
            first_date=datetime(2020, 1, 1),
            last_date=datetime(2030, 12, 31)
        )
        # --- FIM DA ATUALIZAÇÃO DE DATA ---
        
        self.modal_txt_valor_inicial = ft.TextField(label="Valor Inicial", prefix="R$", input_filter=ft.InputFilter(r"[0-9.,]"))
        self.modal_txt_ptres = ft.TextField(label="PTRES", width=150)
        self.modal_txt_nd = ft.TextField(label="Natureza Despesa (ND)", width=150)
        self.modal_txt_fonte = ft.TextField(label="Fonte", width=150)
        self.modal_txt_pi = ft.TextField(label="PI", width=150)
        self.modal_txt_ug_gestora = ft.TextField(label="UG Gestora", width=150)
        
        # --- NOVO CAMPO: Observação ---
        self.modal_txt_observacao = ft.TextField(
            label="Observação (Opcional)", 
            multiline=True, 
            min_lines=3, 
            max_lines=5
        )
        # ---------------------------------
        
        self.history_modal_title = ft.Text("Extrato da NC")
        self.history_nes_list = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, height=150)
        self.history_recolhimentos_list = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, height=150)
        
        self.recolhimento_modal_title = ft.Text("Recolher Saldo da NC")
        self.modal_rec_data = ft.TextField(label="Data do Recolhimento", hint_text="AAAA-MM-DD", autofocus=True)
        self.modal_rec_valor = ft.TextField(label="Valor Recolhido", prefix="R$", input_filter=ft.InputFilter(r"[0-9.,]"))
        self.modal_rec_descricao = ft.TextField(label="Descrição (Opcional)")

        # --- Modais: Definições (Layout V14) ---
        self.modal_form = ft.AlertDialog(
            modal=True, title=ft.Text("Adicionar Nova Nota de Crédito"),
            content=ft.Column(
                [
                    self.modal_txt_numero_nc,
                    # --- ATUALIZAÇÃO DE LAYOUT (para corrigir a imagem) ---
                    ft.Row(
                        [
                            self.modal_txt_data_recebimento, 
                            self.btn_abrir_data_recebimento,
                        ], 
                        spacing=10
                    ),
                    ft.Row(
                        [
                            self.modal_txt_data_validade,
                            self.btn_abrir_data_validade,
                        ],
                        spacing=10
                    ),
                    # --- FIM DA ATUALIZAÇÃO DE LAYOUT ---
                    self.modal_txt_valor_inicial,
                    ft.Row([self.modal_txt_ptres, self.modal_txt_nd, self.modal_txt_fonte]),
                    ft.Row([self.modal_txt_pi, self.modal_txt_ug_gestora]),
                    self.modal_txt_observacao, # <-- ADICIONADO
                ], 
                # Altura aumentada para caber o novo campo
                height=550, 
                width=500, 
                scroll=ft.ScrollMode.ADAPTIVE,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self.close_modal),
                ft.ElevatedButton("Salvar", on_click=self.save_nc, icon="SAVE"),
            ], actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.history_modal = ft.AlertDialog(
            modal=True, title=self.history_modal_title,
            content=ft.Column(
                [
                    ft.Text("Notas de Empenho (NEs) Vinculadas:", weight=ft.FontWeight.BOLD),
                    ft.Container(content=self.history_nes_list, border=ft.border.all(1, "grey300"), border_radius=5, padding=10),
                    ft.Divider(height=10),
                    ft.Text("Recolhimentos de Saldo Vinculados:", weight=ft.FontWeight.BOLD),
                    ft.Container(content=self.history_recolhimentos_list, border=ft.border.all(1, "grey300"), border_radius=5, padding=10),
                ], height=400, width=600,
            ),
            actions=[ft.TextButton("Fechar", on_click=self.close_history_modal)], actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.recolhimento_modal = ft.AlertDialog(
            modal=True, title=self.recolhimento_modal_title,
            content=ft.Column(
                [
                    self.modal_rec_data,
                    self.modal_rec_valor,
                    self.modal_rec_descricao,
                ], height=250, width=400,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self.close_recolhimento_modal),
                ft.ElevatedButton("Confirmar Recolhimento", on_click=self.save_recolhimento, icon="KEYBOARD_RETURN"),
            ], actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.confirm_delete_nc_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar Exclusão de Nota de Crédito"),
            content=ft.Text("Atenção!\nTem a certeza de que deseja excluir esta Nota de Crédito?\nTodas as Notas de Empenho e Recolhimentos vinculados também serão excluídos.\nEsta ação não pode ser desfeita."),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.close_confirm_delete_nc(None)),
                ft.ElevatedButton("Excluir NC", color="white", bgcolor="red", on_click=self.confirm_delete_nc),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        # --- Filtros (Inalterados) ---
        self.filtro_pesquisa_nc = ft.TextField(label="Pesquisar por Nº NC", hint_text="Digite parte do número...", expand=True, on_submit=self.load_ncs_data_wrapper)
        self.filtro_pi = ft.Dropdown(label="Filtrar por PI", options=[ft.dropdown.Option(text="Carregando...", disabled=True)], expand=True, on_change=self.on_pi_filter_change)
        self.filtro_nd = ft.Dropdown(label="Filtrar por ND", options=[ft.dropdown.Option(text="Carregando...", disabled=True)], expand=True, on_change=self.load_ncs_data_wrapper)
        self.filtro_status = ft.Dropdown(label="Filtrar por Status", options=[ft.dropdown.Option(text="Ativa", key="Ativa"), ft.dropdown.Option(text="Sem Saldo", key="Sem Saldo"), ft.dropdown.Option(text="Vencida", key="Vencida"), ft.dropdown.Option(text="Cancelada", key="Cancelada"),], width=200, on_change=self.load_ncs_data_wrapper)
        self.btn_limpar_filtros = ft.IconButton(icon="CLEAR_ALL", tooltip="Limpar Filtros", on_click=self.limpar_filtros)

        # --- Layout da Página (Inalterado) ---
        self.controls = [
            ft.Row(
                [
                    ft.Text("Gestão de Notas de Crédito", size=20, weight=ft.FontWeight.W_600),
                    ft.Row([
                        ft.IconButton(icon="REFRESH", on_click=self.load_ncs_data_wrapper, tooltip="Recarregar e Aplicar Filtros"),
                        self.progress_ring,
                    ])
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            
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
                        on_click=lambda _: self.file_picker_import.pick_files(
                            allow_multiple=False,
                            allowed_extensions=["pdf"]
                        )
                    )
                ],
                spacing=20
            ),
            
            ft.Row([ self.filtro_pesquisa_nc, self.filtro_status, self.btn_limpar_filtros ]),
            ft.Row([ self.filtro_pi, self.filtro_nd ]),
            ft.Divider(),
            ft.Container( content=self.tabela_ncs, expand=True )
        ]

        # --- Overlay (COM OS NOVOS DATE PICKERS) ---
        self.page.overlay.append(self.modal_form)
        self.page.overlay.append(self.history_modal)
        self.page.overlay.append(self.recolhimento_modal)
        self.page.overlay.append(self.confirm_delete_nc_dialog)
        self.page.overlay.append(self.file_picker_import) 
        self.page.overlay.append(self.date_picker_recebimento) # <-- ADICIONADO
        self.page.overlay.append(self.date_picker_validade)   # <-- ADICIONADO
        
        self.load_filter_options()
        self.load_ncs_data()
        
        # -----------------------------------------------------------------
    # INÍCIO DO BLOCO DE MÉTODOS (Tudo indentado dentro da classe)
    # -----------------------------------------------------------------

    def show_snackbar(self, message, color="red"):
        self.page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor=color)
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
            
    # --- NOVAS FUNÇÕES DE DATE PICKER (V14) ---
    def open_datepicker(self, picker: ft.DatePicker):
        """Abre o DatePicker (copiado de relatorios_view.py)."""
        if picker and self.page: 
             if picker not in self.page.overlay:
                 self.page.overlay.append(picker)
                 self.page.update()
             picker.visible = True
             picker.open = True
             self.page.update()

    def handle_date_recebimento_change(self, e):
        """Define o valor do campo Data Recebimento."""
        selected_date = e.control.value
        self.modal_txt_data_recebimento.value = selected_date.strftime('%Y-%m-%d') if selected_date else ""
        e.control.open = False
        self.modal_txt_data_recebimento.update()

    def handle_date_validade_change(self, e):
        """Define o valor do campo Prazo Empenho."""
        selected_date = e.control.value
        self.modal_txt_data_validade.value = selected_date.strftime('%Y-%m-%d') if selected_date else ""
        e.control.open = False
        self.modal_txt_data_validade.update()
    # --- FIM DAS NOVAS FUNÇÕES ---
        
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
            self.update() 
        except Exception as ex: 
            print(f"Erro ao carregar opções de filtro: {ex}")
            self.show_snackbar(f"Erro ao carregar filtros: {ex}")
            
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
            # SQL V14: Seleciona a 'observacao'
            query = supabase.table('ncs_com_saldos').select('id, numero_nc, pi, natureza_despesa, status_calculado, valor_inicial, saldo_disponivel, data_validade_empenho, data_recebimento, ptres, fonte, ug_gestora, observacao')
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
                    data_val = datetime.fromisoformat(nc['data_validade_empenho']).strftime('%d/%m/%Y')
                    self.tabela_ncs.rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(nc.get('numero_nc', ''))),
                                ft.DataCell(ft.Text(nc.get('pi', ''))),
                                ft.DataCell(ft.Text(nc.get('natureza_despesa', ''))),
                                ft.DataCell(ft.Text(nc.get('status_calculado', ''))),
                                ft.DataCell(ft.Text(self.formatar_moeda(nc.get('valor_inicial')))),
                                ft.DataCell(ft.Text(self.formatar_moeda(nc.get('saldo_disponivel')), weight=ft.FontWeight.BOLD)),
                                ft.DataCell(ft.Text(data_val)),
                                ft.DataCell(
                                    ft.Row([
                                        ft.IconButton(icon="HISTORY", tooltip="Ver Extrato", on_click=lambda e, nc_obj=nc: self.open_history_modal(nc_obj)),
                                        ft.IconButton(icon="EDIT", tooltip="Editar NC", icon_color="blue700", on_click=lambda e, nc_obj=nc: self.open_edit_modal(nc_obj)),
                                        ft.IconButton(icon="KEYBOARD_RETURN", tooltip="Recolher Saldo", icon_color="orange700", on_click=lambda e, nc_obj=nc: self.open_recolhimento_modal(nc_obj)),
                                        ft.IconButton(icon="DELETE", tooltip="Excluir NC", icon_color="red700", on_click=lambda e, nc_obj=nc: self.open_confirm_delete_nc(nc_obj)),
                                    ])
                                ),
                            ]
                        )
                    )
            else:
                self.tabela_ncs.rows.append(
                    ft.DataRow(cells=[ ft.DataCell(ft.Text("Nenhuma Nota de Crédito encontrada com estes filtros.", italic=True)), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")), ])
                )
            print("NCs: Dados carregados com sucesso.")
        except Exception as ex: print(f"Erro ao carregar NCs: {ex}"); self.show_snackbar(f"Erro ao carregar NCs: {ex}")
        self.progress_ring.visible = False; self.page.update()
        
    def open_add_modal(self, e):
        print("A abrir modal de ADIÇÃO...")
        self.id_sendo_editado = None 
        self.modal_form.title = ft.Text("Adicionar Nova Nota de Crédito")
        if len(self.modal_form.actions) > 1:
            self.modal_form.actions[1].text = "Salvar"
            self.modal_form.actions[1].icon = "SAVE"
        
        # Limpa todos os campos (incluindo o novo)
        self.modal_txt_numero_nc.value = ""
        self.modal_txt_data_recebimento.value = ""
        self.modal_txt_data_validade.value = ""
        self.modal_txt_valor_inicial.value = ""
        self.modal_txt_ptres.value = ""
        self.modal_txt_nd.value = ""
        self.modal_txt_fonte.value = ""
        self.modal_txt_pi.value = ""
        self.modal_txt_ug_gestora.value = ""
        self.modal_txt_observacao.value = "" # <-- ADICIONADO
        
        for campo in [self.modal_txt_numero_nc, self.modal_txt_data_recebimento, self.modal_txt_data_validade,
                      self.modal_txt_valor_inicial, self.modal_txt_ptres, self.modal_txt_nd,
                      self.modal_txt_fonte, self.modal_txt_pi, self.modal_txt_ug_gestora,
                      self.modal_txt_observacao]: # <-- ADICIONADO
            campo.error_text = None
            
        self.modal_form.open = True
        self.page.update()
        self.modal_txt_numero_nc.focus() 

    def open_edit_modal(self, nc):
        print(f"A abrir modal de EDIÇÃO para: {nc['numero_nc']}")
        self.id_sendo_editado = nc['id'] 
        self.modal_form.title = ft.Text(f"Editar NC: {nc['numero_nc']}")
        if len(self.modal_form.actions) > 1:
            self.modal_form.actions[1].text = "Atualizar"
            self.modal_form.actions[1].icon = "UPDATE"

        # Preenche todos os campos (incluindo o novo)
        self.modal_txt_numero_nc.value = nc.get('numero_nc', '')
        self.modal_txt_data_recebimento.value = nc.get('data_recebimento', '')
        self.modal_txt_data_validade.value = nc.get('data_validade_empenho', '')
        self.modal_txt_valor_inicial.value = self.formatar_valor_para_campo(nc.get('valor_inicial'))
        self.modal_txt_ptres.value = nc.get('ptres', '')
        self.modal_txt_nd.value = nc.get('natureza_despesa', '')
        self.modal_txt_fonte.value = nc.get('fonte', '')
        self.modal_txt_pi.value = nc.get('pi', '')
        self.modal_txt_ug_gestora.value = nc.get('ug_gestora', '')
        self.modal_txt_observacao.value = nc.get('observacao', '') # <-- ADICIONADO
        
        for campo in [self.modal_txt_numero_nc, self.modal_txt_data_recebimento, self.modal_txt_data_validade,
                      self.modal_txt_valor_inicial, self.modal_txt_ptres, self.modal_txt_nd,
                      self.modal_txt_fonte, self.modal_txt_pi, self.modal_txt_ug_gestora,
                      self.modal_txt_observacao]: # <-- ADICIONADO
            campo.error_text = None
            
        self.modal_form.open = True
        self.page.update() 

    def close_modal(self, e):
        self.modal_form.open = False
        self.id_sendo_editado = None 
        self.page.update()

    def save_nc(self, e):
        """ Salva (INSERT) ou Atualiza (UPDATE) uma NC (V14). """
        try:
            print("A validar dados da NC...")
            # 'observacao' não é obrigatório
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
            
            if has_error:
                print("Erro de validação.")
                self.modal_form.update()
                return

            valor_limpo = self.modal_txt_valor_inicial.value.replace(".", "").replace(",", ".")
            
            # Prepara os dados (com o novo campo)
            dados_para_salvar = {
                "numero_nc": self.modal_txt_numero_nc.value.strip(),
                "data_recebimento": self.modal_txt_data_recebimento.value.strip(),
                "data_validade_empenho": self.modal_txt_data_validade.value.strip(),
                "valor_inicial": float(valor_limpo),
                "ptres": self.modal_txt_ptres.value.strip(),
                "natureza_despesa": self.modal_txt_nd.value.strip(),
                "fonte": self.modal_txt_fonte.value.strip(),
                "pi": self.modal_txt_pi.value.strip(),
                "ug_gestora": self.modal_txt_ug_gestora.value.strip(),
                "observacao": self.modal_txt_observacao.value.strip() # <-- ADICIONADO
            }

            if self.id_sendo_editado is None:
                print("A inserir nova NC no Supabase...")
                supabase.table('notas_de_credito').insert(dados_para_salvar).execute()
                print("NC salva com sucesso.")
                self.show_snackbar(f"NC {dados_para_salvar['numero_nc']} salva com sucesso!", "green")
            else:
                print(f"A atualizar NC ID: {self.id_sendo_editado}...")
                supabase.table('notas_de_credito').update(dados_para_salvar).eq('id', self.id_sendo_editado).execute()
                print("NC atualizada com sucesso.")
                self.show_snackbar(f"NC {dados_para_salvar['numero_nc']} atualizada com sucesso!", "green")
            
            self.close_modal(None)
            self.load_filter_options() 
            self.load_ncs_data() 

        except Exception as ex:
            print(f"Erro ao salvar NC: {ex}")
            self.show_snackbar(f"Erro ao salvar: {ex}")
            self.modal_form.update()
                 
    def open_history_modal(self, nc):
        nc_id = nc.get('id')
        nc_numero = nc.get('numero_nc', 'Desconhecido')
        if not nc_id:
             self.show_snackbar("Erro: ID da NC não encontrado para carregar extrato.")
             return
        print(f"A carregar extrato para a NC: {nc_numero} (ID: {nc_id})")
        try:
            self.history_modal_title.value = f"Extrato: {nc_numero}"
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
            self.history_modal.open = True
            self.page.update()
        except Exception as ex:
            print(f"Erro ao carregar extrato da NC: {ex}")
            self.show_snackbar(f"Erro ao carregar extrato: {ex}")
            
    def close_history_modal(self, e):
        self.history_modal.open = False
        self.page.update()
        
    def open_recolhimento_modal(self, nc):
        nc_id = nc.get('id')
        nc_numero = nc.get('numero_nc', 'Desconhecido')
        if not nc_id:
             self.show_snackbar("Erro: ID da NC não encontrado para recolhimento.")
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
             self.show_snackbar("Erro: Nenhuma NC selecionada para recolhimento.")
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
            print("A inserir Recolhimento no Supabase...")
            supabase.table('recolhimentos_de_saldo').insert(dados_para_inserir).execute()
            print("Recolhimento salvo com sucesso.")
            self.show_snackbar("Recolhimento de saldo registado com sucesso!", "green")
            self.close_recolhimento_modal(None)
            self.load_ncs_data() 
        except Exception as ex:
            print(f"Erro ao salvar Recolhimento: {ex}")
            self.show_snackbar(f"Erro ao salvar Recolhimento: {ex}")
            self.recolhimento_modal.update()
                 
    def open_confirm_delete_nc(self, nc):
        nc_id = nc.get('id')
        nc_numero = nc.get('numero_nc', 'Desconhecida')
        if not nc_id:
             self.show_snackbar("Erro: ID da NC não encontrado para exclusão.")
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
        try:
            id_para_excluir = self.confirm_delete_nc_dialog.data
            if not id_para_excluir:
                self.show_snackbar("Erro: ID da NC para exclusão não encontrado.")
                self.close_confirm_delete_nc(None)
                return
            print(f"A excluir NC ID: {id_para_excluir}...")
            supabase.table('notas_de_credito').delete().eq('id', id_para_excluir).execute()
            print("NC excluída com sucesso.")
            self.show_snackbar("Nota de Crédito excluída com sucesso.", "green")
            self.close_confirm_delete_nc(None)
            self.load_filter_options() 
            self.load_ncs_data() 
        except Exception as ex:
            print(f"Erro ao excluir NC: {ex}")
            self.show_snackbar(f"Erro ao excluir NC: {ex}")
            self.close_confirm_delete_nc(None)
            
            # --- FUNÇÕES DE IMPORTAÇÃO DE PDF (V14 - Adiciona Observação) ---

    def on_file_picker_result(self, e: ft.FilePickerResultEvent):
        """
        Chamado quando o utilizador seleciona um ficheiro PDF para importar.
        """
        if e.files:
            file_path = e.files[0].path
            print(f"A processar ficheiro PDF: {file_path}")
            self.progress_ring.visible = True
            self.update()
            
            try:
                dados_extraidos = self._parse_siafi_pdf(file_path)
                
                if dados_extraidos:
                    print(f"Dados extraídos com sucesso: {dados_extraidos}")
                    self.preencher_modal_com_dados(dados_extraidos)
                else:
                    self.show_snackbar("Não foi possível extrair dados do PDF. Verifique o console.")
                    
            except Exception as ex:
                print(f"Erro ao processar o PDF: {ex}")
                import traceback
                traceback.print_exc()
                self.show_snackbar(f"Erro ao ler o ficheiro PDF: {ex}")
            
            self.progress_ring.visible = False
            self.update()

    def _parse_siafi_pdf(self, file_path: str):
        """
        Abre o PDF e extrai os campos da NC usando pdfplumber e RegEx.
        (V13 - Lógica de data corrigida)
        """
        texto_completo = ""
        
        with pdfplumber.open(file_path) as pdf:
            primeira_pagina = pdf.pages[0]
            texto_completo = primeira_pagina.extract_text(layout=True, x_tolerance=2)

        if not texto_completo:
            print("Erro de parsing: Nenhum texto extraído do PDF.")
            return None

        dados_nc = {}

        # MAPA DE MESES
        mapa_meses = {
            'JAN': '01', 'FEV': '02', 'MAR': '03', 'ABR': '04',
            'MAI': '05', 'JUN': '06', 'JUL': '07', 'AGO': '08',
            'SET': '09', 'OUT': '10', 'NOV': '11', 'DEZ': '12'
        }

        def extrair(padrao, texto, nome_campo):
            """Função ajudante para RegEx com logging."""
            match = re.search(padrao, texto, re.IGNORECASE | re.DOTALL)
            if match:
                valor = match.group(1).strip()
                valor = valor.replace("\n", " ").replace("\r", "")
                # Remove múltiplos espaços
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
                dt = datetime.strptime(data_str, '%d%b%y') # ex: '17OUT25'
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                try:
                    dt = datetime.strptime(data_str, '%d%b') # ex: '31OUT'
                    if ano_base_str:
                        ano = ano_base_str[:4]
                        return dt.replace(year=int(ano)).strftime('%Y-%m-%d')
                    else:
                        print(f"Formato de data sem ano, mas ano_base não fornecido: {data_str}")
                        return None
                except ValueError:
                    print(f"Formato de data inválido: {data_str}")
                    return None

        # --- Extração dos Campos (V14) ---
        
        # 1. Número da NC
        dados_nc['numero_nc'] = extrair(r'NUMERO\s*:\s*(\d{4}NC\d+)', texto_completo, "Número NC")
        
        # 2. Data Recebimento (Emissão)
        data_emissao_str = extrair(r'DATA EMISSAO\s*:\s*(\S+)', texto_completo, "Data Emissão") 
        dados_nc['data_recebimento'] = formatar_data(data_emissao_str)
        
        # 3. Prazo Empenho (da Observação)
        # 4. Observação (NOVO V14)
        # Captura TUDO entre OBSERVACAO e NUM. TRANSFERENCIA
        obs_match = re.search(r'OBSERVACAO(.*?)(NUM\. TRANSFERENCIA:|LANCADO POR)', texto_completo, re.DOTALL | re.IGNORECASE)
        if obs_match:
            obs_texto_completo = obs_match.group(1).strip()
            # Limpa o texto da observação (remove quebras de linha e espaços extras)
            obs_limpa = re.sub(r'\s+', ' ', obs_texto_completo.replace("\n", " ")).strip()
            dados_nc['observacao'] = obs_limpa
            print(f"Campo <Observação> encontrado: {obs_limpa}")
            
            # Agora procura o prazo DENTRO do texto da observação
            if re.search(r'empenho imediato', obs_texto_completo, re.IGNORECASE):
                dados_nc['data_validade'] = dados_nc['data_recebimento']
                print("Campo <Prazo Empenho> encontrado: empenho imediato")
            else:
                prazo_str = extrair(r'EMPH ATÉ\s*([\d\w\.]+)', obs_texto_completo, "Prazo Empenho")
                if prazo_str:
                    dados_nc['data_validade'] = formatar_data(prazo_str, ano_base_str=dados_nc['data_recebimento'])
        else:
            print("Bloco <OBSERVACAO> não encontrado.")

        # 5. Extração da Tabela (Lógica V12)
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

        # 6. UG Gestora
        ug_emitente = extrair(r'UG EMITENTE\s*:\s*(\d+)', texto_completo, "UG Gestora (Emitente)")
        if ug_emitente:
            dados_nc['ug_gestora'] = ug_emitente
        elif dados_nc.get('ug_gestora_tabela'):
            dados_nc['ug_gestora'] = dados_nc.get('ug_gestora_tabela')
        
        return dados_nc

    def preencher_modal_com_dados(self, dados_nc):
        """
        Abre o modal de Adição e preenche os campos com os dados extraídos.
        (V14 - Adiciona Observação)
        """
        self.open_add_modal(None)
        
        print("A preencher modal...")
        
        if dados_nc.get('numero_nc'):
            self.modal_txt_numero_nc.value = dados_nc['numero_nc']
        if dados_nc.get('data_recebimento'):
            self.modal_txt_data_recebimento.value = dados_nc['data_recebimento']
        if dados_nc.get('data_validade'):
            self.modal_txt_data_validade.value = dados_nc['data_validade']
        if dados_nc.get('valor_inicial'):
            valor_formatado = dados_nc['valor_inicial'].replace(".", "")
            self.modal_txt_valor_inicial.value = valor_formatado
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
            self.modal_txt_observacao.value = dados_nc['observacao'] # <-- ADICIONADO
            
        self.modal_txt_numero_nc.focus()
        self.page.update()
                 
# --- Função de Nível Superior (Obrigatória) ---
def create_ncs_view(page: ft.Page):
    """
    Exporta a nossa NcsView como um controlo Flet padrão.
    """
    return NcsView(page)