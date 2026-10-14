# Histórico de Mudanças e Versões (Changelog)

Todas as alterações notáveis deste projeto são registradas neste documento, seguindo os princípios de [Versionamento Semântico (SemVer)](https://semver.org/lang/pt-BR/).

---

## [1.0.0] - 2026-10-14

### Adicionado
- **Motor Metodológico NT 8/2026:**
  - Implementação exata dos pesos e cálculos para equipes `eSF`, `eAP`, `eSB` e `eMulti`.
  - Tratamento correto de limites e faixas: Componente II (Ótimo >8.5, Bom >=7.0 e <=8.5, Suficiente >=5.0 e <7.0, Regular <5.0) e Componente III (Ótimo >7.5, Bom >=5.0 e <=7.5, Suficiente >2.5 e <5.0, Regular <=2.5).
  - Exclusão explícita de tipos de equipe não cobertos (`eAPP`, `eCR`, `eSFR`).
  - Preservação estrita de ausência de dados (sem conversão para zero).
- **Ingestão Pública Oficial & Idempotência:**
  - Coleta automatizada a partir do catálogo público do Siaps (`apisiaps.saude.gov.br`).
  - Filtro restrito ao município de Pacujá/CE (IBGE `230990`).
  - Geração e arquivamento de quatro relatórios CSV oficiais com assinaturas SHA-256.
  - Idempotência verificada por hash e comparação em nível de linha, evitando duplicação de dados.
- **Segurança e Controles OWASP ASVS:**
  - Cabeçalhos de segurança HTTP automáticos (`Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `HSTS`, `Permissions-Policy`).
  - Prevenção rigorosa de SSRF restringindo conexões externas a `https://apisiaps.saude.gov.br/`.
  - Consultas SQL 100% parametrizadas prevenindo SQL Injection.
  - Sanitização de células contra CSV Formula Injection (CWE-1236).
  - Prevenção contra Path Traversal no download de arquivos brutos.
  - Autorização proporcional via `SIAPS_ADMIN_KEY` (`X-Admin-Key`) para rotas administrativas.
- **Privacidade e LGPD:**
  - Interceptador com regex no backend bloqueando inclusão inadvertida de CPF e CNS/SUS em campos de planos de ação.
  - Zero armazenamento de dados de prontuário ou identificadores clínicos.
- **Acessibilidade WCAG 2.2 Nível AA:**
  - Indicador de foco visível (`:focus-visible`) de alto contraste em todos os elementos interativos.
  - Link de salto para o conteúdo principal (`.skip-link`).
  - Independência de cor em gráficos através de tabelas textuais complementares.
  - Suporte à preferência do sistema operacional para redução de movimento (`prefers-reduced-motion`).
- **Operação, Auditoria e Backup:**
  - Endpoint de saúde `/healthz` com verificação de conectividade do SQLite.
  - Endpoint de exportação `/api/export/backup` gerando JSON integral com hash SHA-256 no payload.
  - Bloqueio de concorrência por mutex (`SyncLockContext`) evitando coletas simultâneas.
- **Suíte de Testes Automatizados:**
  - 38 testes automatizados cobrindo cálculos metodológicos, parser de CSV, endpoints da API, cabeçalhos de segurança, validação de entradas, bloqueador LGPD, mutex de concorrência e integridade de backup.
