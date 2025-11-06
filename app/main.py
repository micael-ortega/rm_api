from __future__ import annotations

from app.infra.soap.client import build_rm_service
from app.infra.soap.pipeline import build_pipeline
from app.logging import logger
from app.ui.plano_odonto import main as odontologia_ui_main


def run_query(query_name: str) -> None:
    """Execute uma consulta RM e registra o resultado no CSV configurado."""
    rm_service = build_rm_service()
    soap_payload = rm_service.execute(query_name, timeout=None)

    if not soap_payload:
        logger.error("Consulta nao retornou payload.")
        return

    pipeline = build_pipeline()
    result = pipeline.run(soap_payload, query_name)
    if not result:
        logger.error("Pipeline ETL nao produziu dados.")
        return

    dataframe, csv_path = result
    logger.info(
        "DataFrame com %s linhas e %s colunas. CSV salvo em %s",
        len(dataframe),
        len(dataframe.columns),
        csv_path,
    )
    print(dataframe.head())


def main() -> None:
    """Inicializa a interface do gerador TXT odontologico."""
    odontologia_ui_main()


if __name__ == "__main__":
    main()

