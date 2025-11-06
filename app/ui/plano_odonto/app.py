"""Tkinter interface for generating odontological TXT files."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from datetime import datetime
from tkinter import filedialog, messagebox, Label
from tkinter import ttk
import webbrowser

from tkcalendar import DateEntry

from app.domain.beneficios_planos import (
    DependentesRepository,
    OdontoTxtGenerator,
    PlanoOdonto,
    PlanosRepository,
    RegistroBeneficioDependente,
)
from app.logging import logger


class OdontoApp(ttk.Frame):
    def __init__(self, master: tk.Misc | None = None) -> None:
        super().__init__(master)
        if master is None:
            master = tk.Tk()
        self.master = master
        self.master.title("Gerador TXT Benefício Dependentes v1.0")
        self._build_menu()

        self.dep_repo = DependentesRepository()
        self.planos_repo = PlanosRepository()
        self.generator = OdontoTxtGenerator()

        self._colaboradores = self.dep_repo.listar_colaboradores()
        self._planos: list[PlanoOdonto] = []
        self._flag_options = ["Ativa", "Inativa"]
        self._flag_map = {"Ativa": "1", "Inativa": "0"}
        self._flag_active_index = self._flag_options.index("Ativa")
        self._flag_inactive_index = self._flag_options.index("Inativa")
        self._flag_saude_options = ["Sim", "Nao"]
        self._flag_saude_map = {"Sim": "1", "Nao": "0"}
        self._flag_saude_active_index = self._flag_saude_options.index("Sim")
        self._flag_saude_inactive_index = self._flag_saude_options.index("Nao")
        self._registros: list[RegistroBeneficioDependente] = []
        self._dependentes_atuais: list = []
        self._colaborador_atual = None

        self._build_widgets()

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.master)
        info_menu = tk.Menu(menubar, tearoff=0)
        info_menu.add_command(label="Sobre", command=self._show_about_dialog)
        menubar.add_cascade(label="Informacoes", menu=info_menu)
        self.master.config(menu=menubar)

    def _show_about_dialog(self) -> None:
        dialog = tk.Toplevel(self.master)
        dialog.title("Sobre o aplicativo")
        dialog.resizable(False, False)
        dialog.grab_set()

        ttk.Label(
            dialog,
            text="Gerador TXT Beneficios Dependentes",
            font=("Segoe UI", 11, "bold"),
        ).pack(padx=16, pady=(16, 4))

        ttk.Label(dialog, text="Desenvolvido por Micael Ortega").pack(padx=16, pady=(0, 8))

        link = ttk.Label(
            dialog,
            text="LinkedIn: https://www.linkedin.com/in/micael-ortega",
            foreground="blue",
            cursor="hand2",
        )
        link.pack(padx=16)
        link.bind(
            "<Button-1>",
            lambda _: webbrowser.open_new("https://www.linkedin.com/in/micael-ortega"),
        )

        ttk.Button(dialog, text="Fechar", command=dialog.destroy).pack(pady=(12, 16))

    def _build_widgets(self) -> None:
        self.pack(fill="both", expand=True, padx=12, pady=12)

        filtro_frame = ttk.LabelFrame(self, text="Pesquisar colaborador")
        filtro_frame.pack(fill="x")

        ttk.Label(filtro_frame, text="Colaborador:").grid(row=0, column=0, sticky="w")
        self.combo_colaborador = ttk.Combobox(
            filtro_frame,
            state="normal",
            values=[c.nome for c in self._colaboradores],
        )
        self.combo_colaborador.grid(row=0, column=1, columnspan=2, sticky="we", pady=4)
        self.combo_colaborador.bind("<<ComboboxSelected>>", self._on_colaborador_selected)
        self.combo_colaborador.bind("<KeyRelease>", self._on_colaborador_typed)
        filtro_frame.columnconfigure(1, weight=1)

        ttk.Label(filtro_frame, text="Dependente:").grid(row=1, column=0, sticky="w")
        self.combo_dependente = ttk.Combobox(filtro_frame, state="readonly")
        self.combo_dependente.grid(row=1, column=1, columnspan=2, sticky="we", pady=4)
        self.combo_dependente.bind("<<ComboboxSelected>>", self._on_dependente_selected)

        ttk.Label(filtro_frame, text="Plano Odonto:").grid(row=2, column=0, sticky="w")
        self.combo_plano = ttk.Combobox(filtro_frame, state="readonly", values=[])
        self.combo_plano.grid(row=2, column=1, columnspan=2, sticky="we", pady=4)

        ttk.Label(filtro_frame, text="Assistencia odontologica ativa:").grid(
            row=3, column=0, sticky="w"
        )
        self.combo_flag = ttk.Combobox(
            filtro_frame,
            state="readonly",
            values=self._flag_options,
        )
        self.combo_flag.grid(row=3, column=1, columnspan=2, sticky="we", pady=4)
        self.combo_flag.current(self._flag_active_index)
        self.combo_flag.bind("<<ComboboxSelected>>", self._on_flag_odonto_changed)

        ttk.Label(filtro_frame, text="Assistencia medica ativa:").grid(
            row=4, column=0, sticky="w"
        )
        self.combo_flag_saude = ttk.Combobox(
            filtro_frame,
            state="readonly",
            values=self._flag_saude_options,
        )
        self.combo_flag_saude.grid(row=4, column=1, columnspan=2, sticky="we", pady=4)
        self.combo_flag_saude.current(self._flag_saude_inactive_index)

        ttk.Label(filtro_frame, text="Data inicio assistencia medica:").grid(
            row=5, column=0, sticky="w"
        )
        self.entry_data_saude = DateEntry(
            filtro_frame,
            date_pattern="dd/mm/yyyy",
            showweeknumbers=False,
            locale="pt_BR",
        )
        self.entry_data_saude.grid(row=5, column=1, columnspan=2, sticky="we", pady=4)
        self._update_plano_state()

        ttk.Button(
            filtro_frame,
            text="Adicionar linha",
            command=self._on_adicionar,
        ).grid(row=6, column=2, pady=6, sticky="e")

        tabela_frame = ttk.LabelFrame(self, text="Registros selecionados")
        tabela_frame.pack(fill="both", expand=True, pady=(10, 0))

        self.tree = ttk.Treeview(
            tabela_frame,
            columns=(
                "cod_coligada",
                "chapa",
                "nro_depend",
                "cod_plano",
                "flag_odonto",
                "flag_saude",
                "data_saude",
            ),
            show="headings",
            height=8,
        )
        self.tree.heading("cod_coligada", text="Cod. Coligada")
        self.tree.heading("chapa", text="Chapa")
        self.tree.heading("nro_depend", text="Nro Depend.")
        self.tree.heading("cod_plano", text="Plano Odonto")
        self.tree.heading("flag_odonto", text="Flag Odonto")
        self.tree.heading("flag_saude", text="Flag Saude")
        self.tree.heading("data_saude", text="Data Saude")
        self.tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(
            tabela_frame, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(fill="x", pady=10)

        ttk.Button(
            buttons_frame,
            text="Remover selecao",
            command=self._on_remover,
        ).pack(side="left")

        ttk.Button(
            buttons_frame,
            text="Exportar TXT...",
            command=self._on_exportar,
        ).pack(side="right")

    def _format_dependente_label(self, dependente) -> str:
        base = f"{dependente.numero} - {dependente.nome}"
        if getattr(dependente, "plano_odonto", None):
            return f"{base} (Plano atual {dependente.plano_odonto})"
        return f"{base} (Sem plano)"

    def _format_plano_label(self, plano: PlanoOdonto) -> str:
        return f"{plano.cod_coligada} - {plano.codigo} - {plano.descricao}" if plano.descricao else plano.codigo

    def _sync_planos_combobox(self) -> None:
        self.combo_plano["values"] = [self._format_plano_label(p) for p in self._planos]

    def _find_plano_index(self, codigo: str) -> int | None:
        for idx, plano in enumerate(self._planos):
            if plano.codigo == codigo:
                return idx
        return None

    def _parse_data_saude(self, valor: str):
        if not valor:
            return None
        valor = valor.strip()
        formatos = (
            "%d/%m/%Y",
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%d-%m-%Y",
            "%d/%m/%Y %H:%M:%S",
        )
        for fmt in formatos:
            try:
                return datetime.strptime(valor, fmt).date()
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(valor).date()
        except ValueError:
            return None

    def _update_plano_state(self) -> None:
        if self.combo_flag.current() == self._flag_inactive_index:
            self.combo_plano.set("")
            self.combo_plano.configure(state="disabled")
        else:
            self.combo_plano.configure(state="readonly")

    def _on_flag_odonto_changed(self, event=None) -> None:
        self._update_plano_state()

    def _on_colaborador_typed(self, event=None) -> None:
        if event and event.keysym in {"Up", "Down", "Left", "Right", "Return", "Escape"}:
            return
        termo = self.combo_colaborador.get()
        pending_id = getattr(self, "_colaborador_filter_id", None)
        if pending_id:
            try:
                self.after_cancel(pending_id)
            except Exception:
                pass
        self._colaborador_filter_id = self.after(
            180, lambda: self._apply_colaborador_filtro(termo, reset_selection=False)
        )

    def _apply_colaborador_filtro(self, termo: str, reset_selection: bool = True) -> None:
        self._colaborador_filter_id = None
        texto_atual = self.combo_colaborador.get()
        self._colaboradores = self.dep_repo.buscar_por_nome(termo)
        self.combo_colaborador["values"] = [c.nome for c in self._colaboradores]
        if reset_selection:
            self.combo_colaborador.set("")
        else:
            self.combo_colaborador.set(texto_atual)
        self.combo_dependente.set("")
        self.combo_dependente["values"] = []
        self.combo_plano.set("")
        self.combo_plano["values"] = []
        self.combo_flag.current(self._flag_active_index)
        self.combo_flag_saude.current(self._flag_saude_inactive_index)
        self.entry_data_saude.delete(0, "end")
        self._planos = []
        self._dependentes_atuais = []
        self._colaborador_atual = None
        self._update_plano_state()

    def _on_colaborador_selected(self, event=None) -> None:
        idx = self.combo_colaborador.current()
        if idx < 0:
            return
        colaborador = self._colaboradores[idx]
        dependentes = self.dep_repo.dependentes_do_colaborador(
            colaborador.cod_coligada,
            colaborador.chapa,
        )
        self.combo_dependente["values"] = [
            self._format_dependente_label(d) for d in dependentes
        ]
        self.combo_dependente.set("")
        self._dependentes_atuais = dependentes
        self._planos = self.planos_repo.listar_planos(colaborador.cod_coligada)
        self._sync_planos_combobox()
        self.combo_plano.set("")
        self.combo_flag.current(self._flag_active_index)
        self.combo_flag_saude.current(self._flag_saude_inactive_index)
        self.entry_data_saude.delete(0, "end")
        self._colaborador_atual = colaborador
        self._update_plano_state()

    def _on_dependente_selected(self, event=None) -> None:
        idx = self.combo_dependente.current()
        if idx < 0 or idx >= len(self._dependentes_atuais):
            return
        dependente = self._dependentes_atuais[idx]

        codigo_plano = dependente.plano_odonto
        if codigo_plano:
            match_index = self._find_plano_index(codigo_plano)
            if match_index is None:
                novo_plano = PlanoOdonto(
                    cod_coligada=dependente.cod_coligada,
                    codigo=codigo_plano,
                    descricao="",
                )
                self._planos.append(novo_plano)
                self._sync_planos_combobox()
                match_index = len(self._planos) - 1
            self.combo_plano.current(match_index)
            self.combo_flag.current(self._flag_active_index)
        else:
            self.combo_plano.set("")
            self.combo_flag.current(self._flag_inactive_index)

        flag_saude = (dependente.flag_plano_saude or "").strip()
        if flag_saude == "1":
            self.combo_flag_saude.current(self._flag_saude_active_index)
        elif flag_saude == "0":
            self.combo_flag_saude.current(self._flag_saude_inactive_index)
        else:
            self.combo_flag_saude.current(self._flag_saude_inactive_index)
        self.entry_data_saude.delete(0, "end")
        data_saude = (dependente.data_inicio_plano_saude or "").strip()
        if data_saude:
            parsed = self._parse_data_saude(data_saude)
            if parsed:
                self.entry_data_saude.set_date(parsed)
            else:
                self.entry_data_saude.insert(0, data_saude)
        self._update_plano_state()

    def _on_adicionar(self) -> None:
        if self._colaborador_atual is None:
            messagebox.showwarning("Selecao incompleta", "Escolha um colaborador primeiro.")
            return

        idx_dep = self.combo_dependente.current()
        idx_plano = self.combo_plano.current()
        idx_flag = self.combo_flag.current()
        idx_flag_saude = self.combo_flag_saude.current()
        if idx_dep < 0:
            messagebox.showwarning("Selecao incompleta", "Selecione um dependente.")
            return
        if idx_flag < 0:
            messagebox.showwarning(
                "Selecao incompleta", "Selecione o status da assistencia odontologica."
            )
            return
        if idx_flag_saude < 0:
            messagebox.showwarning(
                "Selecao incompleta", "Selecione o status da assistencia medica."
            )
            return

        flag_label = self.combo_flag.get() or self._flag_options[self._flag_active_index]
        flag_inclusao = self._flag_map.get(flag_label, "1")
        exige_plano = flag_inclusao == "1"
        if exige_plano and idx_plano < 0 and not self.combo_plano.get().strip():
            messagebox.showwarning(
                "Selecao incompleta", "Selecione uma opcao de plano odontologico."
            )
            return

        dependente = self._dependentes_atuais[idx_dep]
        plano_codigo = ""
        if exige_plano:
            if idx_plano >= len(self._planos):
                selected_label = self.combo_plano.get().strip()
                if not selected_label:
                    messagebox.showwarning(
                        "Selecao incompleta", "Selecione uma opcao de plano valida."
                    )
                    return
                codigo = selected_label.split(" - ")[0]
                novo_plano = PlanoOdonto(
                    cod_coligada=self._colaborador_atual.cod_coligada,
                    codigo=codigo,
                    descricao="",
                )
                self._planos.append(novo_plano)
                self._sync_planos_combobox()
                idx_plano = len(self._planos) - 1
                self.combo_plano.current(idx_plano)
            plano_codigo = self._planos[idx_plano].codigo
        else:
            if 0 <= idx_plano < len(self._planos):
                plano_codigo = self._planos[idx_plano].codigo
            else:
                label = self.combo_plano.get().strip()
                plano_codigo = label.split(" - ")[0] if label else ""

        flag_saude_label = (
            self.combo_flag_saude.get() or self._flag_saude_options[self._flag_saude_inactive_index]
        )
        flag_plano_saude = self._flag_saude_map.get(flag_saude_label, "0")
        data_plano_saude = self.entry_data_saude.get().strip()
        if flag_plano_saude != "1":
            data_plano_saude = ""

        registro = RegistroBeneficioDependente(
            cod_coligada=dependente.cod_coligada,
            chapa=dependente.chapa,
            nro_depend=dependente.numero,
            cod_plano=plano_codigo,
            flag_inclusao=flag_inclusao,
            flag_plano_saude=flag_plano_saude,
            data_inicio_plano_saude=data_plano_saude,
        )

        self._registros.append(registro)
        self.tree.insert(
            "",
            "end",
            values=(
                registro.cod_coligada,
                registro.chapa,
                registro.nro_depend,
                registro.cod_plano,
                registro.flag_inclusao,
                registro.flag_plano_saude,
                registro.data_inicio_plano_saude,
            ),
        )

    def _on_remover(self) -> None:
        selecionados = self.tree.selection()
        if not selecionados:
            return
        for item in selecionados:
            index = self.tree.index(item)
            self.tree.delete(item)
            self._registros.pop(index)

    def _on_exportar(self) -> None:
        if not self._registros:
            messagebox.showinfo("Nada a exportar", "Adicione pelo menos uma linha.")
            return

        filename = filedialog.asksaveasfilename(
            title="Salvar TXT odontologico",
            defaultextension=".txt",
            filetypes=[("Arquivo texto", "*.txt"), ("Todos os arquivos", "*.*")],
        )
        if not filename:
            return

        destino = Path(filename)
        self.generator.export(self._registros, destino)
        logger.info("Arquivo TXT salvo em %s", destino)
        messagebox.showinfo("Sucesso", f"Arquivo salvo em {destino}")


def main() -> None:
    root = tk.Tk()
    OdontoApp(root)
    root.mainloop()


__all__ = ["main", "OdontoApp"]
