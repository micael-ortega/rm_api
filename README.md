# RM API – Gerador Benefício Odontológico (dependentes)

Ferramentas para consultar o TOTVS RM via SOAP, transformar os resultados em `pandas.DataFrame` e gerar arquivos TXT/CSV usados em rotinas de atualização de benefício odontológico dos dependentes.

## Recursos
- Consumo da operação `RealizarConsultaSQL` do TOTVS RM com autenticação básica.
- Pipeline ETL que higieniza o payload SOAP, normaliza o XML e salva resultados em CSV.
- UI em Tkinter para combinar colaboradores, dependentes e planos, exportando o layout TXT esperado.
- Gerador de TXT parametrizável (separador, cabeçalho) para integrações posteriores.
- Camadas organizadas em `config`, `infra`, `domain` e `ui`, facilitando testes e manutenção.

## Arquitetura em Camadas
- `app/config`: carrega variáveis de ambiente a partir do `.env`, inclusive em builds PyInstaller.
- `app/infra`: gateways SOAP (`SoapClient`, `RMQueryService`) e pipeline ETL (`RMQueryETLPipeline`, `CSVExporter`).
- `app/domain/plano_odonto`: modelos de domínio, repositórios com cache (`pandas`) e gerador de TXT.
- `app/ui/plano_odonto`: interface Tkinter (`OdontoApp`) que orquestra repositórios e geração.
- `app/main.py`: ponto de entrada; abre a UI ou pode ser usado para disparar consultas programaticamente.

## Pré-requisitos
- Python 3.13 (versão usada durante o desenvolvimento; 3.11+ deve funcionar).
- Dependências: `pandas`, `requests`, `python-dotenv`. Instale com:
  ```bash
  pip install pandas requests python-dotenv
  ```
- Ambiente com acesso ao endpoint SOAP do TOTVS RM.

## Configuração
1. Copie `.env.exemple` para `.env` e preencha:
   ```env
   USER=usuario_rm
   PASSWORD=senha
   SOAP_ACTION_ENDPOINT=https://...
   ODONTO_PLANOS_QUERY=INFO.PLODONTO
   ODONTO_DEPENDENTES_QUERY=INFO.DEPENDENTES
   ROW_TAG=DATAFRAME_ROW_TAG
   LOG_LEVEL=INFO
   ```
2. Mantenha `.env` e dados reais fora do versionamento (`.gitignore` já cobre).
3. Ajuste `CSV_OUTPUT_DIR`, `CSV_OUTPUT_ENCODING` e `CSV_INCLUDE_INDEX` se precisar personalizar o pipeline (via `.env`).

## Uso

### Interface gráfica
```bash
python -m app.main
```
- Filtrar colaboradores pelo nome (busca aproximada).
- Selecionar dependentes e planos retornados pelas queries RM.
- Exportar o layout TXT com cabeçalho `CODCOLIGADA;CHAPA;NRODEPEND;CODPLANOODONTOLOGICO;FLAG`.

### Pipeline ETL programático
```python
from app.main import run_query

run_query("INFO.PLODONTO")
```
- Resultado salvo em `consultas_csv/<NOME_DA_QUERY>.csv` (configurável).
- Logs informam quantidade de linhas/colunas e caminho do CSV.

### Gerar executável (opcional)
Há um arquivo `GeradorOdonto.spec` para PyInstaller. Ajuste-o (ou execute `pyinstaller GeradorOdonto.spec`) lembrando-se de **não** embutir o `.env` com credenciais reais nos builds distribuídos.

## Estrutura
```
app/
  config/
  infra/
  domain/
    plano_odonto/
  ui/
    plano_odonto/
  main.py
.env.exemple
GeradorOdonto.spec
consultas_csv/
```

