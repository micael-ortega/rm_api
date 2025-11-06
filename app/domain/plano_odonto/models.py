"""Domain models for the odontological TXT generator."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Colaborador:
    cod_coligada: str
    chapa: str
    nome: str


@dataclass(frozen=True)
class Dependente:
    cod_coligada: str
    chapa: str
    numero: str
    nome: str
    grau_parentesco: str


@dataclass(frozen=True)
class PlanoOdonto:
    codigo: str
    descricao: str


@dataclass
class RegistroOdonto:
    cod_coligada: str
    chapa: str
    nro_depend: str
    cod_plano: str
    flag_inclusao: str = "1"

    def to_line(self, separator: str = ";") -> str:
        return separator.join(
            [
                self.cod_coligada,
                self.chapa,
                self.nro_depend,
                self.cod_plano,
                self.flag_inclusao,
            ]
        )
