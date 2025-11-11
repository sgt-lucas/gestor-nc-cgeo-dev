# views/nes_view.py
# (Versão 3, com filtros)

import flet as ft
from supabase_client import supabase # Cliente 'anon'
from datetime import datetime

class NesView(ft.Column):
    """
    Representa o conteúdo da aba Notas de Empenho (CRUD).
    Versão 3: Adiciona funcionalidade de FILTROS.
    """
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.id_ne_sendo_editada = None
        
        self.alignment = ft.MainAxisAlignment.START
        self.spacing = 20
        # (Corrigido para o formato Flet)
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

        # --- Modais (Adição/Edição e Exclusão) ---
        self.modal_dropdown_nc = ft.Dropdown(label="Vincular à NC (Obrigatório)")
        self.modal_txt_numero_ne = ft.TextField(label="Número NE", hint_text="Ex: 2025NE000123")
        self.modal_txt_data_empenho = ft.TextField(label="Data Empenho", hint_text="AAAA-MM-DD")
        self.modal_txt_valor_empenhado = ft.TextField(label="Valor Empenhado", prefix="R$", input_filter=ft.InputFilter(r"[0-9.,]"))
        self.modal_txt_descricao = ft.TextField(label="Descrição (Opcional)")
        
        self.modal_form = ft.AlertDialog(
            modal=True, title=ft.Text("Adicionar Nova Nota de Empenho"),
            content=ft.Column(
                [
                    self.modal_dropdown_nc,
                    self.modal_txt_numero_ne,
                    self.modal_txt_data_empenho,
                    self.modal_txt_valor_empenhado,
                    self.modal_txt_descricao,
                ], height=400, width=500, scroll=ft.ScrollMode.ADAPTIVE,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=self.close_modal),
                ft.ElevatedButton("Salvar", on_click=self.save_ne, icon="SAVE"),
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
        self.btn_limpar_filtros = ft.IconButton(
            icon="CLEAR_ALL", 
            tooltip="Limpar Filtros",
            on_click=self.limpar_filtros
        )

        # --- LAYOUT ATUALIZADO (com filtros) ---
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
        
        self.load_nc_filter_options()
        self.load_nes_data()

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

    def load_nc_filter_options(self):
        """
        Busca todas as NCs (ID e Numero) para preencher o dropdown de filtro.
        """
        print("NEs: A carregar NCs para o filtro...")
        try:
            resposta_ncs = supabase.table('notas_de_credito') \
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
            print(f"Erro ao carregar NCs para filtro: {ex}")
            # Este é o erro que víamos no log
            self.show_snackbar(f"Erro ao carregar NCs para filtro: {ex}")

    def load_nes_data_wrapper(self, e):
        self.load_nes_data()

    def load_nes_data(self):
        """
        Busca todas as NEs, APLICANDO FILTROS, e as NCs vinculadas.
        """
        print("NEs: A carregar dados com filtros...")
        self.progress_ring.visible = True
        self.page.update()

        try:
            query = supabase.table('notas_de_empenho') \
                           .select('*, notas_de_credito(numero_nc)') # O join busca o numero_nc

            if self.filtro_pesquisa_ne.value:
                query = query.ilike('numero_ne', f"%{self.filtro_pesquisa_ne.value}%")
            
            if self.filtro_nc_vinculada.value:
                query = query.eq('id_nc', self.filtro_nc_vinculada.value)

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
            print(f"Erro ao carregar NEs: {ex}")
            self.show_snackbar(f"Erro ao carregar NEs: {ex}")
        
        self.progress_ring.visible = False
        self.page.update()

    def limpar_filtros(self, e):
        """
        Limpa os filtros de NE e recarrega a tabela.
        """
        print("NEs: A limpar filtros...")
        self.filtro_pesquisa_ne.value = ""
        self.filtro_nc_vinculada.value = None
        self.load_nes_data()
        self.page.update()

    def carregar_ncs_para_dropdown_modal(self):
        """Busca NCs 'Ativas' para o dropdown do MODAL."""
        print("NEs Modal: A carregar NCs ativas...")
        try:
            resposta_ncs = supabase.table('ncs_com_saldos') \
                                   .select('id, numero_nc, saldo_disponivel') \
                                   .filter('status_calculado', 'eq', 'Ativa') \
                                   .execute()
            self.modal_dropdown_nc.options.clear()
            if not resposta_ncs.data:
                self.show_snackbar("Nenhuma NC 'Ativa' encontrada para vincular.")
                return False
            for nc in resposta_ncs.data:
                saldo_formatado = self.formatar_moeda(nc['saldo_disponivel'])
                texto_opcao = f"{nc['numero_nc']} (Saldo: {saldo_formatado})"
                self.modal_dropdown_nc.options.append(
                    ft.dropdown.Option(key=nc['id'], text=texto_opcao)
                )
            return True
        except Exception as ex:
            print(f"Erro ao carregar NCs para dropdown do modal: {ex}")
            self.show_snackbar(f"Erro ao carregar NCs: {ex}")
            return False

    def open_add_modal(self, e):
        print("A abrir modal de ADIÇÃO de NE...")
        if not self.carregar_ncs_para_dropdown_modal():
            return 
        self.id_ne_sendo_editada = None
        self.modal_form.title = ft.Text("Adicionar Nova Nota de Empenho")
        self.modal_form.actions[1].text = "Salvar"
        self.modal_form.actions[1].icon = "SAVE"
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
        self.modal_form.actions[1].text = "Atualizar"
        self.modal_form.actions[1].icon = "UPDATE"
        self.modal_dropdown_nc.value = ne['id_nc'] 
        self.modal_txt_numero_ne.value = ne['numero_ne']
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
            if has_error:
                print("Erro de validação.")
                self.modal_form.update()
                return 
            valor_limpo = self.modal_txt_valor_empenhado.value.replace(".", "").replace(",", ".")
            dados_para_salvar = {
                "id_nc": self.modal_dropdown_nc.value,
                "numero_ne": self.modal_txt_numero_ne.value, 
                "data_empenho": self.modal_txt_data_empenho.value,
                "valor_empenhado": float(valor_limpo),
                "descricao": self.modal_txt_descricao.value,
            }
            if self.id_ne_sendo_editada is None:
                print("A inserir nova NE no Supabase...")
                supabase.table('notas_de_empenho').insert(dados_para_salvar).execute()
                print("NE salva com sucesso.")
                self.show_snackbar(f"NE {dados_para_salvar['numero_ne']} salva com sucesso!", "green")
            else:
                print(f"A atualizar NE ID: {self.id_ne_sendo_editada}...")
                supabase.table('notas_de_empenho').update(dados_para_salvar).eq('id', self.id_ne_sendo_editada).execute()
                print("NE atualizada com sucesso.")
                self.show_snackbar(f"NE {dados_para_salvar['numero_ne']} atualizada com sucesso!", "green")
            self.close_modal(None) 
            self.load_nes_data() 
        except Exception as ex:
            print(f"Erro ao salvar NE: {ex}")
            self.show_snackbar(f"Erro ao salvar: {ex}")
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
        try:
            id_para_excluir = self.confirm_delete_dialog.data
            print(f"A excluir NE ID: {id_para_excluir}...")
            supabase.table('notas_de_empenho').delete().eq('id', id_para_excluir).execute()
            print("NE excluída com sucesso.")
            self.show_snackbar("Nota de Empenho excluída com sucesso.", "green")
            self.close_confirm_delete(None)
            self.load_nes_data() 
        except Exception as ex:
            print(f"Erro ao excluir NE: {ex}")
            self.show_snackbar(f"Erro ao excluir: {ex}")
            self.close_confirm_delete(None)

def create_nes_view(page: ft.Page):
    """
    Exporta a nossa NesView como um controlo Flet padrão.
    """
    return NesView(page)