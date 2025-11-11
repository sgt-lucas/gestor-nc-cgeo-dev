# views/dashboard_view.py
# (Versão 5.0, Lote 4 - Responsividade dos Filtros)

import flet as ft
from supabase_client import supabase # Cliente 'anon'
from datetime import datetime, timedelta

class DashboardView(ft.Column):
    """
    Representa o conteúdo da aba Dashboard.
    Versão 5.0 (Lote 4):
    - (Item 10) Torna os controlos de filtro responsivos (stack vertical em telas < 768px).
    """
    
    def __init__(self, page, error_modal=None):
        super().__init__()
        self.page = page
        self.alignment = ft.MainAxisAlignment.START
        self.spacing = 20
        self.padding = 20
        self.error_modal = error_modal
        
        self.progress_ring = ft.ProgressRing(visible=True, width=32, height=32)
        self.txt_saldo_total = ft.Text("R$ 0,00", size=32, weight=ft.FontWeight.BOLD)
        
        # --- TABELA "A VENCER" ---
        self.tabela_vencendo = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Número NC", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Prazo Empenho", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("PI", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("ND", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Saldo Disponível", weight=ft.FontWeight.BOLD), numeric=True),
            ],
            rows=[], 
            expand=True,
            border=ft.border.all(1, "grey200"),
            border_radius=8,
        )
        
        # --- CONTROLOS DE FILTRO ---
        self.filtro_pi = ft.Dropdown(
            label="Filtrar Saldo por PI",
            options=[ft.dropdown.Option(text="Carregando...", disabled=True)],
            expand=True,
            on_change=self.on_pi_filter_change
        )
        self.filtro_nd = ft.Dropdown(
            label="Filtrar Saldo por ND",
            options=[ft.dropdown.Option(text="Carregando...", disabled=True)],
            expand=True,
            on_change=self.load_dashboard_data_wrapper 
        )
        self.filtro_status = ft.Dropdown(
            label="Filtrar Saldo por Status",
            options=[
                ft.dropdown.Option(text="Ativa", key="Ativa"), 
                ft.dropdown.Option(text="Sem Saldo", key="Sem Saldo"),
                ft.dropdown.Option(text="Vencida", key="Vencida"),
                ft.dropdown.Option(text="Cancelada", key="Cancelada"),
            ],
            value="Ativa",
            width=200,
            on_change=self.load_dashboard_data_wrapper
        )
        self.btn_limpar_filtros = ft.IconButton(
            icon="CLEAR_ALL", 
            tooltip="Limpar Filtros do Saldo",
            on_click=self.limpar_filtros
        )

        # --- LAYOUT (LOTE 4 - Responsivo) ---
        self.controls = [
            ft.Row(
                [
                    ft.Text("Saldo Disponível Total", size=20, weight=ft.FontWeight.W_600),
                    ft.Row([
                        ft.IconButton(icon="REFRESH", on_click=self.load_dashboard_data_wrapper, tooltip="Recarregar e Aplicar Filtros"),
                        self.progress_ring,
                    ])
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            
            # (LOTE 4, Item 10) - Linhas de Filtro convertidas para Responsivas
            ft.ResponsiveRow(
                [
                    ft.Column(col={"sm": 12, "md": 6}, controls=[self.filtro_pi]),
                    ft.Column(col={"sm": 12, "md": 6}, controls=[self.filtro_nd]),
                ]
            ),
            ft.ResponsiveRow(
                [
                    ft.Column(col={"sm": 12, "md": 4}, controls=[self.filtro_status]),
                    ft.Column(
                        col={"sm": 12, "md": 2}, 
                        controls=[self.btn_limpar_filtros],
                        # Alinha o botão verticalmente com o dropdown
                        vertical_alignment=ft.CrossAxisAlignment.CENTER 
                    ),
                ],
                alignment=ft.MainAxisAlignment.START
            ),
            # (Fim LOTE 4)

            self.txt_saldo_total,
            ft.Divider(),
            ft.Text("Notas de Crédito a Vencer (Próximos 7 dias)", size=20, weight=ft.FontWeight.W_600),
            ft.Container(
                content=self.tabela_vencendo,
                expand=True
            )
        ]

        # Carrega filtros e depois os dados
        self.load_filter_options()
        self.load_dashboard_data(None)
        
    def show_error(self, message):
        """Exibe o modal de erro global."""
        if self.error_modal:
            self.error_modal.show(message)
        else:
            print(f"ERRO CRÍTICO (Modal não encontrado): {message}")
            
    def handle_db_error(self, ex, context=""):
        """Traduz erros comuns do Supabase/PostgREST para mensagens amigáveis."""
        msg = str(ex)
        print(f"Erro de DB Bruto ({context}): {msg}") 
        
        if "fetch failed" in msg or "Connection refused" in msg:
            self.show_error("Erro de Rede: Não foi possível conectar ao banco de dados. Verifique sua internet.")
        else:
            self.show_error(f"Erro inesperado ao {context}: {msg}")

    def formatar_moeda(self, valor):
        """Formata um float ou string para R$ 0.000,00"""
        try:
            val = float(valor)
            return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, TypeError):
            return "R$ 0,00"

    def load_filter_options(self, pi_selecionado=None):
        """
        Preenche os dropdowns de filtro PI e ND.
        """
        try:
            if pi_selecionado is None:
                print("Dashboard: A carregar opções de filtro (PIs e NDs)...")
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
                print("Dashboard: Opções de filtro iniciais carregadas.")
            
            else:
                print(f"Dashboard: A carregar NDs para o PI: {pi_selecionado}...")
                self.filtro_nd.disabled = True
                self.filtro_nd.update()
                nds = supabase.rpc('get_distinct_nds_for_pi', {'p_pi': pi_selecionado}).execute()
                self.filtro_nd.options.clear()
                self.filtro_nd.options.append(ft.dropdown.Option(text="Todas as NDs", key=None))
                if nds.data:
                    for nd in sorted(nds.data):
                         if nd: self.filtro_nd.options.append(ft.dropdown.Option(text=nd, key=nd))
                print("Dashboard: Filtro ND atualizado.")
            
            self.filtro_nd.disabled = False
            self.update() 

        except Exception as ex:
            print(f"Erro ao carregar opções de filtro no Dashboard: {ex}")
            self.handle_db_error(ex, "carregar filtros do Dashboard")

    def on_pi_filter_change(self, e):
        """
        Recarrega as opções de ND e depois recarrega os dados do Dashboard.
        """
        pi_val = self.filtro_pi.value if self.filtro_pi.value else None
        self.filtro_nd.value = None
        self.load_filter_options(pi_selecionado=pi_val)
        self.load_dashboard_data(None) 

    def load_dashboard_data_wrapper(self, e):
        """Função "wrapper" para o botão recarregar."""
        self.load_dashboard_data(e)

    def load_dashboard_data(self, e):
        """
        Busca os dados no Supabase e atualiza os controlos da UI.
        Aplica filtros APENAS ao cálculo do saldo total.
        """
        print("Dashboard: A carregar dados com filtros...")
        self.progress_ring.visible = True
        self.page.update()

        try:
            # --- 1. Buscar Saldo Total (COM FILTROS) ---
            query_saldo = supabase.table('ncs_com_saldos').select('saldo_disponivel')
            
            if self.filtro_status.value:
                query_saldo = query_saldo.eq('status_calculado', self.filtro_status.value)
            if self.filtro_pi.value:
                query_saldo = query_saldo.eq('pi', self.filtro_pi.value)
            if self.filtro_nd.value:
                query_saldo = query_saldo.eq('natureza_despesa', self.filtro_nd.value)

            resposta_saldo = query_saldo.execute()
            
            saldo_total = 0.0
            if resposta_saldo.data:
                saldo_total = sum(float(item['saldo_disponivel']) for item in resposta_saldo.data)
            
            self.txt_saldo_total.value = self.formatar_moeda(saldo_total)
            
            # --- 2. Buscar NCs a Vencer (SEM FILTROS ADICIONAIS) ---
            hoje = datetime.now().date()
            em_7_dias = hoje + timedelta(days=7)
            
            resposta_vencendo = supabase.table('ncs_com_saldos') \
                                        .select('numero_nc, data_validade_empenho, saldo_disponivel, pi, natureza_despesa') \
                                        .filter('status_calculado', 'eq', 'Ativa') \
                                        .filter('data_validade_empenho', 'gte', hoje.isoformat()) \
                                        .filter('data_validade_empenho', 'lte', em_7_dias.isoformat()) \
                                        .order('data_validade_empenho', desc=False) \
                                        .execute()

            # --- 3. Preencher a Tabela "A Vencer" ---
            self.tabela_vencendo.rows.clear()
            if resposta_vencendo.data:
                for nc in resposta_vencendo.data:
                    saldo_nc = float(nc['saldo_disponivel'])
                    data_formatada = datetime.fromisoformat(nc['data_validade_empenho']).strftime('%d/%m/%Y')
                    self.tabela_vencendo.rows.append(
                        ft.DataRow(
                            cells=[
                                ft.DataCell(ft.Text(nc['numero_nc'])),
                                ft.DataCell(ft.Text(data_formatada)),
                                ft.DataCell(ft.Text(nc['pi'])),
                                ft.DataCell(ft.Text(nc['natureza_despesa'])),
                                ft.DataCell(ft.Text(self.formatar_moeda(saldo_nc))),
                            ]
                        )
                    )
            else:
                self.tabela_vencendo.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text("Nenhuma NC a vencer nos próximos 7 dias.", italic=True)),
                        ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")),
                        ft.DataCell(ft.Text("")), ft.DataCell(ft.Text("")),
                    ])
                )

            print("Dashboard: Dados carregados com sucesso.")

        except Exception as ex:
            print(f"Erro ao carregar dashboard: {ex}")
            self.handle_db_error(ex, "carregar dados do Dashboard")
        
        self.progress_ring.visible = False
        self.page.update()
        
    def limpar_filtros(self, e):
        """
        Limpa os filtros do saldo e recarrega os dados.
        """
        print("Dashboard: A limpar filtros do saldo...")
        self.filtro_pi.value = None
        self.filtro_nd.value = None
        self.filtro_status.value = "Ativa" # Volta ao default
        
        self.load_filter_options(pi_selecionado=None) 
        self.load_dashboard_data(None)
        self.page.update()

# --- Função de Nível Superior (Obrigatória) ---
def create_dashboard_view(page: ft.Page, error_modal=None):
    """
    Exporta a nossa DashboardView como um controlo Flet padrão.
    """
    return DashboardView(page, error_modal=error_modal)