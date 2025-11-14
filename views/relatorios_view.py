# views/relatorios_view.py
# (CORREÇÃO 7: Reverte para 100% síncrono, remove 'run_thread_safe')

import flet as ft
from supabase_client import supabase # Cliente 'anon'
from datetime import datetime, date
import pandas as pd
import traceback 

# (LOTE 3, Item 6) - Importações necessárias do ReportLab para quebra de texto
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT 

class RelatoriosView(ft.Column):
    """
    Representa o conteúdo da aba Relatórios.
    """
    
    def __init__(self, page, error_modal=None):
        super().__init__()
        self.page = page
        self.alignment = ft.MainAxisAlignment.START
        self.spacing = 20
        self.padding = 20
        self.error_modal = error_modal
        
        self.scroll = ft.ScrollMode.ADAPTIVE
        
        self.progress_ring = ft.ProgressRing(visible=False, width=32, height=32)

        # --- Secção: Relatório Geral NCs ---
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

        # --- Secção: Relatório Individual (Extrato) ---
        self.dropdown_nc_extrato = ft.Dropdown(
            label="Selecione a NC para gerar o Extrato",
            options=[ft.dropdown.Option(text="Carregando...", disabled=True)],
            expand=True
        )
        self.btn_gerar_excel_extrato = ft.ElevatedButton("Gerar Extrato Excel", icon="TABLE_CHART", on_click=self.gerar_extrato_excel)
        self.btn_gerar_pdf_extrato = ft.ElevatedButton("Gerar Extrato PDF", icon="PICTURE_AS_PDF", on_click=self.gerar_extrato_pdf)
        
        # --- Diálogo de Salvamento ---
        self.save_file_dialog = ft.FilePicker(on_result=self.handle_save_file_result)
        self.tipo_ficheiro_a_salvar = None 
        self.dados_relatorio_para_salvar = None 
        self.id_nc_extrato_selecionada = None 

        # --- Layout da Página (V2.2) ---
        self.controls = [
            ft.Row(
                [
                    ft.Text("Relatórios", size=20, weight=ft.FontWeight.W_600),
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
            
            ft.Text("Relatório Geral de Notas de Crédito", size=16, weight=ft.FontWeight.BOLD),
            ft.Text("Filtros (Relatório Geral):"),
            ft.Row([ self.filtro_data_inicio, self.btn_abrir_data_inicio, ft.Container(width=20), self.filtro_data_fim, self.btn_abrir_data_fim, ], alignment=ft.MainAxisAlignment.START),
            ft.Row([self.filtro_pi, self.filtro_nd]),
            ft.Row([self.filtro_status, self.btn_limpar_filtros_geral], alignment=ft.MainAxisAlignment.START),
            ft.Row([self.btn_gerar_excel_geral, self.btn_gerar_pdf_geral], alignment=ft.MainAxisAlignment.CENTER),
            
            ft.Divider(height=30, thickness=2), 

            # Secção Relatório Individual (Extrato)
            ft.Text("Relatório Individual (Extrato) por NC", size=16, weight=ft.FontWeight.BOLD),
            ft.Row([self.dropdown_nc_extrato]),
            ft.Row([self.btn_gerar_excel_extrato, self.btn_gerar_pdf_extrato], alignment=ft.MainAxisAlignment.CENTER),
        ]

        # A lógica de adicionar ao overlay está no __init__
        if self.page:
            self.page.overlay.extend([
                self.date_picker_inicio, 
                self.date_picker_fim, 
                self.save_file_dialog
            ])
        # --- FIM DA CORREÇÃO ---

        self.on_mount = self.on_view_mount
        
    def on_view_mount(self, e):
        """Chamado pelo Flet DEPOIS que o controlo é adicionado à página."""
        print("RelatoriosView: Controlo montado. A carregar dados...")
        self.load_all_filters() 
        
    # -----------------------------------------------------------------
    # INÍCIO DO BLOCO DE MÉTODOS (Tudo indentado dentro da classe)
    # -----------------------------------------------------------------

    def show_error(self, message):
        """Exibe o modal de erro global."""
        if self.error_modal:
            # Em Flet Web, on_click síncrono pode chamar UI
            self.error_modal.show(message)
        else:
            print(f"ERRO CRÍTICO (Modal não encontrado): {message}")
            
    def handle_db_error(self, ex, context=""):
        """Traduz erros comuns do Supabase/PostgREST para mensagens amigáveis."""
        msg = str(ex)
        print(f"Erro de DB Bruto ({context}): {msg}") # Manter no log
        
        if "fetch failed" in msg or "Connection refused" in msg or "Server disconnected" in msg:
            self.show_error("Erro de Rede: Não foi possível conectar ao banco de dados. Tente atualizar a aba.")
        else:
            self.show_error(f"Erro inesperado ao {context}: {msg}")

    def show_success_snackbar(self, message):
        """Mostra uma mensagem de sucesso (verde)."""
        self.page.snack_bar = ft.SnackBar(ft.Text(message), bgcolor="green")
        self.page.snack_bar.open = True
        self.page.update()
             
    def formatar_moeda(self, valor):
        try: val = float(valor); return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, TypeError): return "R$ 0,00"

    # --- Funções dos DatePickers ---
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

    # --- Funções de Filtro (PI, ND) ---
    
    def load_all_filters_wrapper(self, e):
        """Recarrega todas as opções de dropdown na página."""
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
        """Função unificada para carregar todos os dropdowns."""
        self.load_filter_options()
        self.load_nc_list_for_statement_filter()
    
    def load_filter_options(self, pi_selecionado=None):
        """Preenche os dropdowns de filtro PI e ND para o Relatório Geral."""
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
        """Recarrega as opções de ND quando o PI muda."""
        pi_val = self.filtro_pi.value if self.filtro_pi.value else None
        self.filtro_nd.value = None 
        self.load_filter_options(pi_selecionado=pi_val)

    def limpar_filtros_geral(self, e):
        """Limpa os filtros do Relatório Geral."""
        print("Relatórios: A limpar filtros do Relatório Geral...");
        self.filtro_data_inicio.value = ""; self.filtro_data_fim.value = ""
        self.filtro_pi.value = None; self.filtro_nd.value = None
        self.filtro_status.value = None
        self.load_filter_options(pi_selecionado=None)
        if self.page: self.page.update() 
        
    def fetch_report_data_geral(self, e): 
        """Busca os dados das NCs para o Relatório Geral, aplicando filtros."""
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
        """Busca os dados detalhados (NC, NEs, Recolhimentos) para uma NC específica."""
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
        """Busca todas as NCs (ID e Numero) para preencher o dropdown de seleção do Extrato."""
        print("Relatórios: A carregar NCs para o filtro de Extrato...")
        try:
            resposta_ncs = supabase.table('notas_de_credito') \
                                   .select('id, numero_nc') \
                                   .order('numero_nc', desc=False) \
                                   .execute()

            self.dropdown_nc_extrato.options.clear()
            if resposta_ncs.data:
                for nc in resposta_ncs.data:
                    self.dropdown_nc_extrato.options.append(
                        ft.dropdown.Option(key=nc['id'], text=nc['numero_nc'])
                    )
            else:
                 self.dropdown_nc_extrato.options.append(ft.dropdown.Option(text="Nenhuma NC encontrada", disabled=True))

            print("Relatórios: Lista de NCs para Extrato carregada.")
            self.update() 

        except Exception as ex:
            print("--- ERRO CRÍTICO (TRACEBACK) NO RELATORIOS [load_nc_list_for_statement_filter] ---")
            traceback.print_exc()
            print("----------------------------------------------------------------------------------")
            
            print(f"Erro ao carregar NCs para filtro de extrato: {ex}")
            self.handle_db_error(ex, "carregar lista de NCs")
            
    # --- Funções de Geração e Salvamento (Lote 3) ---
    
    def _ensure_and_save_file(self, dialog_title, file_name, allowed_extensions):
        """
        (CORREÇÃO 7)
        Esta função é chamada DIRETAMENTE.
        Ela garante que o FilePicker está no overlay e chama save_file.
        """
        try:
            if self.save_file_dialog and self.page:
                if self.save_file_dialog not in self.page.overlay:
                    print("A re-adicionar save_file_dialog ao overlay...")
                    self.page.overlay.append(self.save_file_dialog)
                
                self.save_file_dialog.save_file(
                    dialog_title=dialog_title,
                    file_name=file_name,
                    allowed_extensions=allowed_extensions
                )
                self.page.update() # Garante que o diálogo abra
            else:
                print("ERRO: save_file_dialog ou page não estão disponíveis.")
        except Exception as e:
            print(f"Erro em _ensure_and_save_file: {e}")
            self.show_error(f"Erro ao tentar abrir diálogo: {e}")
    
    def gerar_relatorio_geral_excel(self, e):
        """Inicia a geração do relatório Excel GERAL."""
        try:
            self.progress_ring.visible = True
            self.update()
            
            dados = self.fetch_report_data_geral(e)
            if dados:
                try:
                    df = pd.DataFrame(dados)
                    df = df.rename(columns={ 'numero_nc': 'Número NC', 'pi': 'PI', 'natureza_despesa': 'ND', 'status_calculado': 'Status', 'valor_inicial': 'Valor Inicial', 'saldo_disponivel': 'Saldo Disponível', 'data_validade_empenho': 'Prazo Empenho', 'ug_gestora': 'UG Gestora', 'data_recebimento': 'Data Recebimento', 'observacao': 'Observação' })
                    colunas_relatorio = ['Número NC', 'PI', 'ND', 'Status', 'Valor Inicial', 'Saldo Disponível', 'Prazo Empenho', 'UG Gestora', 'Data Recebimento', 'Observação']
                    colunas_existentes = [col for col in colunas_relatorio if col in df.columns]
                    df = df[colunas_existentes]
                    if 'Data Recebimento' in df.columns: df['Data Recebimento'] = pd.to_datetime(df['Data Recebimento'], errors='coerce').dt.strftime('%d/%m/%Y')
                    if 'Prazo Empenho' in df.columns: df['Prazo Empenho'] = pd.to_datetime(df['Prazo Empenho'], errors='coerce').dt.strftime('%d/%m/%Y')
                    
                    self.dados_relatorio_para_salvar = df
                    self.tipo_ficheiro_a_salvar = "excel_geral"
                    
                    # --- (INÍCIO DA CORREÇÃO 7) ---
                    # Chamada síncrona direta
                    self._ensure_and_save_file(
                        dialog_title="Salvar Relatório Geral Excel",
                        file_name="relatorio_geral_ncs.xlsx",
                        allowed_extensions=["xlsx"]
                    )
                    # --- (FIM DA CORREÇÃO 7) ---
                    
                except Exception as ex_pandas: 
                    print(f"Erro (Excel Geral): {ex_pandas}"); 
                    self.show_error(f"Erro ao gerar Excel: {ex_pandas}")
                    
        finally:
            self.progress_ring.visible = False; self.update()

    def gerar_relatorio_geral_pdf(self, e):
        """Inicia a geração do relatório PDF GERAL."""
        try:
            self.progress_ring.visible = True
            self.update()
            
            dados = self.fetch_report_data_geral(e)
            if dados:
                self.dados_relatorio_para_salvar = dados 
                self.tipo_ficheiro_a_salvar = "pdf_geral"

                # --- (INÍCIO DA CORREÇÃO 7) ---
                # Chamada síncrona direta
                self._ensure_and_save_file(
                    dialog_title="Salvar Relatório Geral PDF",
                    file_name="relatorio_geral_ncs.pdf",
                    allowed_extensions=["pdf"]
                )
                # --- (FIM DA CORREÇÃO 7) ---
            
        finally:
            self.progress_ring.visible = False; self.update()


    def gerar_extrato_excel(self, e):
        """Inicia a geração do relatório Excel TIPO EXTRATO."""
        try:
            nc_id_selecionada = self.dropdown_nc_extrato.value
            if not nc_id_selecionada: 
                self.page.snack_bar = ft.SnackBar(ft.Text("Selecione uma NC."), bgcolor="orange")
                self.page.snack_bar.open = True
                self.page.update()
                return
                
            self.progress_ring.visible = True
            self.update()
                
            dados = self.fetch_report_data_extrato(nc_id_selecionada)
            if dados:
                try:
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

                    self.dados_relatorio_para_salvar = {"nc": df_nc, "nes": df_nes, "recolhimentos": df_recolhimentos}
                    self.tipo_ficheiro_a_salvar = "excel_extrato"
                    self.id_nc_extrato_selecionada = nc_id_selecionada
                    nc_numero_sanitizado = dados['nc'].get('numero_nc', 'extrato').replace('/', '_').replace('\\', '_')
                    
                    # --- (INÍCIO DA CORREÇÃO 7) ---
                    # Chamada síncrona direta
                    self._ensure_and_save_file(
                        dialog_title="Salvar Extrato Excel",
                        file_name=f"extrato_{nc_numero_sanitizado}.xlsx",
                        allowed_extensions=["xlsx"]
                    )
                    # --- (FIM DA CORREÇÃO 7) ---

                except Exception as ex_pandas: 
                    print(f"Erro (Extrato Excel): {ex_pandas}"); 
                    self.show_error(f"Erro ao gerar Excel: {ex_pandas}")
                    
        finally:
            self.progress_ring.visible = False; self.update()

    def gerar_extrato_pdf(self, e):
        """Inicia a geração do relatório PDF TIPO EXTRATO."""
        try:
            nc_id_selecionada = self.dropdown_nc_extrato.value
            if not nc_id_selecionada: 
                self.page.snack_bar = ft.SnackBar(ft.Text("Selecione uma NC."), bgcolor="orange")
                self.page.snack_bar.open = True
                self.page.update()
                return
                
            self.progress_ring.visible = True
            self.update()
                
            dados = self.fetch_report_data_extrato(nc_id_selecionada)
            if dados:
                self.dados_relatorio_para_salvar = dados 
                self.tipo_ficheiro_a_salvar = "pdf_extrato"
                self.id_nc_extrato_selecionada = nc_id_selecionada
                nc_numero_sanitizado = dados['nc'].get('numero_nc', 'extrato').replace('/', '_').replace('\\', '_')
                
                # --- (INÍCIO DA CORREÇÃO 7) ---
                # Chamada síncrona direta
                self._ensure_and_save_file(
                    dialog_title="Salvar Extrato PDF",
                    file_name=f"extrato_{nc_numero_sanitizado}.pdf",
                    allowed_extensions=["pdf"]
                )
                # --- (FIM DA CORREÇÃO 7) ---
                
        finally:
            self.progress_ring.visible = False; self.update()

    def handle_save_file_result(self, e):
        """Chamado DEPOIS que o utilizador escolhe onde salvar."""
        
        self.progress_ring.visible = True
        self.update()
        
        # Esta função (on_result) JÁ É executada na thread principal,
        # mas a GERAÇÃO do PDF/Excel é bloqueante.
        
        def blocking_save_operation(caminho_salvar):
            # Esta função síncrona interna fará o trabalho pesado
            try:
                styles = getSampleStyleSheet()
                style_normal = styles['Normal']
                style_normal.alignment = TA_LEFT
                style_normal.fontSize = 8
                style_right = ParagraphStyle(name='Right', parent=style_normal, alignment=TA_RIGHT)
                style_header = ParagraphStyle(name='Header', parent=style_normal, alignment=TA_CENTER, fontName='Helvetica-Bold', textColor=colors.whitesmoke, fontSize=9)
                style_center = ParagraphStyle(name='Center', parent=style_normal, alignment=TA_CENTER)
                style_title = styles['Heading1']
                style_title.alignment = TA_CENTER
                style_heading2 = styles['Heading2']
                
                
                # --- EXCEL GERAL ---
                if self.tipo_ficheiro_a_salvar == "excel_geral":
                    df_to_save: pd.DataFrame = self.dados_relatorio_para_salvar
                    if 'Valor Inicial' in df_to_save.columns: df_to_save['Valor Inicial'] = pd.to_numeric(df_to_save['Valor Inicial'], errors='coerce').fillna(0)
                    if 'Saldo Disponível' in df_to_save.columns: df_to_save['Saldo Disponível'] = pd.to_numeric(df_to_save['Saldo Disponível'], errors='coerce').fillna(0)
                    df_to_save.to_excel(caminho_salvar, index=False, engine='openpyxl')
                    return "Relatório Excel Geral salvo!"

                # --- PDF GERAL (LOTE 3, Item 6 - Corrigido) ---
                elif self.tipo_ficheiro_a_salvar == "pdf_geral":
                    doc = SimpleDocTemplate(caminho_salvar, pagesize=landscape(letter)); story = [];
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
                    dados_pdf = self.dados_relatorio_para_salvar
                    
                    for item in dados_pdf: 
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
                    style = TableStyle([ 
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey), 
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'), 
                        ('GRID', (0, 0), (-1, -1), 1, colors.black), 
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige), 
                    ])
                    table.setStyle(style); story.append(table)
                    doc.build(story)
                    return "Relatório PDF Geral salvo!"

                # --- EXCEL EXTRATO ---
                elif self.tipo_ficheiro_a_salvar == "excel_extrato":
                    dfs: dict = self.dados_relatorio_para_salvar
                    with pd.ExcelWriter(caminho_salvar, engine='openpyxl') as writer:
                         if 'Valor Empenhado' in dfs["nes"].columns: dfs["nes"]['Valor Empenhado'] = pd.to_numeric(dfs["nes"]['Valor Empenhado'], errors='coerce')
                         if 'Valor Recolhido' in dfs["recolhimentos"].columns: dfs["recolhimentos"]['Valor Recolhido'] = pd.to_numeric(dfs["recolhimentos"]['Valor Recolhido'], errors='coerce')
                         
                         dfs["nc"].to_excel(writer, sheet_name='Dados da NC', index=False)
                         dfs["nes"].to_excel(writer, sheet_name='Notas de Empenho', index=False)
                         dfs["recolhimentos"].to_excel(writer, sheet_name='Recolhimentos', index=False)
                    return "Extrato Excel salvo!"
                    
                # --- PDF EXTRATO (LOTE 3, Item 6 - Corrigido) ---
                elif self.tipo_ficheiro_a_salvar == "pdf_extrato":
                    doc = SimpleDocTemplate(caminho_salvar, pagesize=letter); story = []; 
                    dados_extrato: dict = self.dados_relatorio_para_salvar
                    nc = dados_extrato['nc']
                    
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
                    for ne in dados_extrato['nes']:
                        data = datetime.fromisoformat(ne.get('data_empenho', '')).strftime('%d/%m/%Y') if ne.get('data_empenho') else ''
                        row = [
                            Paragraph(ne.get('numero_ne', ''), style_center), 
                            Paragraph(data, style_center), 
                            Paragraph(self.formatar_moeda(ne.get('valor_empenhado')), style_right), 
                            Paragraph(ne.get('descricao', ''), style_normal) 
                        ]
                        pdf_data_nes.append(row)
                    if not dados_extrato['nes']: pdf_data_nes.append([Paragraph("Nenhum empenho registado.", style_normal), "", "", ""])
                    
                    table_nes = Table(pdf_data_nes, repeatRows=1, colWidths=[1.5*inch, 0.8*inch, 1.2*inch, 4*inch])
                    style_nes = TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.darkblue), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('GRID', (0, 0), (-1, -1), 1, colors.black), ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),])
                    table_nes.setStyle(style_nes); story.append(table_nes); story.append(Spacer(1, 0.2*inch))
                    
                    story.append(Paragraph("Recolhimentos de Saldo Vinculados", style_heading2))
                    header_rec = [Paragraph(h, style_header) for h in ['Data', 'Valor Recolhido', 'Descrição']]
                    pdf_data_rec = [header_rec]
                    for rec in dados_extrato['recolhimentos']:
                         data = datetime.fromisoformat(rec.get('data_recolhimento', '')).strftime('%d/%m/%Y') if rec.get('data_recolhimento') else ''
                         row = [
                            Paragraph(data, style_center), 
                            Paragraph(self.formatar_moeda(rec.get('valor_recolhido')), style_right), 
                            Paragraph(rec.get('descricao', ''), style_normal) 
                         ]
                         pdf_data_rec.append(row)
                    if not dados_extrato['recolhimentos']: pdf_data_rec.append([Paragraph("Nenhum recolhimento registado.", style_normal), "", ""])
                    
                    table_rec = Table(pdf_data_rec, repeatRows=1, colWidths=[1*inch, 1.5*inch, 5*inch])
                    style_rec = TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.darkorange), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('GRID', (0, 0), (-1, -1), 1, colors.black), ('BACKGROUND', (0, 1), (-1, -1), colors.lightyellow),])
                    table_rec.setStyle(style_rec); story.append(table_rec)

                    doc.build(story)
                    return "Extrato PDF salvo!"
                
                return None 
            
            except Exception as ex_save: 
                print(f"Erro ao salvar ({self.tipo_ficheiro_a_salvar}): {ex_save}")
                return ex_save # Retorna a exceção

        # --- Continuação de handle_save_file_result ---
        try:
            if e.path and self.dados_relatorio_para_salvar is not None and self.tipo_ficheiro_a_salvar:
                caminho_salvar = e.path
                print(f"A salvar relatório ({self.tipo_ficheiro_a_salvar}) em: {caminho_salvar}")
                
                # Executa a geração de PDF/Excel (bloqueante)
                resultado = blocking_save_operation(caminho_salvar)
                
                if isinstance(resultado, Exception):
                    self.show_error(f"Erro ao salvar: {resultado}")
                elif resultado:
                    self.show_success_snackbar(resultado)

            else:
                print("Salvar cancelado/dados em falta.")
        
        finally: 
            self.dados_relatorio_para_salvar = None
            self.tipo_ficheiro_a_salvar = None
            self.id_nc_extrato_selecionada = None
            self.progress_ring.visible = False
            self.page.update() 
            
# --- FUNÇÃO QUE FALTAVA ---
def create_relatorios_view(page: ft.Page, error_modal=None):
    """
    Exporta a nossa RelatoriosView como um controlo Flet padrão.
    """
    return RelatoriosView(page, error_modal=error_modal)