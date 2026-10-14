# Monitor APS Pacujá

Aplicação web de portfólio para acompanhar, com transparência, os resultados públicos dos Componentes II (Vínculo e Acompanhamento Territorial) e III (Qualidade) do Siaps para o município de Pacujá, Ceará.

## Estado do projeto

Esta é a fundação do projeto: documentação de escopo e metodologia, uma tela inicial executável e verificações básicas. Ainda não há CSV real importado nem cálculo publicado pelo app. A próxima etapa é implementar e validar a captura dos arquivos exclusivamente pela área pública do Siaps.

## Regras de escopo

- Origem permitida: `https://siaps.saude.gov.br/publico` e arquivos públicos baixados a partir dela.
- Filtros fixos do projeto: UF CE e município Pacujá.
- Não acessar login, rotas ou conteúdo restritos.
- Não importar dados individuais de pacientes.
- CSV original e arquivo processado terão registro de origem, período, data de captura e hash.
- Ausência de informação não será convertida em zero.

## Executar no Windows

Requer Python 3.11 ou superior.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Abra `http://127.0.0.1:5000` no navegador. Para executar os testes:

```powershell
python -m unittest discover -s tests -v
```

## Pastas

```text
data/raw/          CSV originais baixados do Siaps
data/processed/    dados normalizados e prontos para o painel
docs/              escopo, metodologia e arquitetura
scripts/           futura automação de captura e importação
static/            estilos e recursos da interface
templates/         telas HTML
tests/             verificações automatizadas
```

## Fonte oficial

- [Relatórios Públicos do Siaps](https://siaps.saude.gov.br/publico)
- Nota Técnica nº 8/2026-DEAPS/SAPS/MS, publicada em 02/10/2026.
- Portaria GM/MS nº 3.493/2024 e alterações citadas na Nota Técnica.

O painel será uma ferramenta de monitoramento gerencial. O resultado oficial continua sendo o publicado pelo Ministério da Saúde; o sistema deve mostrar a regra usada e a trilha de auditoria de cada atualização.
