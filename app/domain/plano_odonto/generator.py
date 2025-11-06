"""TXT generator for odontological data."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from app.domain.plano_odonto.models import RegistroBeneficioDependente


class OdontoTxtGenerator:
    """Export records to a TXT file using the expected semicolon layout."""

    def __init__(self, separator: str = ";", include_header: bool = False) -> None:
        self.separator = separator
        self.include_header = include_header

    def export(
        self,
        registros: Iterable[RegistroBeneficioDependente],
        destino: Path,
    ) -> Path:
        destino.parent.mkdir(parents=True, exist_ok=True)
        linhas: list[str] = []
        if self.include_header:
            linhas.append(
                f"CODCOLIGADA{self.separator}CHAPA{self.separator}"
                f"NRODEPEND{self.separator}CODPLANOODONTOLOGICO"
                f"{self.separator}FLAG{self.separator}FLAGASSISTMEDICA"
                f"{self.separator}DATAINIASSISTMEDICA"
            )

        for registro in registros:
            linhas.append(registro.to_line(separator=self.separator))

        destino.write_text("\n".join(linhas), encoding="utf-8")
        return destino
