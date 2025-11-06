"""Gateway to execute RM queries and return pandas DataFrames."""

from __future__ import annotations

from typing import Any, Mapping, Optional
from xml.etree import ElementTree

import pandas as pd

from app.infra.soap.client import build_rm_service
from app.infra.soap.parser import (
    DatasetDataFrameBuilder,
    DatasetNormalizer,
    SoapResponseParser,
)
from app.logging import logger


class RMQueryGateway:
    """High-level adapter that returns DataFrames from RM SOAP queries."""

    def __init__(self, *, row_tag: Optional[str] = None) -> None:
        self.rm_service = build_rm_service()
        self.parser = SoapResponseParser()
        self.normalizer = DatasetNormalizer()
        self.df_builder = DatasetDataFrameBuilder()
        self.row_tag_override = row_tag

    def fetch_dataframe(
        self,
        query_name: str,
        *,
        parameters: Optional[Mapping[str, Any]] = None,
        row_tag: Optional[str] = None,
    ) -> pd.DataFrame:
        payload = self.rm_service.execute(
            query_name,
            parameters=parameters,
            timeout=None,
        )
        if not payload:
            logger.warning("Consulta %s retornou payload vazio.", query_name)
            return pd.DataFrame()

        fault_message = self._extract_fault_message(payload)
        if fault_message:
            logger.error(
                "Consulta %s retornou Fault do servidor: %s",
                query_name,
                fault_message,
            )
            return pd.DataFrame()

        dataset_xml = self.parser.extract_result_xml(payload)
        dataset_root = self.normalizer.parse(dataset_xml)
        if dataset_root is None:
            return pd.DataFrame()

        dataframe = self.df_builder.to_dataframe(
            dataset_root,
            row_tag=row_tag or self.row_tag_override,
        )
        return dataframe.fillna("")

    @staticmethod
    def _extract_fault_message(payload: str) -> Optional[str]:
        """Return the soap fault message when present."""
        try:
            root = ElementTree.fromstring(payload)
        except ElementTree.ParseError:
            return None

        namespaces = {
            "soapenv": "http://schemas.xmlsoap.org/soap/envelope/",
            "s": "http://schemas.xmlsoap.org/soap/envelope/",
        }
        fault = (
            root.find(".//soapenv:Fault", namespaces=namespaces)
            or root.find(".//s:Fault", namespaces=namespaces)
            or root.find(".//Fault")
        )
        if fault is None:
            return None

        faultstring = fault.findtext("faultstring")
        if faultstring:
            return faultstring.strip()

        detail_message = fault.findtext(".//Message")
        if detail_message:
            return detail_message.strip()

        return ElementTree.tostring(fault, encoding="unicode")

