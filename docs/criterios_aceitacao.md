# Critérios de Aceitação

Este documento estabelece os critérios objetivos de aceitação para cada funcionalidade do **Monitor APS Pacujá**, cobrindo o comportamento esperado em condições normais, casos de borda e cenários de falha.

---

## 1. Coleta e Descoberta de Dados (Ingestion)

- **CA-COL-01 (Descoberta Dinâmica):** A coleta deve consultar dinamicamente a API pública oficial do Siaps (`https://apisiaps.saude.gov.br/api/public/...`), identificando quadrimestres e equipes disponíveis sem listas estáticas pré-fixadas no código.
- **CA-COL-02 (Recorte Territorial Estrito):** Toda requisição ao Siaps deve enviar estritamente os filtros `uf = ["CE"]` e `coMunicipioIbge = ["230990"]` (Pacujá). Nenhuma requisição para outro município ou UF é permitida.
- **CA-COL-03 (Idempotência e Hash SHA-256):** Cada arquivo CSV oficial gerado deve ter seu hash SHA-256 calculado. Se os dados retornados forem idênticos aos já arquivados, o arquivo e o registro de banco não devem ser duplicados, computando o status `unchanged`.
- **CA-COL-04 (Rastreabilidade):** Toda coleta bem-sucedida deve registrar em banco a URL de origem, timestamp ISO em UTC, total de bytes, SHA-256, período, tipo de equipe e número de registros importados.
- **CA-COL-05 (Prevenção de SSRF):** O cliente de coleta deve validar se o endpoint de destino pertence exclusivamente a `https://apisiaps.saude.gov.br/`. Qualquer tentativa de requisição para endereços internos, loopback (`localhost`), esquemas não HTTPs ou outros domínios deve ser abortada imediatamente.

---

## 2. Atualização e Concorrência

- **CA-ATU-01 (Bloqueio de Concorrência):** Duas execuções simultâneas de sincronização não podem ocorrer. Caso uma coleta esteja em andamento, requisições adicionais devem retornar `HTTP 409 Conflict` (ou mensagem informativa de ocupado).
- **CA-ATU-02 (Tolerância a Falhas e Resiliência):** Em caso de instabilidade na rede ou erro 5xx do Siaps, o sistema deve realizar até 3 tentativas com backoff exponencial. Se todas falharem, a base existente deve ser mantida intacta (falha segura).
- **CA-ATU-03 (Detecção de Mudança de Formato):** Caso a resposta do Siaps venha corrompida ou sem os campos essenciais, o parser deve abortar a importação antes de persistir, registrando a anomalia em `sync_history`.

---

## 3. Filtros e Visualização

- **CA-FIL-01 (Filtro Temporal):** O usuário pode filtrar os dados por quadrimestre específico (`2026Q1`, `2025Q3`, etc.) ou visualizar a série consolidada (`all`). Parâmetros com formato inválido devem retornar erro amigável e seguro (`HTTP 400`).
- **CA-FIL-02 (Filtro por Tipo de Equipe):** O usuário pode selecionar `eSF`, `eSB`, `eMulti` ou `todas`. Tipos de equipe não cobertos pela NT 8/2026 (ex.: `eAPP`, `eCR`, `eSFR`) não devem ser processados sob esta regra.
- **CA-FIL-03 (Cards de Indicadores de Atenção):** Indicadores com desempenho classificado como "Regular" ou com queda em relação ao período anterior devem ser destacados automaticamente na lista de atenção para priorização da gestão.

---

## 4. Gráficos e Evolução Temporal

- **CA-GRA-01 (Apresentação Visual e Semântica):** Os gráficos de evolução temporal devem utilizar componentes acessíveis, apresentando legendas claras, eixos rotulados e unidade de medida.
- **CA-GRA-02 (Independência de Cor):** A identificação dos dados e conceitos nos gráficos não deve depender exclusivamente de cores; rótulos de texto, tabelas equivalentes e tooltips informativos devem estar disponíveis (WCAG 1.4.1).
- **CA-GRA-03 (Preservação de Dados Ausentes):** Períodos em que uma equipe ou indicador não teve dados coletados devem ser exibidos como "Sem dado" ou descontinuidade de linha, nunca como valor numérico zero.

---

## 5. Exportação e Auditoria

- **CA-EXP-01 (Sanitização de CSV):** Qualquer exportação ou download de arquivo CSV deve neutralizar injeção de fórmulas (CWE-1236), adicionando apóstrofo antes de células iniciadas por `=`, `+`, `-`, `@`, `\t` ou `\r`.
- **CA-EXP-02 (Proteção de Diretório):** O download de relatórios brutos deve restringir-se estritamente ao diretório `data/raw/` e a nomes validados na lista permitida (`Relatorio_Publico_*.csv`), impedindo qualquer ataque de `path traversal` (`../`).
- **CA-EXP-03 (Backup com Assinatura SHA-256):** O endpoint `/api/export/backup` deve gerar JSON completo com todos os dados normalizados, histórico e metadados, contendo no próprio corpo o hash de integridade SHA-256 de verificação.

---

## 6. Plano de Ação de Melhoria

- **CA-ACO-01 (CRUD Completo):** Gestores devem conseguir criar, listar, alterar status (`pendente`, `em_andamento`, `concluido`) e excluir ações vinculadas a indicadores ou equipes municipais.
- **CA-ACO-02 (Salvaguarda de Privacidade LGPD):** O sistema deve rejeitar no backend qualquer tentativa de inclusão de CPF ou número do Cartão Nacional de Saúde (CNS) nos campos de título, descrição ou responsável (`HTTP 400`).
- **CA-ACO-03 (Validação de Prazo):** O campo de prazo deve aceitar apenas datas válidas no formato ISO `AAAA-MM-DD`.

---

## 7. Situações de Indisponibilidade, Erros e Dados Ausentes

- **CA-ERR-01 (Siaps Fora do Ar):** O painel deve continuar funcionando plenamente em modo offline com a última versão válida dos dados armazenada localmente.
- **CA-ERR-02 (Ausência vs Zero):** O sistema nunca deve converter ausência de dados em valor numérico `0.0`. Indicadores sem registro oficial devem ser exibidos como "Ausente" ou "Incompleto" e acompanhados de justificativa metodológica.
- **CA-ERR-03 (Exclusão Metodológica):** Meses com pagamento suspenso ou sem eventos elegíveis (ex: crianças completando 2 anos) não devem ser computados na média do quadrimestre, conforme determina a NT 8/2026.
