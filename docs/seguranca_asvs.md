# Avaliação de Riscos de Segurança e Controles OWASP ASVS

Este documento consolida a análise de riscos de segurança e a implementação de controles defensivos no **Monitor APS Pacujá**, utilizando como referência o padrão **OWASP Application Security Verification Standard (ASVS v4.0.3)** em conformidade com as orientações do Ministério da Saúde e as regras de governança do projeto.

---

## 1. Modelo de Ameaças (Threat Model)

| Vetor de Ataque / Risco | Impacto Potencial | Controle Implementado no Código | Status de Verificação |
|---|---|---|---|
| **SSRF (Server-Side Request Forgery)** | Consulta a serviços internos ou destinos não autorizados | Validação estrita de URL em `_validate_safe_url()` restringindo unicamente a `https://apisiaps.saude.gov.br/` | Testado em `TestSSRFProtection` |
| **SQL Injection** | Extração ou corrupção da base de dados local | Uso exclusivo de consultas parametrizadas (`sqlite3` com placeholders `?`). Zero concatenação de strings em SQL | Verificado em `siaps/services.py` e `siaps/ingestion.py` |
| **XSS (Cross-Site Scripting)** | Injeção de scripts no navegador de gestores | Escape automático por padrão no Jinja2 (`templates/index.html`) e função defensiva `escapeHtml()` no frontend JavaScript | Testado e verificado |
| **Path Traversal / Acesso Indevido a Arquivos** | Download de arquivos do sistema operacional | Whitelist rigorosa de nomes (`validate_csv_filename`) e verificação `is_relative_to(raw_dir)` no endpoint `/api/raw-files/<filename>/download` | Testado em `test_raw_files_endpoint_and_download_security` |
| **CSV Formula Injection (CWE-1236)** | Execução de comandos no Excel/Calc ao abrir relatórios | Sanitização com prefixo de apóstrofo `'` em `sanitize_csv_formula()` para campos com `=`, `+`, `-`, `@`, `\t`, `\r` | Testado em `test_sanitize_csv_formula` |
| **Exposição de Dados Pessoais (LGPD)** | Vazamento ou inclusão indevida de dados de pacientes | Interceptador regex em `validate_action_payload` bloqueando números de CPF e CNS/SUS em campos de texto livre | Testado em `test_validate_action_payload_rejects_cpf_cns_lgpd` |
| **Condição de Corrida / Concorrência de Coleta** | Corrupção de base ou sobrecarga da fonte pública | Context manager `SyncLockContext` (mutex) que bloqueia execuções simultâneas e retorna `HTTP 409 Conflict` | Testado em `TestConcurrencyLock` |
| **Ataque de Força Bruta / Disparo Não Autorizado** | Degradação da fonte pública ou alteração de planos | Autorização proporcional via `SIAPS_ADMIN_KEY` e cabeçalho `X-Admin-Key` em rotas de mutação (`POST /api/sync`, `POST/PUT/DELETE /api/actions`) | Testado em `TestProportionalAuthorization` |

---

## 2. Mapeamento de Controles OWASP ASVS

### V1 — Arquitetura, Design e Modelagem de Ameaças
- **V1.1.1:** O escopo da aplicação é estritamente delimitado a dados públicos agregados de Pacujá/CE.
- **V1.4.1:** Separação arquitetural nítida entre interface (`templates/` e `static/`), API (`app.py`), serviços de domínio (`siaps/services.py`), motor de cálculo metodológico (`siaps/calculations.py`), validação (`siaps/validators.py`) e ingestão (`siaps/ingestion.py`).
- **V1.14.1:** Defesa em profundidade com validação no cliente e validação obrigatória no servidor.

### V2 — Autenticação e Autorização Proporcional
- **V2.1.1:** O painel de consulta a dados públicos de saúde permanece acessível à sociedade e aos técnicos da saúde sem barreiras desnecessárias, assegurando a transparência pública do SUS.
- **V4.1.1:** Operações administrativas que geram escrita ou alteração de estado (disparo de sincronização e modificações no plano de ações) requerem validação no servidor via `SIAPS_ADMIN_KEY` (`X-Admin-Key`).

### V5 — Validação e Sanitização de Entradas
- **V5.1.1:** Todas as entradas da aplicação (filtros de query string, corpos JSON e nomes de arquivo) são tipadas e validadas por expressões regulares restritivas (`validate_period`, `validate_team_type`, `validate_csv_filename`, `validate_action_payload`).
- **V5.1.2:** Limites de tamanho de string são estritamente aplicados (título até 200 caracteres, descrição até 2000 caracteres, responsável até 100 caracteres).
- **V5.3.1:** Proteção contra CSV Formula Injection em todas as gerações de planilhas.

### V8 — Proteção de Dados e Criptografia
- **V8.2.1:** A comunicação com o Siaps público utiliza HTTPS obrigatório com verificação estrita de certificados TLS (`ssl.create_default_context()`).
- **V8.3.1:** Todos os arquivos CSV originais e backups exportados possuem hash criptográfico SHA-256 para auditoria e detecção de adulteração.
- **V8.4.1:** Nenhum dado clínico, prontuário ou identificador de paciente é armazenado ou processado.

### V13 — Segurança nas Comunicações e Cabeçalhos HTTP
O decorador `apply_security_headers` injeta automaticamente em todas as respostas HTTP:
- `Content-Security-Policy`: Restringe scripts e estilos a fontes confiáveis (`'self'`, Google Fonts e CDN Chart.js oficial).
- `X-Content-Type-Options: nosniff`: Previne interpretação MIME incorreta pelo navegador.
- `X-Frame-Options: DENY`: Impede ataques de clickjacking em iframes.
- `Referrer-Policy: strict-origin-when-cross-origin`: Minimiza vazamento de cabeçalhos referer.
- `Permissions-Policy: geolocation=(), camera=(), microphone=()`: Desativa sensores desnecessários.
- `Strict-Transport-Security (HSTS)`: Força conexões HTTPS quando em ambiente de produção.

### V14 — Configuração e Gerenciamento de Segredos
- **V14.1.1:** Nenhuma credencial, senha, token ou chave de API está hardcoded no código ou repositório. Todas as configurações sensíveis são lidas de variáveis de ambiente (`SIAPS_ADMIN_KEY`, `SIAPS_SECRET_KEY`, `FLASK_ENV`).
- **V14.2.1:** Arquivos `.db`, `.sqlite3`, `.env` e arquivos brutos locais são mantidos no `.gitignore` para proteção do repositório.
