"""Utilities to parse SOAP payloads into XML and DataFrames."""

from __future__ import annotations

from typing import Optional

import pandas as pd
import re
from xml.etree import ElementTree

from app.logging import logger

SOAP_NAMESPACES = {
    "soapenv": "http://schemas.xmlsoap.org/soap/envelope/",
    "tot": "http://www.totvs.com/",
}


class SoapResponseParser:
    """Extract and sanitise the RM SOAP response payload."""

    AMP_PATTERN = re.compile(r"&(?![a-zA-Z_]+;|#[0-9]+;|#x[0-9A-Fa-f]+;)")
    CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")
    DECIMAL_ENTITY_PATTERN = re.compile(r"&#([0-9]+);")
    HEX_ENTITY_PATTERN = re.compile(r"&#x([0-9A-Fa-f]+);")

    ENTITY_MAP = {
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": '"',
        "&apos;": "'",
        "&#x0D;": "\r",
        "&#x0A;": "\n",
    }

    def extract_result_xml(self, soap_payload: str | None) -> str | None:
        if not soap_payload:
            return None

        try:
            root = ElementTree.fromstring(soap_payload)
        except ElementTree.ParseError as exc:
            logger.error(
                "Não foi possível interpretar o envelope SOAP: %s",
                exc,
                exc_info=True,
            )
            return None

        result_node = root.find(
            ".//tot:RealizarConsultaSQLResult",
            namespaces=SOAP_NAMESPACES,
        )
        if result_node is None:
            logger.error("Elemento RealizarConsultaSQLResult não encontrado.")
            return None

        raw_xml = (result_node.text or "").strip()
        if not raw_xml:
            logger.warning("Campo RealizarConsultaSQLResult vazio.")
            return None

        decoded = self._decode_basic_entities(raw_xml)
        decoded = self._decode_numeric_entities(decoded)
        decoded = self.AMP_PATTERN.sub("&amp;", decoded)
        return self.CONTROL_CHARS_PATTERN.sub("", decoded)

    def _decode_basic_entities(self, text: str) -> str:
        decoded = text
        for entity, replacement in self.ENTITY_MAP.items():
            decoded = decoded.replace(entity, replacement)
        return decoded

    def _decode_numeric_entities(self, text: str) -> str:
        text = self.DECIMAL_ENTITY_PATTERN.sub(self._replace_decimal_entity, text)
        text = self.HEX_ENTITY_PATTERN.sub(self._replace_hex_entity, text)
        return text

    def _replace_decimal_entity(self, match: re.Match[str]) -> str:
        codepoint = int(match.group(1), 10)
        return self._codepoint_to_char(codepoint)

    def _replace_hex_entity(self, match: re.Match[str]) -> str:
        codepoint = int(match.group(1), 16)
        return self._codepoint_to_char(codepoint)

    def _codepoint_to_char(self, codepoint: int) -> str:
        if self._is_valid_xml_codepoint(codepoint):
            return chr(codepoint)
        logger.debug("Descartando referência numérica inválida: %#x", codepoint)
        return ""

    @staticmethod
    def _is_valid_xml_codepoint(codepoint: int) -> bool:
        return (
            codepoint in (0x9, 0xA, 0xD)
            or 0x20 <= codepoint <= 0xD7FF
            or 0xE000 <= codepoint <= 0xFFFD
            or 0x10000 <= codepoint <= 0x10FFFF
        )


class DatasetNormalizer:
    """Turns the dataset XML payload into an ElementTree.Element."""

    def parse(self, dataset_xml: str | None) -> ElementTree.Element | None:
        if not dataset_xml:
            return None

        try:
            return ElementTree.fromstring(dataset_xml)
        except ElementTree.ParseError as exc:
            logger.error(
                "XML retornado pela consulta está inválido: %s",
                exc,
                exc_info=True,
            )
            return None


class DatasetDataFrameBuilder:
    """Converts the dataset XML into a pandas DataFrame."""

    ENCODED_NAME_PATTERN = re.compile(r"_x([0-9A-Fa-f]{4})_")

    def to_dataframe(
        self,
        dataset_root: ElementTree.Element,
        *,
        row_tag: Optional[str] = None,
    ) -> pd.DataFrame:
        rows = self._find_rows(dataset_root, row_tag=row_tag)
        records = [
            {
                self._decode_name(child.tag): (child.text or "").strip()
                for child in row
                if isinstance(child.tag, str)
            }
            for row in rows
        ]

        if not records:
            return pd.DataFrame()

        return pd.DataFrame(records)

    def _find_rows(
        self,
        dataset_root: ElementTree.Element,
        *,
        row_tag: Optional[str],
    ) -> list[ElementTree.Element]:
        if row_tag:
            return dataset_root.findall(f".//{row_tag}")

        direct_children = [
            child
            for child in dataset_root
            if isinstance(child.tag, str) and list(child)
        ]
        if direct_children:
            return direct_children

        candidates = [
            element
            for element in dataset_root.iter()
            if element is not dataset_root
            and isinstance(element.tag, str)
            and list(element)
        ]
        return candidates[:1] if candidates else []

    def _decode_name(self, name: str) -> str:
        return self.ENCODED_NAME_PATTERN.sub(
            lambda match: chr(int(match.group(1), 16)),
            name,
        )

