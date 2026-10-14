# Escopo do produto

## Objetivo

Disponibilizar à Secretaria Municipal de Saúde e à coordenação da APS de Pacujá um painel para monitorar resultados públicos dos Componentes II e III, comparar quadrimestres, identificar indicadores que merecem análise e documentar ações de melhoria.

## Público e limite territorial

- Público principal: gestão municipal e coordenação da APS.
- Recorte fixo: município de Pacujá, Ceará.
- O sistema não fará consultas abertas para outros municípios ou UFs.
- O sistema não usará o Acesso Restrito.

## Fontes e relatórios

1. A automação abre o catálogo público do Siaps.
2. Seleciona o componente de Vínculo e Acompanhamento Territorial e Qualidade.
3. Seleciona CE e apenas Pacujá.
4. Descobre os quadrimestres disponíveis no próprio catálogo, sem lista fixa de anos.
5. Baixa os CSVs públicos oferecidos para equipes e componentes existentes no município.
6. Registra os arquivos originais e suas versões antes de processar os dados.

Na verificação inicial do catálogo, a página apresentou Q2/25, Q3/25 e Q1/26. Para o filtro CE/Pacujá, foram listados relatórios de Vínculo para eSF e relatórios de Qualidade para eMulti, eSB e eSF. A automação deve redescobrir os períodos e tipos a cada execução; esses itens observados não devem ser codificados como lista permanente.

## Atualização

O processo roda mensalmente para verificar se o Siaps publicou períodos ou versões novos. Se a página apresentar somente relatórios quadrimestrais, o painel não deve inventar uma série mensal: exibirá os quadrimestres disponíveis e a data da última verificação. Relatórios mensais, se oferecidos publicamente no mesmo catálogo, serão uma série separada.

## Funcionalidades planejadas

- Arquivo e histórico de CSV por período, equipe e componente.
- Painel geral com quantidade de equipes e classificação por componente.
- Filtros por quadrimestre, tipo de equipe e indicador.
- Série temporal dos resultados publicados.
- Comparação entre período atual e anterior, quando ambos existirem.
- Indicadores de qualidade por equipe, classificação e peso oficial.
- Registro de falhas, alterações de arquivos e data da última sincronização.
- Exportação de dados processados e relatório gerencial.
- Registro manual de ações de melhoria, responsável, prazo e situação.

## Fora do escopo

- Acesso a qualquer tela autenticada ou restrita do Siaps.
- Dados identificáveis ou individuais de usuários do SUS.
- Alterar, enviar ou corrigir dados no Siaps.
- Substituir a publicação oficial do Ministério da Saúde.
- Prever repasse financeiro ou inferir regras não publicadas.
- Emitir orientação clínica individual.

## Requisitos de segurança e qualidade

- A coleta é somente leitura e limitada ao domínio público oficial.
- Nenhuma credencial do Siaps é necessária ou permitida.
- As credenciais próprias do aplicativo, se houver, ficam fora do código e dos CSVs.
- A tela identifica a data, o período e a origem oficial dos dados.
- O importador valida UF, município, tipo de relatório e quadrimestre antes de aceitar um arquivo.
- Erros de formato interrompem a importação sem substituir o último resultado válido.
