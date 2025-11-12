# views/dashboard_view.py
# (Versão 5.10 - Lote 8.4: Implementação Final do Gráfico)

import flet as ft
import traceback 
from supabase_client import supabase # Cliente 'anon'
from datetime import datetime, timedelta

# (NOVO - Ponto 6) Importa a biblioteca de gráficos
try:
    import flet_charts as charts # Corrigido o nome do pacote de importação
    FLET_CHARTS_AVAILABLE = True
except ImportError:
    print("AVISO: Biblioteca de gráficos 'flet_charts' não encontrada. Execute: pip install flet_charts")
    FLET_CHARTS_AVAILABLE = False


class DashboardView(ft.Column):
    """
    Representa o conteúdo da aba Dashboard.
    Versão 5.10 (Lote 8.4):
    - (Ponto 6) Adiciona gráfico de barras (BarChart) para Saldo por Seção.
    - (BUGFIX) Adiciona 'self.scroll = ft.ScrollMode.ADAPTIVE'.
    """
    
    def __init__(self, page, error_modal=None):
        super().__init__()
        self.page = page
        self.alignment = ft.MainAxisAlignment.START
        self.spacing = 20
        self.padding = 20
        self.error_modal = error_modal
        
        self.scroll = ft.ScrollMode.ADAPTIVE
        
        self.progress_ring = ft.ProgressRing(visible=True, width=32, height=32)
        self.txt_saldo_total = ft.Text("R$ 0,00", size=32, weight=ft.FontWeight.BOLD)
        
        # --- TABELA "A VENCER" (Ponto 3) ---
        self.tabela_vencendo = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Número NC", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Prazo Empenho", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("PI", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("ND", weight=ft.FontWeight.BOLD)),
                ft.DataColumn(ft.Text("Valor Inicial", weight=ft.FontWeight.BOLD), numeric=True),
                ft.DataColumn(ft.Text("Saldo Disponível", weight=ft.FontWeight.BOLD), numeric=True),
            ],
            rows=[], 
            border=ft.border.all(1, "grey200"),
            border_radius=8,
        )
        
        # --- (NOVO - Ponto 6) Gráfico ---
        self.secao_chart = ft.Text("Carregando gráfico de seções...")
        if FLET_CHARTS_AVAILABLE:
            self.secao_chart = charts.BarChart(
                bar_groups=[],
                border=ft.border.all(1, "grey200"),
                border_radius=8,
                horizontal_grid_lines=charts.GridLines(
                    interval=10000, 
                    color="grey200",
                    width=1
                ),
                tooltip=True,
                height=300,
            )
        else:
            self.secao_chart = ft.Text(
                "Erro: Biblioteca 'flet_charts' não instalada.\n"
                "Execute 'pip install flet_charts' no seu terminal.",
                color=ft.colors.RED
            )
        # --- Fim (Ponto 6) ---
        
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

        # --- LAYOUT (Ponto 6) ---
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
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER 
            ),

            self.txt_saldo_total,
            ft.Divider(),
            
            # (Ponto 6) Título e Container do Gráfico
            ft.Text("Saldo Disponível por Seção (NCs Ativas)", size=20, weight=ft.FontWeight.W_600),
            ft.Container(
                content=self.secao_chart,
                padding=10,
                border_radius=8,
            ),
            # --- Fim (Ponto 6) ---
            
            ft.Divider(),
            ft.Text("Notas de Crédito a Vencer (Próximos 7 dias)", size=20, weight=ft.FontWeight.W_600),
            ft.Container(
                content=self.tabela_vencendo,
            )
        ]

        self.on_mount = self.on_view_mount
        
    def on_view_mount(self, e):
        """Chamado pelo Flet DEPOIS que o controlo é adicionado à página."""
        print("DashboardView: Controlo montado. A carregar dados...")
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
        
        if "fetch failed" in msg or "Connection refused" in msg or "Server disconnected" in msg:
            self.show_error("Erro de Rede: Não foi possível conectar ao banco de dados. Tente atualizar a aba.")
        else:
            self.show_error(f"Erro inesperado ao {context}: {msg}")

    def formatar_moeda(self, valor):
        """Formata um float ou string para R$ 0.000,00"""
        try:
            val = float(valor)
            return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (ValueError, TypeError):
            return "R$ 0,00"

    # --- (NOVO - Ponto 6) Função de Carregar Gráfico ---
    def load_chart_data(self):
        """Busca os dados de saldo por seção e constrói o gráfico."""
        if not FLET_CHARTS_AVAILABLE or not isinstance(self.secao_chart, charts.BarChart):
            return # Não faz nada se a biblioteca estiver em falta

        try:
            print("Dashboard: A carregar dados do gráfico de seções...")
            # 1. Chama a nova função RPC 'get_saldo_por_secao'
            resp = supabase.rpc('get_saldo_por_secao').execute()
            
            if not resp.data:
                print("Dashboard: Gráfico - Nenhum dado de seção encontrado.")
                self.secao_chart.bar_groups = []
                self.secao_chart.update()
                return

            print("Dashboard: Dados do gráfico carregados.")
            
            bar_groups = []
            max_y = 0 
            
            # 2. Constrói as barras
            for i, item in enumerate(resp.data):
                secao_nome = item['secao_nome']
                saldo_total = float(item['saldo_total'])
                
                if saldo_total > max_y:
                    max_y = saldo_total
                
                bar_groups.append(
                    charts.BarGroup(
                        x=i,
                        bar_rods=[
                            charts.BarRod(
                                from_y=0,
                                to_y=saldo_total,
                                width=25,
                                color=ft.colors.GREEN_600,
                                tooltip=f"{secao_nome}\n{self.formatar_moeda(saldo_total)}",
                                border_radius=0,
                            )
                        ]
                    )
                )

            # 3. Atualiza o gráfico
            self.secao_chart.bar_groups = bar_groups
            
            # Define o eixo Y para ser um pouco maior que o valor máximo
            self.secao_chart.max_y = (max_y * 1.1) 
            
            # Define os títulos do eixo X (os nomes das seções)
            self.secao_chart.bottom_axis = charts.Axis(
                labels=[
                    charts.AxisLabel(value=i, label=item['secao_nome'][:10]) 
                    for i, item in enumerate(resp.data)
                ]
            )
            
            self.secao_chart.update()
            print("Dashboard: Gráfico de seções atualizado.")

        except Exception as ex:
            print("--- ERRO CRÍTICO (TRACEBACK) NO DASHBOARD [load_chart_data] ---")
            traceback.print_exc()
            self.handle_db_error(ex, "carregar gráfico de seções")
    # --- Fim (Ponto 6) ---

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
            
            if pi_selecionado is None:
                self.update() 

        except Exception as ex:
            print("--- ERRO CRÍTICO (TRACEBACK) NO DASHBOARD [load_filter_options] ---")
            traceback.print_exc()
            print("------------------------------------------------------------------")
            
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
            
            # --- 2. Buscar NCs a Vencer (Ponto 3) ---
            hoje = datetime.now().date()
            em_7_dias = hoje + timedelta(days=7)
            
            resposta_vencendo = supabase.table('ncs_com_saldos') \
                                        .select('numero_nc, data_validade_empenho, saldo_disponivel, pi, natureza_despesa, valor_inicial') \
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
                                ft.DataCell(ft.Text(self.formatar_moeda(nc['valor_inicial']))),
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
                        ft.DataCell(ft.Text("")), 
                    ])
                )

            print("Dashboard: Dados carregados com sucesso.")
            
            # --- (NOVO - Ponto 6) ---
            self.load_chart_data()

        except Exception as ex:
            print("--- ERRO CRÍTICO (TRACEBACK) NO DASHBOARD [load_dashboard_data] ---")
            traceback.print_exc() 
            print("-------------------------------------------------------------------")
            
            print(f"Erro ao carregar dashboard: {ex}")
            self.handle_db_error(ex, "carregar dados do Dashboard")
        
        finally:
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