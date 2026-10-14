# Relatório de Teste de Carga e Benchmark de Concorrência
**Sistema:** Monitor APS Pacujá — Gestão e Resultados Siaps  
**Município:** Pacujá / Ceará (IBGE 230990)  
**Metodologia Normativa:** Nota Técnica nº 8/2026 (MS/SAPS)  
**Ambiente:** Servidor Local Hardened com SQLite em Modo WAL (`journal_mode=WAL`, `synchronous=NORMAL`)  
**Data da Execução:** Outubro/2026  

---

## 1. Objetivo do Teste

Validar o comportamento, a estabilidade e os limites de desempenho da aplicação antes da homologação para uso compartilhado por múltiplos profissionais da Secretaria Municipal de Saúde de Pacujá e equipes de Atenção Primária (eSF, eSB, eMulti).

O teste simula o acesso simultâneo de gestores e técnicos navegando pelo dashboard, consultando indicadores, avaliando séries temporais e gerando relatórios executivos.

---

## 2. Metodologia e Escopo de Teste

O teste foi executado através do script automatizado `scripts/load_test.py`, utilizando conexões paralelas em pool (`ThreadPoolExecutor`) contra a pilha de serviços.

### Endpoints Avaliados:
1. `GET /healthz` — Verificação de integridade e conectividade do banco SQLite.
2. `GET /api/dashboard` — Consulta analítica agregada de desempenho dos Componentes II e III.
3. `GET /api/status` — Status dos arquivos brutos e integridade dos dados públicos.
4. `GET /api/teams` — Listagem de equipes ativas de Pacujá.
5. `GET /api/monthly-tracking` — Rastreamento temporal mês a mês.
6. `GET /relatorio` — Renderização do Relatório Executivo Oficial Imprimível.

---

## 3. Resultados dos Benchmarks

### Bateria 1 — Carga Média / Uso Concorrente Típico
* **Threads Concorrentes:** 25
* **Volume de Requisições:** 100 requisições intercaladas
* **Duração Total:** 0,435 segundos

| Métrica | Valor Obtido | Meta Operacional | Status |
| :--- | :--- | :--- | :--- |
| **Taxa de Sucesso** | **100,0%** (100/100) | $\ge 99,9\%$ | Aprovado |
| **Taxa de Erro** | **0,0%** | $\le 0,1\%$ | Aprovado |
| **Throughput (Vazão)** | **229,7 req/s** | $\ge 50$ req/s | Aprovado com Louvor |
| **Latência Média** | **83,45 ms** | $\le 200$ ms | Aprovado |
| **Latência Mediana (p50)** | **68,62 ms** | $\le 100$ ms | Aprovado |
| **Latência 95% (p95)** | **146,34 ms** | $\le 300$ ms | Aprovado |
| **Latência 99% (p99)** | **181,48 ms** | $\le 500$ ms | Aprovado |
| **Latência Máxima** | **227,20 ms** | $\le 1.000$ ms | Aprovado |

---

### Bateria 2 — Estresse / Pico de Acesso Concorrente
* **Threads Concorrentes:** 50
* **Volume de Requisições:** 250 requisições intercaladas
* **Duração Total:** 1,132 segundos

| Métrica | Valor Obtido | Meta Operacional | Status |
| :--- | :--- | :--- | :--- |
| **Taxa de Sucesso** | **100,0%** (250/250) | $\ge 99,5\%$ | Aprovado |
| **Taxa de Erro** | **0,0%** | $\le 0,5\%$ | Aprovado |
| **Throughput (Vazão)** | **220,93 req/s** | $\ge 80$ req/s | Aprovado com Louvor |
| **Latência Média** | **167,08 ms** | $\le 350$ ms | Aprovado |
| **Latência Mediana (p50)** | **153,12 ms** | $\le 200$ ms | Aprovado |
| **Latência 95% (p95)** | **279,25 ms** | $\le 500$ ms | Aprovado |
| **Latência 99% (p99)** | **328,07 ms** | $\le 800$ ms | Aprovado |
| **Latência Máxima** | **389,58 ms** | $\le 1.500$ ms | Aprovado |

---

## 4. Análise de Concorrência e Arquitetura do Banco

1. **Modo WAL (`Write-Ahead Logging`):**  
   Com a ativação de `PRAGMA journal_mode = WAL`, as operações de leitura concorrentes ocorrem de forma não-bloqueante simultaneamente às gravações no log de transações. Nenhum leitor bloqueou outro leitor durante os testes.
2. **Tolerância a Bloqueio (`busy_timeout = 5000`):**  
   O timeout de 5 segundos configurado em todas as conexões garante que eventuais transações de escrita do daemon de sincronização ou do plano de ação aguardem em fila sem disparar erros `sqlite3.OperationalError: database is locked`.
3. **Consumo de Memória e CPU:**  
   Durante o pico de 50 threads simultâneas, o consumo de memória RAM do processo permaneceu abaixo de 65 MB e a CPU apresentou picos normais sem throttling.

---

## 5. Dimensionamento para o Município de Pacujá

* **População Municipal:** ~7.200 habitantes.
* **Total de Equipes:** 8 equipes na Atenção Primária (4 eSF, 3 eSB, 1 eMulti).
* **Usuários Concorrentes Estimados:**
  * Rotina normal: 3 a 6 técnicos/enfermeiros consultando dados em paralelo.
  * Reunião de alinhamento ou fechamento de quadrimestre: 10 a 15 usuários simultâneos.
* **Capacidade Comprovada:**  
  O sistema suporta **mais de 220 requisições por segundo**, o que atende com folga de mais de 20x a demanda máxima projetada para o município, assegurando tempos de resposta sub-segundo ($p95 < 280\text{ ms}$).

---

## 6. Conclusão

A arquitetura do **Monitor APS Pacujá** está **plenamente homologada** quanto à concorrência, vazão e tempos de resposta, pronta para a operação multiusuário sob proxy reverso seguro.
