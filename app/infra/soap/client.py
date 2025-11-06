"""SOAP client abstractions used to call the RM API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from xml.sax.saxutils import escape

from requests import Session
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException

from app.config import ENV
from app.logging import logger


@dataclass(frozen=True)
class SoapOperation:
    """Represents a SOAP operation with its endpoint, action and envelope template."""

    name: str
    endpoint: str
    soap_action: str
    envelope_template: str

    def build_envelope(self, **payload: Any) -> str:
        return self.envelope_template.format(**payload)


class ParametersSerializer:
    """Serialize the <tot:parameters> block based on the given payload."""

    def serialize(self, parameters: Optional[Any]) -> str:
        if parameters in (None, "", {}):
            return "<tot:parameters/>"

        if isinstance(parameters, Mapping):
            payload = ";".join(
                f"{escape(str(key))}={escape(str(value))}"
                for key, value in parameters.items()
            )
        else:
            payload = escape(str(parameters))

        return f"<tot:parameters>{payload}</tot:parameters>"


class SoapEnvelopeBuilder:
    """Builds the SOAP envelope leveraging a configurable parameters serializer."""

    def __init__(self, serializer: Optional[ParametersSerializer] = None) -> None:
        self.serializer = serializer or ParametersSerializer()

    def build(
        self,
        operation: SoapOperation,
        *,
        cod_sentenca: str,
        cod_coligada: str = "0",
        cod_sistema: str = "G",
        parameters: Any = None,
    ) -> str:
        return operation.build_envelope(
            cod_sentenca=escape(cod_sentenca),
            cod_coligada=escape(str(cod_coligada)),
            cod_sistema=escape(cod_sistema),
            parameters=self.serializer.serialize(parameters),
        )


class SoapClient:
    """Handles SOAP requests, reusing a session and optional authentication."""

    def __init__(
        self,
        session: Optional[Session] = None,
        auth: Optional[HTTPBasicAuth] = None,
        default_headers: Optional[dict[str, str]] = None,
    ) -> None:
        self.session = session or Session()
        self.auth = auth
        self.default_headers = default_headers or {
            "Content-Type": "text/xml; charset=utf-8",
        }

    def call(
        self,
        operation: SoapOperation,
        payload: str,
        *,
        extra_headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> str | None:
        headers = {**self.default_headers, **(extra_headers or {})}
        headers["SOAPAction"] = operation.soap_action

        logger.info("Chamando operação SOAP %s", operation.name)
        logger.debug("Envelope SOAP enviado:\n%s", payload)

        try:
            response = self.session.post(
                operation.endpoint,
                data=payload.encode("utf-8"),
                headers=headers,
                auth=self.auth,
                timeout=timeout,
            )
        except RequestException as exc:
            logger.error(
                "Falha ao executar operação SOAP %s: %s",
                operation.name,
                exc,
                exc_info=True,
            )
            raise

        logger.info("Resposta HTTP %s %s", response.status_code, response.reason)
        logger.debug("Headers de resposta: %s", response.headers)

        if not response.content:
            logger.warning(
                "Resposta vazia recebida para a operação %s.",
                operation.name,
            )
            return None

        logger.debug("Payload de resposta:\n%s", response.text)
        return response.text


class RMQueryService:
    """Facade to execute RM SQL queries via SOAP."""

    def __init__(
        self,
        client: SoapClient,
        builder: SoapEnvelopeBuilder,
        operation: SoapOperation,
    ) -> None:
        self.client = client
        self.builder = builder
        self.operation = operation

    def execute(
        self,
        cod_sentenca: str,
        *,
        cod_coligada: str = "0",
        cod_sistema: str = "G",
        parameters: Any = None,
        timeout: Optional[float] = None,
    ) -> str | None:
        envelope = self.builder.build(
            self.operation,
            cod_sentenca=cod_sentenca,
            cod_coligada=cod_coligada,
            cod_sistema=cod_sistema,
            parameters=parameters,
        )
        return self.client.call(
            self.operation,
            envelope,
            timeout=timeout,
        )


def build_rm_service() -> RMQueryService:
    """Factory for a SOAP RM query service configured via environment variables."""
    operation = SoapOperation(
        name="RealizarConsultaSQL",
        endpoint=ENV["SOAP_ACTION_ENDPOINT"],
        soap_action="http://www.totvs.com/IwsConsultaSQL/RealizarConsultaSQL",
        envelope_template="""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:tot="http://www.totvs.com/">
   <soapenv:Header/>
   <soapenv:Body>
      <tot:RealizarConsultaSQL>
         <tot:codSentenca>{cod_sentenca}</tot:codSentenca>
         <tot:codColigada>{cod_coligada}</tot:codColigada>
         <tot:codSistema>{cod_sistema}</tot:codSistema>
         {parameters}
      </tot:RealizarConsultaSQL>
   </soapenv:Body>
</soapenv:Envelope>
""",
    )

    client = SoapClient(
        auth=HTTPBasicAuth(ENV["USER"], ENV["PASSWORD"]),
    )
    builder = SoapEnvelopeBuilder()
    return RMQueryService(client=client, builder=builder, operation=operation)

