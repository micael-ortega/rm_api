"""Domain models for the odontological TXT generator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


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
    plano_odonto: Optional[str] = None
    flag_plano_saude: Optional[str] = None
    data_inicio_plano_saude: Optional[str] = None


@dataclass(frozen=True)
class PlanoOdonto:
    cod_coligada: str
    codigo: str
    descricao: str


@dataclass
class RegistroBeneficioDependente:
    cod_coligada: str
    chapa: str
    nro_depend: str
    cod_plano: str
    flag_inclusao: str = "1"
    flag_plano_saude: str = "0"
    data_inicio_plano_saude: str = ""

    def to_line(self, separator: str = ";") -> str:
        return separator.join(
            [
                self.cod_coligada,
                self.chapa,
                self.nro_depend,
                self.cod_plano,
                self.flag_inclusao,
                self.flag_plano_saude,
                self.data_inicio_plano_saude,
            ]
        )
