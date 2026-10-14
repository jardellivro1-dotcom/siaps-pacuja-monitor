# Guia de Operação, Monitoramento, Backup e Recuperação

Este documento estabelece os procedimentos operacionais para garantir a alta disponibilidade, integridade, monitoramento contínuo e recuperação de desastres do **Monitor APS Pacujá**.

---

## 1. Monitoramento e Saúde da Aplicação

O sistema provê endpoints dedicados para verificação automatizada por sistemas de orquestração, monitoramento (ex: Prometheus, Uptime Kuma) ou auditoria manual:

### 1.1. Health Check (`GET /healthz`)
- **Finalidade:** Verifica se o processo web está ativo e se a conexão com o banco de dados SQLite está operacional.
- **Resposta:**
  ```json
  {
    "status": "ok",
    "application": "Monitor APS Pacujá",
    "version": "1.0.0",
    "database": "connected",
    "environment": "production",
    "timestamp": "2026-10-14T04:15:00.000000+00:00"
  }
  ```
- **Códigos de Retorno:**
  - `200 OK`: Serviço saudável e banco acessível.
  - `503 Service Unavailable`: Falha de conexão ou corrupção no arquivo do banco de dados.

### 1.2. Status dos Dados e Auditoria (`GET /api/status`)
- **Finalidade:** Retorna a data da última coleta bem-sucedida, período mais recente disponível, total de arquivos brutos arquivados e integridade dos hashes SHA-256.

---

## 2. Política e Rotina de Backup

### 2.1. Backup Integral via API (`GET /api/export/backup`)
O sistema disponibiliza um endpoint seguro que exporta uma cópia estruturada em JSON contendo:
- Metadados do município (Pacujá / CE - 230990);
- Versão da metodologia (Nota Técnica nº 8/2026);
- Tabela de equipes municipais cadastradas;
- Catálogo de arquivos brutos e hashes SHA-256;
- Histórico completo de sincronizações e auditorias;
- Resultados de dimensões CVAT e indicadores de qualidade;
- Planos de ação de melhoria;
- **Hash de Integridade SHA-256 (`sha256_integrity`)** calculado diretamente sobre o payload serializado, garantindo que o backup não sofreu alteração pós-geração.

### 2.2. Backup em Nível de Arquivo
Para preservação física completa, recomenda-se a cópia periódica (diária ou semanal) dos seguintes diretórios:
- `data/siaps_monitor.db` (Banco de dados estruturado SQLite);
- `data/raw/` (Todos os arquivos CSV originais do Ministério da Saúde).

---

## 3. Procedimento de Restauração (Disaster Recovery)

Em caso de falha de hardware, corrupção de sistema de arquivos ou exclusão acidental:

1. **Parar a aplicação:**
   ```bash
   # Encerrar o processo do servidor web
   ```
2. **Restaurar os arquivos brutos:**
   Copie a pasta `data/raw/` do backup mais recente para o diretório de produção.
3. **Restaurar o banco de dados SQLite:**
   Copie o arquivo `siaps_monitor.db` para `data/siaps_monitor.db`.
4. **Verificar a integridade do banco:**
   ```bash
   .venv\Scripts\python.exe -c "import sqlite3; conn = sqlite3.connect('data/siaps_monitor.db'); print(conn.execute('PRAGMA integrity_check').fetchall())"
   ```
   *O resultado deve ser `[('ok',)]`.*
5. **Re-executar os testes unitários:**
   ```bash
   .venv\Scripts\python.exe -m unittest discover -s tests -v
   ```
6. **Reiniciar o serviço:**
   Inicie a aplicação e verifique se `GET /healthz` retorna `status: "ok"`.

---

## 4. Plano de Resposta a Incidentes

| Cenário de Incidente | Sintoma | Procedimento Operacional Padrão |
|---|---|---|
| **Indisponibilidade do Siaps Oficial** | Sincronização falha com timeout ou HTTP 5xx | O sistema mantém a última versão válida dos dados inalterada no banco. O painel continua operando normalmente em modo leitura. Nenhum dado é perdido. Registrar a indisponibilidade no histórico de sincronização. |
| **Mudança no Formato dos Relatórios do Siaps** | Parser acusa ausência de colunas esperadas ou cabeçalho inválido | A importação é abortada imediatamente com erro seguro. O arquivo bruto com o novo formato é preservado para análise pela equipe de desenvolvimento em `data/raw/`. O banco não é alterado até que os testes com o novo formato sejam aprovados. |
| **Concorrência ou Tentativas Simultâneas de Sincronização** | Usuário clica repetidamente no botão "Sincronizar" | O context manager `SyncLockContext` bloqueia a segunda requisição, retornando `HTTP 409 Conflict` ("Sincronização já em andamento"). Não há risco de travamento ou duplicação. |
| **Divergência de Hash SHA-256** | O arquivo baixado tem conteúdo diferente com mesmo nome | O sistema detecta a diferença no SHA-256, arquiva a nova versão e registra a atualização na trilha de auditoria sem sobrescrever cegamente o histórico anterior. |
