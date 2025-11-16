# views/relatorios_view.py
# (Versão Refatorada v1.3 - Layout Moderno)
# (Adiciona scroll vertical à aba)

import flet as ft
from supabase_client import supabase # Cliente 'anon'
from datetime import datetime, date
import pandas as pd
import traceback 
import io       
import os       
import uuid     

# Importações do ReportLab
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT 

class RelatoriosView(ft.Column):
    """
    Representa o conteúdo da aba Relatórios.
    (v1.3) Adiciona scroll vertical.
    """
    
    def __init__(self, page, error_modal=None):
        super().__init__()
        self.page = page
        self.alignment = ft.MainAxisAlignment.START
        self.spacing = 20
        self.error_modal = error_modal
        
        # --- (CORREÇÃO v1.3) ---
        # Adiciona o scroll de volta à coluna principal da view
        self.scroll = ft.ScrollMode.ADAPTIVE
        # --- (FIM DA CORREÇÃO v1.3) ---
        
        self.progress_ring = ft.ProgressRing(visible=False, width=32, height=32)

        # --- Controlos de Download (v8.0 - mantidos) ---
        self.tipo_ficheiro_a_salvar = None 
        self.dados_relatorio_para_salvar = None 
        
        self.download_button_geral = ft.ElevatedButton(
            text="Baixar Relatório", 
            icon="DOWNLOAD",
            visible=False, 
            on_click=lambda e: print("Botão de download geral clicado (URL ainda não definida)")
        )
        self.download_button_extrato = ft.ElevatedButton(
            text="Baixar Extrato", 
            icon="DOWNLOAD",
            visible=False,
            on_click=lambda e: print("Botão de download extrato clicado (URL ainda não definida)")
        )
        # --- Fim dos controlos de Download ---

        # --- Secção: Relatório Geral NCs (Controlos) ---
        self.filtro_data_inicio = ft.TextField(label="Data Início (Receb.)", hint_text="AAAA-MM-DD", width=150, tooltip="Data de recebimento inicial", read_only=True)
        self.filtro_data_fim = ft.TextField(label="Data Fim (Receb.)", hint_text="AAAA-MM-DD", width=150, tooltip="Data de recebimento final", read_only=True)
        self.btn_abrir_data_inicio = ft.IconButton(icon="CALENDAR_MONTH", tooltip="Selecionar Data Início", on_click=lambda e: self.open_datepicker(self.date_picker_inicio))
        self.btn_abrir_data_fim = ft.IconButton(icon="CALENDAR_MONTH", tooltip="Selecionar Data Fim", on_click=lambda e: self.open_datepicker(self.date_picker_fim))
        
        self.date_picker_inicio = ft.DatePicker(on_change=self.handle_start_date_change, first_date=datetime(2020, 1, 1), last_date=datetime(2030, 12, 31))
        self.date_picker_fim = ft.DatePicker(on_change=self.handle_end_date_change, first_date=datetime(2020, 1, 1), last_date=datetime(2030, 12, 31))
        
        self.filtro_pi = ft.Dropdown( label="Filtrar por PI", options=[ft.dropdown.Option(text="Carregando...", disabled=True)], expand=True, on_change=self.on_pi_filter_change )
        self.filtro_nd = ft.Dropdown( label="Filtrar por ND", options=[ft.dropdown.Option(text="Carregando...", disabled=True)], expand=True )
        self.filtro_status = ft.Dropdown( label="Filtrar por Status", options=[ ft.dropdown.Option(text="Todos", key=None), ft.dropdown.Option(text="Ativa", key="Ativa"), ft.dropdown.Option(text="Sem Saldo", key="Sem Saldo"), ft.dropdown.Option(text="Vencida", key="Vencida"), ft.dropdown.Option(text="Cancelada", key="Cancelada"),], width=200 )
        self.btn_limpar_filtros_geral = ft.IconButton(icon="CLEAR_ALL", tooltip="Limpar Filtros (Rel. Geral)", on_click=self.limpar_filtros_geral)

        self.btn_gerar_excel_geral = ft.ElevatedButton("Gerar Excel Geral (.xlsx)", icon="TABLE_CHART", on_click=self.gerar_relatorio_geral_excel)
        self.btn_gerar_pdf_geral = ft.ElevatedButton("Gerar PDF Geral (.pdf)", icon="PICTURE_AS_PDF", on_click=self.gerar_relatorio_geral_pdf)

        # --- Secção: Relatório Individual (Extrato) (Controlos) ---
        self.dropdown_nc_extrato = ft.Dropdown(
            label="Selecione a NC para gerar o Extrato",
            options=[ft.dropdown.Option(text="Carregando...", disabled=True)],
            expand=True
        )
        self.btn_gerar_excel_extrato = ft.ElevatedButton("Gerar Extrato Excel", icon="TABLE_CHART", on_click=self.gerar_extrato_excel)
        self.btn_gerar_pdf_extrato = ft.ElevatedButton("Gerar Extrato PDF", icon="PICTURE_AS_PDF", on_click=self.gerar_extrato_pdf)
        
        
        # --- (INÍCIO DA REFATORAÇÃO VISUAL v1.2) ---
        
        # Card 1: Relatório Geral
        card_relatorio_geral = ft.Card(
            elevation=4,
            content=ft.Container(
                padding=20,
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text("Relatório Geral de Notas de Crédito", size=20, weight=ft.FontWeight.W_600),
                                ft.Row([
                                    ft.IconButton(
                                        icon="REFRESH", 
                                        on_click=self.load_all_filters_wrapper, 
                                        tooltip="Recarregar Listas de Filtros"
                                    ),
                                    self.progress_ring,
                                ])
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Divider(),
                        ft.Text("Filtros (Relatório Geral):", weight=ft.FontWeight.BOLD),
                        ft.Row([ self.filtro_data_inicio, self.btn_abrir_data_inicio, ft.Container(width=20), self.filtro_data_fim, self.btn_abrir_data_fim, ], alignment=ft.MainAxisAlignment.START),
                        ft.Row([self.filtro_pi, self.filtro_nd]),
                        ft.Row([self.filtro_status, self.btn_limpar_filtros_geral], alignment=ft.MainAxisAlignment.START),
                        ft.Row([self.btn_gerar_excel_geral, self.btn_gerar_pdf_geral], alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(self.download_button_geral, alignment=ft.alignment.center),
                    ],
                    spacing=15
                )
            )
        )
        
        # Card 2: Relatório Individual
        card_relatorio_extrato = ft.Card(
            elevation=4,
            content=ft.Container(
                padding=20,
                content=ft.Column(
                    [
                        ft.Text("Relatório Individual (Extrato) por NC", size=20, weight=ft.FontWeight.W_600),
                        ft.Divider(),
                        ft.Row([self.dropdown_nc_extrato]),
                        ft.Row([self.btn_gerar_excel_extrato, self.btn_gerar_pdf_extrato], alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(self.download_button_extrato, alignment=ft.alignment.center),
                    ],
                    spacing=15
                )
            )
        )

        self.controls = [
            card_relatorio_geral,
            card_relatorio_extrato
        ]
        # --- (FIM DA REFATORAÇÃO VISUAL v1.2) ---

        if self.page:
            self.page.overlay.extend([
                self.date_picker_inicio, 
                self.date_picker_fim, 
            ])

        self.on_mount = self.on_view_mount
        
    # -----------------------------------------------------------------
    # O RESTANTE DO FICHEIRO (todas as funções de lógica v8.0)
    # permanece EXATAMENTE IGUAL.
    # -----------------------------------------------------------------
        
    def on_view_mount(self, e):
        print("RelatoriosView: Controlo montado. A carregar dados...")
        self.load_all_filters() 
        
    def show_error(self, message):
        if self.error_modal:
            self.error_modal.show(message)
        else:
            print(f"ERRO CRÍTICO (Modal não encontrado): {message}")
            
    def handle_db_error(self, ex, context=""):
        msg = str(ex)
        print(f"Erro de DB Bruto ({context}): {msg}") 
        if "fetch failed" in msg or "Connection refused" in msg or "Server disconnected" in msg:
            self.show_error("Erro de Rede: Não foi possível conectar ao banco de dados. Tente atualizar a aba.")
        else:
            self.show_error(f"Erro inesperado ao {context}: {msg}")

    def show_success_snackbar(self, message):
        self.page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor="green")
        self.page.snack_bar.open = True
        self.page.update()
             
    def formatar_moeda(self, valor):
        try: val = float(valor); return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, TypeError): return "R$ 0,00"

    def open_datepicker(self, picker: ft.DatePicker):
        if picker and self.page: 
             if picker not in self.page.overlay:
                 self.page.overlay.append(picker)
                 self.page.update() 
             picker.pick_date() 

    def handle_start_date_change(self, e):
        selected_date = e.control.value
        self.filtro_data_inicio.value = selected_date.strftime('%Y-%m-%d') if selected_date else ""
        self.filtro_data_inicio.update() 
        if self.page: self.page.update() 

    def handle_end_date_change(self, e):
        selected_date = e.control.value
        self.filtro_data_fim.value = selected_date.strftime('%Y-%m-%d') if selected_date else ""
        self.filtro_data_fim.update() 
        if self.page: self.page.update() 

    def load_all_filters_wrapper(self, e):
        print("Relatórios: Recarregando todos os filtros...")
        self.progress_ring.visible = True
        self.update() 
        try:
            self.load_all_filters()
            self.show_success_snackbar("Filtros atualizados com sucesso.")
        except Exception as ex:
            print("--- ERRO CRÍTICO (TRACEBACK) NO RELATORIOS [load_all_filters_wrapper] ---")
            traceback.print_exc()
            print("--------------------------------------------------------------------------")
            self.handle_db_error(ex, "recarregar filtros")
        finally: 
            self.progress_ring.visible = False
            self.update() 
        
    def load_all_filters(self):
        self.load_filter_options()
        self.load_nc_list_for_statement_filter()
    
    def load_filter_options(self, pi_selecionado=None):
        try:
            if pi_selecionado is None:
                print("Relatórios: A carregar opções de filtro (PIs e NDs)...")
                pis = supabase.rpc('get_distinct_pis').execute()
                self.filtro_pi.options.clear(); self.filtro_pi.options.append(ft.dropdown.Option(text="Todos os PIs", key=None))
                if pis.data:
                    for pi in sorted(pis.data):
                        if pi: self.filtro_pi.options.append(ft.dropdown.Option(text=pi, key=pi))
                nds = supabase.rpc('get_distinct_nds').execute()
                self.filtro_nd.options.clear(); self.filtro_nd.options.append(ft.dropdown.Option(text="Todas as NDs", key=None))
                if nds.data:
                    for nd in sorted(nds.data):
                        if nd: self.filtro_nd.options.append(ft.dropdown.Option(text=nd, key=nd))
                print("Relatórios: Opções de filtro carregadas.")
            else:
                print(f"Relatórios: A carregar NDs para o PI: {pi_selecionado}...")
                self.filtro_nd.disabled = True; self.filtro_nd.update() 
                nds = supabase.rpc('get_distinct_nds_for_pi', {'p_pi': pi_selecionado}).execute()
                self.filtro_nd.options.clear(); self.filtro_nd.options.append(ft.dropdown.Option(text="Todas as NDs", key=None))
                if nds.data:
                    for nd in sorted(nds.data):
                         if nd: self.filtro_nd.options.append(ft.dropdown.Option(text=nd, key=nd))
                print("Relatórios: Filtro ND atualizado.")
                
            self.filtro_nd.disabled = False
            if pi_selecionado is None:
                self.update() 
        except Exception as ex: 
            print("--- ERRO CRÍTICO (TRACEBACK) NO RELATORIOS [load_filter_options] ---")
            traceback.print_exc()
            print("---------------------------------------------------------------------")
            print(f"Erro ao carregar opções de filtro nos Relatórios: {ex}")
            self.handle_db_error(ex, "carregar filtros de PI/ND")

    def on_pi_filter_change(self, e):
        pi_val = self.filtro_pi.value if self.filtro_pi.value else None
        self.filtro_nd.value = None 
        self.load_filter_options(pi_selecionado=pi_val)

    def limpar_filtros_geral(self, e):
        print("Relatórios: A limpar filtros do Relatório Geral...");
        self.filtro_data_inicio.value = ""; self.filtro_data_fim.value = ""
        self.filtro_pi.value = None; self.filtro_nd.value = None
        self.filtro_status.value = None
        self.download_button_geral.visible = False
        self.load_filter_options(pi_selecionado=None)
        if self.page: self.page.update() 
        
    def fetch_report_data_geral(self, e): 
        print("Relatórios: A buscar dados para Relatório Geral...")
        try:
            query = supabase.table('ncs_com_saldos') \
                           .select('numero_nc, pi, natureza_despesa, status_calculado, valor_inicial, saldo_disponivel, data_validade_empenho, ug_gestora, data_recebimento, observacao') 
            if self.filtro_data_inicio.value: query = query.gte('data_recebimento', self.filtro_data_inicio.value)
            if self.filtro_data_fim.value: query = query.lte('data_recebimento', self.filtro_data_fim.value)
            if self.filtro_status.value: query = query.eq('status_calculado', self.filtro_status.value)
            if self.filtro_pi.value: query = query.eq('pi', self.filtro_pi.value)
            if self.filtro_nd.value: query = query.eq('natureza_despesa', self.filtro_nd.value)
            resposta = query.order('data_recebimento', desc=True).execute()
            
            if resposta.data: 
                print(f"Relatórios: {len(resposta.data)} registos encontrados."); 
                return resposta.data
            else: 
                print("Relatórios: Nenhum registo encontrado.");
                self.page.snack_bar = ft.SnackBar(ft.Text("Nenhum registo encontrado com estes filtros."), bgcolor="orange")
                self.page.snack_bar.open = True
                self.page.update()
                return None
        except Exception as ex: 
            print(f"Erro ao buscar dados (Geral): {ex}"); 
            self.handle_db_error(ex, "buscar dados do Relatório Geral") 
            return None
            
    def fetch_report_data_extrato(self, nc_id):
        if not nc_id: return None
        print(f"Relatórios: A buscar dados para Extrato da NC ID: {nc_id}...")
        try:
            nc_data = supabase.table('notas_de_credito').select('*, observacao').eq('id', nc_id).maybe_single().execute()
            if not nc_data.data: 
                print("NC não encontrada."); 
                self.show_error("NC selecionada não encontrada."); 
                return None
            
            nes_data = supabase.table('notas_de_empenho').select('*').eq('id_nc', nc_id).order('data_empenho', desc=True).execute()
            recolhimentos_data = supabase.table('recolhimentos_de_saldo').select('*').eq('id_nc', nc_id).order('data_recolhimento', desc=True).execute()
            
            print("Dados do Extrato carregados.")
            return { "nc": nc_data.data, "nes": nes_data.data if nes_data.data else [], "recolhimentos": recolhimentos_data.data if recolhimentos_data.data else [] }
        except Exception as ex: 
            print(f"Erro ao buscar dados (Extrato): {ex}"); 
            self.handle_db_error(ex, "buscar dados do Extrato")
            return None
        
    def load_nc_list_for_statement_filter(self):
        print("Relatórios: A carregar NCs para o filtro de Extrato...")
        try:
            resposta_ncs = supabase.table('notas_de_credito') \
                                   .select('id, numero_nc') \
                                   .order('numero_nc', desc=False) \
                                   .execute()

            self.dropdown_nc_extrato.options.clear()
            if not resposta_ncs.data:
                 self.dropdown_nc_extrato.options.append(ft.dropdown.Option(text="Nenhuma NC encontrada", disabled=True))
            else:
                for nc in resposta_ncs.data:
                    self.dropdown_nc_extrato.options.append(
                        ft.dropdown.Option(key=nc['id'], text=nc['numero_nc'])
                    )

            print("Relatórios: Lista de NCs para Extrato carregada.")
            self.update() 
        except Exception as ex:
            print("--- ERRO CRÍTICO (TRACEBACK) NO RELATORIOS [load_nc_list_for_statement_filter] ---")
            traceback.print_exc()
            print("----------------------------------------------------------------------------------")
            print(f"Erro ao carregar NCs para filtro de extrato: {ex}")
            self.handle_db_error(ex, "carregar lista de NCs")
            
    
    # --- LÓGICA DE DOWNLOAD (v8.0 - Mantida) ---
    
    def _executar_download(self, tipo_relatorio, nome_base, dados_para_gerar, button_control_to_update):
        self.progress_ring.visible = True
        button_control_to_update.visible = False 
        self.update()
        
        try:
            self.dados_relatorio_para_salvar = dados_para_gerar
            self.tipo_ficheiro_a_salvar = tipo_relatorio
            
            file_bytes = self._gerar_bytes_do_relatorio()
            
            extensao = "xlsx" if "excel" in tipo_relatorio else "pdf"
            nome_unico = f"{nome_base}_{uuid.uuid4()}.{extensao}"
            
            if not os.path.exists("assets"):
                os.makedirs("assets")
            caminho_servidor = os.path.join("assets", nome_unico)
            
            print(f"A salvar ficheiro público em: {caminho_servidor}")
            with open(caminho_servidor, "wb") as f:
                f.write(file_bytes)
                
            url_download = nome_unico # URL relativa para 'assets/'
            
            button_control_to_update.text = f"Baixar: {nome_unico}"
            button_control_to_update.on_click = lambda e, url=url_download: self.page.launch_url(url)
            button_control_to_update.visible = True
            
            self.show_success_snackbar("Relatório pronto. Clique no botão para baixar.")

        except Exception as e:
            print(f"Erro ao preparar download para {tipo_relatorio}: {e}")
            traceback.print_exc()
            self.show_error(f"Erro ao gerar relatório: {e}")
        
        finally:
            self.dados_relatorio_para_salvar = None
            self.tipo_ficheiro_a_salvar = None
            self.progress_ring.visible = False
            self.update()

    def gerar_relatorio_geral_excel(self, e):
        dados = self.fetch_report_data_geral(e)
        if dados:
            self._executar_download(
                tipo_relatorio="excel_geral",
                nome_base="relatorio_geral_ncs",
                dados_para_gerar=dados,
                button_control_to_update=self.download_button_geral 
            )

    def gerar_relatorio_geral_pdf(self, e):
        dados = self.fetch_report_data_geral(e)
        if dados:
            self._executar_download(
                tipo_relatorio="pdf_geral",
                nome_base="relatorio_geral_ncs",
                dados_para_gerar=dados,
                button_control_to_update=self.download_button_geral
            )

    def gerar_extrato_excel(self, e):
        self.download_button_extrato.visible = False 
        nc_id_selecionada = self.dropdown_nc_extrato.value
        if not nc_id_selecionada: 
            self.page.snack_bar = ft.SnackBar(ft.Text("Selecione uma NC."), bgcolor="orange")
            self.page.snack_bar.open = True; self.page.update()
            return
            
        dados_extrato = self.fetch_report_data_extrato(nc_id_selecionada)
        if dados_extrato:
            nome_base = dados_extrato['nc'].get('numero_nc', 'extrato').replace('/', '_').replace('\\', '_')
            self._executar_download(
                tipo_relatorio="excel_extrato",
                nome_base=f"extrato_{nome_base}",
                dados_para_gerar=dados_extrato,
                button_control_to_update=self.download_button_extrato 
            )

    def gerar_extrato_pdf(self, e):
        self.download_button_extrato.visible = False
        nc_id_selecionada = self.dropdown_nc_extrato.value
        if not nc_id_selecionada: 
            self.page.snack_bar = ft.SnackBar(ft.Text("Selecione uma NC."), bgcolor="orange")
            self.page.snack_bar.open = True; self.page.update()
            return
            
        dados_extrato = self.fetch_report_data_extrato(nc_id_selecionada)
        if dados_extrato:
            nome_base = dados_extrato['nc'].get('numero_nc', 'extrato').replace('/', '_').replace('\\', '_')
            self._executar_download(
                tipo_relatorio="pdf_extrato",
                nome_base=f"extrato_{nome_base}",
                dados_para_gerar=dados_extrato,
                button_control_to_update=self.download_button_extrato
            )

    def _gerar_bytes_do_relatorio(self):
        tipo = self.tipo_ficheiro_a_salvar
        dados = self.dados_relatorio_para_salvar
        
        if not tipo or not dados:
            raise Exception("Dados ou tipo de relatório em falta para gerar bytes.")

        print(f"A gerar bytes para: {tipo}")

        try:
            # --- EXCEL GERAL ---
            if tipo == "excel_geral":
                df = pd.DataFrame(dados)
                df = df.rename(columns={ 'numero_nc': 'Número NC', 'pi': 'PI', 'natureza_despesa': 'ND', 'status_calculado': 'Status', 'valor_inicial': 'Valor Inicial', 'saldo_disponivel': 'Saldo Disponível', 'data_validade_empenho': 'Prazo Empenho', 'ug_gestora': 'UG Gestora', 'data_recebimento': 'Data Recebimento', 'observacao': 'Observação' })
                colunas_relatorio = ['Número NC', 'PI', 'ND', 'Status', 'Valor Inicial', 'Saldo Disponível', 'Prazo Empenho', 'UG Gestora', 'Data Recebimento', 'Observação']
                colunas_existentes = [col for col in colunas_relatorio if col in df.columns]
                df = df[colunas_existentes]
                if 'Data Recebimento' in df.columns: df['Data Recebimento'] = pd.to_datetime(df['Data Recebimento'], errors='coerce').dt.strftime('%d/%m/%Y')
                if 'Prazo Empenho' in df.columns: df['Prazo Empenho'] = pd.to_datetime(df['Prazo Empenho'], errors='coerce').dt.strftime('%d/%m/%Y')
                if 'Valor Inicial' in df.columns: df['Valor Inicial'] = pd.to_numeric(df['Valor Inicial'], errors='coerce').fillna(0)
                if 'Saldo Disponível' in df.columns: df['Saldo Disponível'] = pd.to_numeric(df['Saldo Disponível'], errors='coerce').fillna(0)
                
                with io.BytesIO() as file_in_memory:
                    df.to_excel(file_in_memory, index=False, engine='openpyxl')
                    return file_in_memory.getvalue()

            # --- PDF GERAL ---
            elif tipo == "pdf_geral":
                with io.BytesIO() as file_in_memory:
                    doc = SimpleDocTemplate(file_in_memory, pagesize=landscape(letter)); story = [];
                    styles = getSampleStyleSheet()
                    style_normal = styles['Normal']; style_normal.alignment = TA_LEFT; style_normal.fontSize = 8
                    style_right = ParagraphStyle(name='Right', parent=style_normal, alignment=TA_RIGHT)
                    style_header = ParagraphStyle(name='Header', parent=style_normal, alignment=TA_CENTER, fontName='Helvetica-Bold', textColor=colors.whitesmoke, fontSize=9)
                    style_center = ParagraphStyle(name='Center', parent=style_normal, alignment=TA_CENTER)
                    style_title = styles['Heading1']; style_title.alignment = TA_CENTER
                    
                    story.append(Paragraph("Relatório Geral de Notas de Crédito", style_title)); story.append(Spacer(1, 0.2*inch))
                    filtros_str = "Filtros Aplicados: "; 
                    if self.filtro_data_inicio.value: filtros_str += f"Data Rec. Início: {self.filtro_data_inicio.value}, "; 
                    if self.filtro_data_fim.value: filtros_str += f"Data Rec. Fim: {self.filtro_data_fim.value}, "; 
                    if self.filtro_pi.value: filtros_str += f"PI: {self.filtro_pi.value}, "; 
                    if self.filtro_nd.value: filtros_str += f"ND: {self.filtro_nd.value}, "; 
                    if self.filtro_status.value: filtros_str += f"Status: {self.filtro_status.value}"; 
                    if filtros_str == "Filtros Aplicados: ": filtros_str += "Nenhum"
                    story.append(Paragraph(filtros_str, styles['Normal'])); story.append(Spacer(1, 0.2*inch))
                    
                    header = [Paragraph(h, style_header) for h in ['Número NC', 'PI', 'ND', 'Status', 'Valor Inicial', 'Saldo', 'Prazo Empenho', 'UG Gestora', 'Data Receb.', 'Observação']]
                    pdf_data = [header]
                    
                    for item in dados: 
                        data_rec = datetime.fromisoformat(item.get('data_recebimento', '')).strftime('%d/%m/%Y') if item.get('data_recebimento') else ''
                        prazo_emp = datetime.fromisoformat(item.get('data_validade_empenho', '')).strftime('%d/%m/%Y') if item.get('data_validade_empenho') else ''
                        row = [ 
                            Paragraph(item.get('numero_nc', ''), style_center), 
                            Paragraph(item.get('pi', ''), style_center), 
                            Paragraph(item.get('natureza_despesa', ''), style_center), 
                            Paragraph(item.get('status_calculado', ''), style_center), 
                            Paragraph(self.formatar_moeda(item.get('valor_inicial')), style_right), 
                            Paragraph(self.formatar_moeda(item.get('saldo_disponivel')), style_right), 
                            Paragraph(prazo_emp, style_center), 
                            Paragraph(item.get('ug_gestora', ''), style_center), 
                            Paragraph(data_rec, style_center), 
                            Paragraph(item.get('observacao', ''), style_normal) 
                        ]
                        pdf_data.append(row) 
                        
                    col_widths = [1.2*inch, 0.7*inch, 0.7*inch, 0.7*inch, 1.0*inch, 1.0*inch, 0.8*inch, 0.7*inch, 0.8*inch, 2.4*inch]
                    
                    table = Table(pdf_data, repeatRows=1, colWidths=col_widths) 
                    style = TableStyle([ ('BACKGROUND', (0, 0), (-1, 0), colors.grey), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('GRID', (0, 0), (-1, -1), 1, colors.black), ('BACKGROUND', (0, 1), (-1, -1), colors.beige), ])
                    table.setStyle(style); story.append(table)
                    doc.build(story)
                    return file_in_memory.getvalue()

            # --- EXCEL EXTRATO ---
            elif tipo == "excel_extrato":
                df_nc = pd.DataFrame([dados['nc']])
                df_nc = df_nc.rename(columns={ 'numero_nc': 'Número NC', 'pi': 'PI', 'natureza_despesa': 'ND', 'valor_inicial': 'Valor Inicial', 'data_validade_empenho': 'Prazo Empenho', 'ug_gestora': 'UG Gestora', 'data_recebimento': 'Data Recebimento', 'ptres':'PTRES', 'fonte':'Fonte', 'observacao': 'Observação' })
                df_nc = df_nc[['Número NC', 'PI', 'ND', 'Valor Inicial', 'Prazo Empenho', 'Data Recebimento', 'UG Gestora', 'PTRES', 'Fonte', 'Observação']] 
                if 'Data Recebimento' in df_nc.columns: df_nc['Data Recebimento'] = pd.to_datetime(df_nc['Data Recebimento'], errors='coerce').dt.strftime('%d/%m/%Y')
                if 'Prazo Empenho' in df_nc.columns: df_nc['Prazo Empenho'] = pd.to_datetime(df_nc['Prazo Empenho'], errors='coerce').dt.strftime('%d/%m/%Y')
                
                df_nes = pd.DataFrame(dados['nes'])
                if not df_nes.empty:
                    df_nes = df_nes.rename(columns={'numero_ne': 'Número NE', 'data_empenho': 'Data Empenho', 'valor_empenhado': 'Valor Empenhado', 'descricao':'Descrição'})
                    df_nes = df_nes[['Número NE', 'Data Empenho', 'Valor Empenhado', 'Descrição']]
                    if 'Data Empenho' in df_nes.columns: df_nes['Data Empenho'] = pd.to_datetime(df_nes['Data Empenho'], errors='coerce').dt.strftime('%d/%m/%Y')
                    if 'Valor Empenhado' in df_nes.columns: df_nes['Valor Empenhado'] = pd.to_numeric(df_nes['Valor Empenhado'], errors='coerce') 
                else: df_nes = pd.DataFrame([{" ": "Nenhum empenho registado."}])
                    
                df_recolhimentos = pd.DataFrame(dados['recolhimentos'])
                if not df_recolhimentos.empty:
                    df_recolhimentos = df_recolhimentos.rename(columns={'data_recolhimento': 'Data Recolhimento', 'valor_recolhido': 'Valor Recolhido', 'descricao':'Descrição'})
                    df_recolhimentos = df_recolhimentos[['Data Recolhimento', 'Valor Recolhido', 'Descrição']]
                    if 'Data Recolhimento' in df_recolhimentos.columns: df_recolhimentos['Data Recolhimento'] = pd.to_datetime(df_recolhimentos['Data Recolhimento'], errors='coerce').dt.strftime('%d/%m/%Y')
                    if 'Valor Recolhido' in df_recolhimentos.columns: df_recolhimentos['Valor Recolhido'] = pd.to_numeric(df_recolhimentos['Valor Recolhido'], errors='coerce')
                else: df_recolhimentos = pd.DataFrame([{" ": "Nenhum recolhimento registado."}])
                
                with io.BytesIO() as file_in_memory:
                    with pd.ExcelWriter(file_in_memory, engine='openpyxl') as writer:
                         if 'Valor Empenhado' in df_nes.columns: df_nes['Valor Empenhado'] = pd.to_numeric(df_nes['Valor Empenhado'], errors='coerce')
                         if 'Valor Recolhido' in df_recolhimentos.columns: df_recolhimentos['Valor Recolhido'] = pd.to_numeric(df_recolhimentos['Valor Recolhido'], errors='coerce')
                         
                         df_nc.to_excel(writer, sheet_name='Dados da NC', index=False)
                         df_nes.to_excel(writer, sheet_name='Notas de Empenho', index=False)
                         df_recolhimentos.to_excel(writer, sheet_name='Recolhimentos', index=False)
                    return file_in_memory.getvalue()
                    
            # --- PDF EXTRATO ---
            elif tipo == "pdf_extrato":
                with io.BytesIO() as file_in_memory:
                    doc = SimpleDocTemplate(file_in_memory, pagesize=letter); story = []; 
                    
                    nc = dados['nc'] 
                    
                    styles = getSampleStyleSheet()
                    style_normal = styles['Normal']; style_normal.alignment = TA_LEFT; style_normal.fontSize = 8
                    style_right = ParagraphStyle(name='Right', parent=style_normal, alignment=TA_RIGHT)
                    style_header = ParagraphStyle(name='Header', parent=style_normal, alignment=TA_CENTER, fontName='Helvetica-Bold', textColor=colors.whitesmoke, fontSize=9)
                    style_center = ParagraphStyle(name='Center', parent=style_normal, alignment=TA_CENTER)
                    style_title = styles['Heading1']; style_title.alignment = TA_CENTER
                    style_heading2 = styles['Heading2']
                    
                    story.append(Paragraph(f"Extrato da Nota de Crédito: {nc.get('numero_nc', '')}", style_title)); story.append(Spacer(1, 0.1*inch))
                    story.append(Paragraph(f"PI: {nc.get('pi', '')} | ND: {nc.get('natureza_despesa', '')}", styles['Normal']))
                    story.append(Paragraph(f"Valor Inicial: {self.formatar_moeda(nc.get('valor_inicial'))} | Prazo Empenho: {datetime.fromisoformat(nc.get('data_validade_empenho', '')).strftime('%d/%m/%Y') if nc.get('data_validade_empenho') else ''}", styles['Normal']))
                    story.append(Paragraph(f"Data Recebimento: {datetime.fromisoformat(nc.get('data_recebimento', '')).strftime('%d/%m/%Y') if nc.get('data_recebimento') else ''} | UG Gestora: {nc.get('ug_gestora', '')}", styles['Normal']))
                    story.append(Paragraph("Observação:", style_heading2))
                    story.append(Paragraph(nc.get('observacao', 'N/A'), styles['Normal']))
                    story.append(Spacer(1, 0.2*inch))

                    story.append(Paragraph("Notas de Empenho Vinculadas", style_heading2))
                    header_nes = [Paragraph(h, style_header) for h in ['Número NE', 'Data', 'Valor', 'Descrição']]
                    pdf_data_nes = [header_nes]
                    
                    for ne in dados['nes']:
                        data = datetime.fromisoformat(ne.get('data_empenho', '')).strftime('%d/%m/%Y') if ne.get('data_empenho') else '??/??/????'
                        row = [
                            Paragraph(ne.get('numero_ne', ''), style_center), 
                            Paragraph(data, style_center), 
                            Paragraph(self.formatar_moeda(ne.get('valor_empenhado')), style_right), 
                            Paragraph(ne.get('descricao', ''), style_normal) 
                        ]
                        pdf_data_nes.append(row)
                    
                    if not dados['nes']: 
                        pdf_data_nes.append([Paragraph("Nenhum empenho registado.", style_normal), "", "", ""])
                    
                    table_nes = Table(pdf_data_nes, repeatRows=1, colWidths=[1.5*inch, 0.8*inch, 1.2*inch, 4*inch])
                    style_nes = TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.darkblue), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('GRID', (0, 0), (-1, -1), 1, colors.black), ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),])
                    table_nes.setStyle(style_nes); story.append(table_nes); story.append(Spacer(1, 0.2*inch))
                    
                    story.append(Paragraph("Recolhimentos de Saldo Vinculados", style_heading2))
                    header_rec = [Paragraph(h, style_header) for h in ['Data', 'Valor Recolhido', 'Descrição']]
                    pdf_data_rec = [header_rec]
                    
                    for rec in dados['recolhimentos']:
                         data = datetime.fromisoformat(rec.get('data_recolhimento', '')).strftime('%d/%m/%Y') if rec.get('data_recolhimento') else '??/??/????'
                         row = [
                            Paragraph(data, style_center), 
                            Paragraph(self.formatar_moeda(rec.get('valor_recolhido')), style_right), 
                            Paragraph(rec.get('descricao', ''), style_normal) 
                         ]
                         pdf_data_rec.append(row)
                    
                    if not dados['recolhimentos']: 
                        pdf_data_rec.append([Paragraph("Nenhum recolhimento registado.", style_normal), "", ""])
                    
                    table_rec = Table(pdf_data_rec, repeatRows=1, colWidths=[1*inch, 1.5*inch, 5*inch])
                    style_rec = TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.darkorange), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('GRID', (0, 0), (-1, -1), 1, colors.black), ('BACKGROUND', (0, 1), (-1, -1), colors.lightyellow),])
                    table_rec.setStyle(style_rec); story.append(table_rec)

                    doc.build(story)
                    return file_in_memory.getvalue()
            
            else:
                raise Exception(f"Tipo de relatório desconhecido: {tipo}")
        
        except Exception as e:
            print(f"Erro ao gerar bytes para {tipo}: {e}")
            traceback.print_exc()
            raise e # Propaga o erro
            
# --- FIM DAS ALTERAÇÕES ---

def create_relatorios_view(page: ft.Page, error_modal=None):
    """
    Exporta a nossa RelatoriosView como um controlo Flet padrão.
    """
    return RelatoriosView(page, error_modal=error_modal)