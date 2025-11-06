"""Tkinter interface for generating odontological TXT files."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from tkinter import ttk

from app.domain.plano_odonto import (
    DependentesRepository,
    OdontoTxtGenerator,
    PlanosRepository,
    RegistroOdonto,
)
from app.logging import logger


class OdontoApp(ttk.Frame):
    def __init__(self, master: tk.Misc | None = None) -> None:
        super().__init__(master)
        if master is None:
            master = tk.Tk()
        self.master = master
        self.master.title("Gerador TXT Odontológico")
        self._build_menu()

        self.dep_repo = DependentesRepository()
        self.planos_repo = PlanosRepository()
        self.generator = OdontoTxtGenerator()

        self._colaboradores = self.dep_repo.listar_colaboradores()
        self._planos = self.planos_repo.listar_planos()
        self._registros: list[RegistroOdonto] = []
        self._dependentes_atuais = []
        self._colaborador_atual = None

        self._build_widgets()

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.master)
        info_menu = tk.Menu(menubar, tearoff=0)
        info_menu.add_command(label="Sobre", command=self._show_about_dialog)
        menubar.add_cascade(label="Informações", menu=info_menu)
        self.master.config(menu=menubar)

    def _show_about_dialog(self) -> None:
        messagebox.showinfo(
            "Sobre o aplicativo",
            (
                "Gerador TXT Odontológico\n"
                "Desenvolvido por Micael Ortega\n"
                "LinkedIn: https://www.linkedin.com/in/micael-ortega"
            ),
        )

    def _build_widgets(self) -> None:
        self.pack(fill="both", expand=True, padx=12, pady=12)

        filtro_frame = ttk.LabelFrame(self, text="Pesquisar colaborador")
        filtro_frame.pack(fill="x")

        ttk.Label(filtro_frame, text="Nome contém:").grid(row=0, column=0, sticky="w")
        self.entry_busca = ttk.Entry(filtro_frame, width=40)
        self.entry_busca.grid(row=0, column=1, padx=6, pady=4, sticky="we")
        filtro_frame.columnconfigure(1, weight=1)
        self.entry_busca.bind("<KeyRelease>", self._on_busca_digitada)

        ttk.Button(
            filtro_frame,
            text="Buscar",
            command=self._on_buscar_colaborador,
        ).grid(row=0, column=2, padx=6)

        ttk.Label(filtro_frame, text="Colaborador:").grid(row=1, column=0, sticky="w")
        self.combo_colaborador = ttk.Combobox(
            filtro_frame,
            state="readonly",
            values=[c.nome for c in self._colaboradores],
        )
        self.combo_colaborador.grid(row=1, column=1, columnspan=2, sticky="we", pady=4)
        self.combo_colaborador.bind("<<ComboboxSelected>>", self._on_colaborador_selected)

        ttk.Label(filtro_frame, text="Dependente:").grid(row=2, column=0, sticky="w")
        self.combo_dependente = ttk.Combobox(filtro_frame, state="readonly")
        self.combo_dependente.grid(row=2, column=1, columnspan=2, sticky="we", pady=4)

        ttk.Label(filtro_frame, text="Plano Odonto:").grid(row=3, column=0, sticky="w")
        self.combo_plano = ttk.Combobox(
            filtro_frame,
            state="readonly",
            values=[
                f"{p.codigo} - {p.descricao}" if p.descricao else p.codigo
                for p in self._planos
            ],
        )
        self.combo_plano.grid(row=3, column=1, columnspan=2, sticky="we", pady=4)

        ttk.Button(
            filtro_frame,
            text="Adicionar linha",
            command=self._on_adicionar,
        ).grid(row=4, column=2, pady=6, sticky="e")

        tabela_frame = ttk.LabelFrame(self, text="Registros selecionados")
        tabela_frame.pack(fill="both", expand=True, pady=(10, 0))

        self.tree = ttk.Treeview(
            tabela_frame,
            columns=("cod_coligada", "chapa", "nro_depend", "cod_plano", "flag"),
            show="headings",
            height=8,
        )
        self.tree.heading("cod_coligada", text="Cod. Coligada")
        self.tree.heading("chapa", text="Chapa")
        self.tree.heading("nro_depend", text="Nro Depend.")
        self.tree.heading("cod_plano", text="Plano Odonto")
        self.tree.heading("flag", text="Flag")
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
            text="Remover seleção",
            command=self._on_remover,
        ).pack(side="left")

        ttk.Button(
            buttons_frame,
            text="Exportar TXT...",
            command=self._on_exportar,
        ).pack(side="right")

    def _on_buscar_colaborador(self) -> None:
        self._apply_colaborador_filtro(self.entry_busca.get())

    def _on_busca_digitada(self, event=None) -> None:
        self._apply_colaborador_filtro(self.entry_busca.get())

    def _apply_colaborador_filtro(self, termo: str) -> None:
        self._colaboradores = self.dep_repo.buscar_por_nome(termo)
        self.combo_colaborador["values"] = [c.nome for c in self._colaboradores]
        self.combo_colaborador.set("")
        self.combo_dependente.set("")
        self.combo_dependente["values"] = []
        self._dependentes_atuais = []
        self._colaborador_atual = None

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
            f"{d.numero} - {d.nome}" for d in dependentes
        ]
        self.combo_dependente.set("")
        self._dependentes_atuais = dependentes
        self._colaborador_atual = colaborador

    def _on_adicionar(self) -> None:
        if self._colaborador_atual is None:
            messagebox.showwarning("Seleção incompleta", "Escolha um colaborador primeiro.")
            return

        idx_dep = self.combo_dependente.current()
        idx_plano = self.combo_plano.current()
        if idx_dep < 0 or idx_plano < 0:
            messagebox.showwarning("Seleção incompleta", "Selecione dependente e plano.")
            return

        dependente = self._dependentes_atuais[idx_dep]
        plano = self._planos[idx_plano]

        registro = RegistroOdonto(
            cod_coligada=dependente.cod_coligada,
            chapa=dependente.chapa,
            nro_depend=dependente.numero,
            cod_plano=plano.codigo,
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
            title="Salvar TXT odontológico",
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
