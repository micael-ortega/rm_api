"""Repositories for working with odontological data coming from RM queries."""

from __future__ import annotations

from typing import Optional
from difflib import SequenceMatcher

import pandas as pd

from app.config import ENV
from app.domain.plano_odonto.models import Colaborador, Dependente, PlanoOdonto
from app.infra.gateways.rm_query import RMQueryGateway


class DependentesRepository:
    """Provides access to collaborator and dependent data."""

    def __init__(
        self,
        gateway: Optional[RMQueryGateway] = None,
        query_name: Optional[str] = None,
    ) -> None:
        self.gateway = gateway or RMQueryGateway()
        self.query_name = query_name or ENV.get(
            "ODONTO_DEPENDENTES_QUERY",
            "INFO.DEPENDENTES",
        )
        self._cache_df: Optional[pd.DataFrame] = None

    def _ensure_cache(self) -> pd.DataFrame:
        if self._cache_df is None:
            df = self.gateway.fetch_dataframe(self.query_name)
            self._cache_df = df.rename(
                columns={
                    "CODCOLIGADA": "cod_coligada",
                    "CHAPA": "chapa",
                    "NOME": "colaborador",
                    "NRODEPEND": "nro_depend",
                    "DEPENDENTE": "dependente",
                    "GRAUPARENTESCO": "grau_parentesco",
                }
            )
        return self._cache_df

    def listar_colaboradores(self) -> list[Colaborador]:
        df = self._ensure_cache()
        if df.empty:
            return []
        grouped = (
            df.groupby(["cod_coligada", "chapa", "colaborador"])
            .size()
            .reset_index()
        )
        return [
            Colaborador(row.cod_coligada, row.chapa, row.colaborador)
            for row in grouped.itertuples(index=False)
        ]

    def dependentes_do_colaborador(
        self,
        cod_coligada: str,
        chapa: str,
    ) -> list[Dependente]:
        df = self._ensure_cache()
        filtrado = df[
            (df.cod_coligada == cod_coligada) & (df.chapa == chapa)
        ]
        return [
            Dependente(
                row.cod_coligada,
                row.chapa,
                row.nro_depend,
                row.dependente,
                row.grau_parentesco,
            )
            for row in filtrado.itertuples(index=False)
        ]

    def buscar_por_nome(self, termo: str, limite: int = 25) -> list[Colaborador]:
        termo_normalizado = termo.strip().lower()
        if not termo_normalizado:
            return self.listar_colaboradores()

        df = self._ensure_cache()
        colaboradores_unicos = (
            df[["cod_coligada", "chapa", "colaborador"]]
            .drop_duplicates()
            .itertuples(index=False)
        )

        scored: list[tuple[float, Colaborador]] = []
        for row in colaboradores_unicos:
            nome_lower = row.colaborador.lower()
            if termo_normalizado in nome_lower:
                score = 1.0
            else:
                score = SequenceMatcher(None, termo_normalizado, nome_lower).ratio()
            if score < 0.35:
                continue
            scored.append(
                (
                    score,
                    Colaborador(row.cod_coligada, row.chapa, row.colaborador),
                )
            )

        scored.sort(key=lambda item: item[0], reverse=True)
        return [colaborador for _, colaborador in scored[:limite]]


class PlanosRepository:
    """Provides access to odontological plans."""

    def __init__(
        self,
        gateway: Optional[RMQueryGateway] = None,
        query_name: Optional[str] = None,
    ) -> None:
        self.gateway = gateway or RMQueryGateway()
        self.query_name = query_name or ENV.get(
            "ODONTO_PLANOS_QUERY",
            "INFO.PLODONTO",
        )
        self._planos: Optional[list[PlanoOdonto]] = None

    def listar_planos(self) -> list[PlanoOdonto]:
        if self._planos is None:
            df = self.gateway.fetch_dataframe(self.query_name)
            df = df.rename(
                columns={
                    "CODIGO": "codigo",
                    "DESCRICAO": "descricao",
                }
            ).fillna("")
            self._planos = [
                PlanoOdonto(row.codigo, row.descricao)
                for row in df.itertuples(index=False)
            ]
        return list(self._planos)
