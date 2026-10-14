# Governança de Privacidade e Tratamento de Dados (LGPD)

Este documento estabelece as diretrizes de privacidade, inventário de dados e conformidade com a **Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709/2018 - LGPD)** e as orientações da **Autoridade Nacional de Proteção de Dados (ANPD)** no âmbito do **Monitor APS Pacujá**.

---

## 1. Princípios Aplicados

- **Finalidade:** O tratamento de dados destina-se exclusivamente ao planejamento, monitoramento gerencial e auditoria pública dos resultados do cofinanciamento federal da Atenção Primária à Saúde em Pacujá/CE.
- **Necessidade e Minimização:** O aplicativo opera exclusivamente com dados agregados por equipe de saúde e município. **Não há tratamento de prontuários, dados sensíveis de saúde de usuários do SUS ou identificadores de pacientes.**
- **Transparência:** Todos os dados processados provêm do catálogo de acesso público do Ministério da Saúde (Siaps), acessíveis sem necessidade de credenciais restritas.

---

## 2. Inventário de Dados

| Categoria de Dado | Natureza | Finalidade | Base Legal (LGPD) | Retenção / Descarte |
|---|---|---|---|---|
| **Resultados do Siaps** (Percentuais, faixas, conceitos, totais agregados) | Dados Públicos Institucionais (não pessoais) | Acompanhamento do cofinanciamento da APS de Pacujá | Execução de políticas públicas (Art. 7º, III) | Histórico permanente para análise longitudinal |
| **Metadados de Equipes e Estabelecimentos** (INE, CNES, nome da equipe) | Dados Públicos Cadastrais do CNES | Identificação e agrupamento das unidades de saúde | Execução de políticas públicas (Art. 7º, III) | Atualizado a cada nova competência do Siaps |
| **Plano de Ações de Melhoria** (Título, descrição da intervenção gerencial, prazo) | Dados Administrativos | Gestão da melhoria contínua da coordenação da APS | Interesse legítimo / Gestão pública (Art. 7º, IX) | Retido enquanto a ação estiver ativa ou arquivado após conclusão |
| **Responsável pela Ação** (Ex.: "Coordenação da APS", "Enfermeiro da ESF Bom Gosto") | Dado Institucional / Cargo funcional | Atribuição de responsabilidade pelas metas | Execução de atribuições do cargo | Descartado ou editado conforme alteração da gestão |
| **Trilha de Auditoria** (SHA-256, horário UTC, URLs públicas do Siaps) | Metadados Técnicos de Integridade | Comprovação de autenticidade dos dados oficiais | Cumprimento de obrigação legal / Rastreabilidade | Histórico auditável permanente |

---

## 3. Proibição Absoluta de Dados de Pacientes

Em cumprimento rigoroso à **Regra nº 3 do AGENTS.md** e ao Art. 11 da LGPD (dados pessoais sensíveis referentes à saúde):
1. **É terminantemente vedado** armazenar, processar ou transitar números de Cadastro de Pessoas Físicas (CPF), números do Cartão Nacional de Saúde (CNS), nomes de pacientes, endereços residenciais ou diagnósticos clínicos individuais no sistema.
2. O aplicativo não possui e nunca possuirá tabelas, colunas ou integrações com prontuários eletrônicos individuais (PEC e-SUS APS, BPA-I ou similares).

---

## 4. Medidas Técnicas Automatizadas de Salvaguarda

Para mitigar o risco de operadores inserirem inadvertidamente identificadores de usuários nos campos de texto do plano de ação:
- O módulo `siaps/validators.py` executa o interceptador `_check_lgpd_sensitive_data()` em todas as requisições de criação ou atualização (`POST/PUT /api/actions`).
- Expressões regulares especializadas barram imediatamente requisições que contenham padrões de CPF (`\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b`) ou Cartão SUS / CNS (`\b[12789]\d{14}\b`).
- A requisição é rejeitada com `HTTP 400 Bad Request` acompanhada de mensagem formal de violação de privacidade, impedindo a gravação no banco de dados.

---

## 6. Scanner Periódico Automatizado e Rotina de Expurgo

Além da validação em tempo de inserção, o sistema conta com:
- **Scanner Automatizado Noturno (`siaps/privacy.py`):** Integrado ao daemon agendador (`scripts/scheduler_daemon.py`), varre todas as tabelas de texto livre (`improvement_actions` e `audit_log`) em busca de CPFs, CNS ou telefones que possam ter sido introduzidos acidentalmente.
- **Rotina de Expurgo Imediato (`purge_privacy_violation`):** Em caso de detecção de dado sensível, substitui instantaneamente o registro por texto de redação padronizado (`[CONTEUDO EXPURGADO POR MOTIVO DE PRIVACIDADE LGPD]`) e gera notificação no log de auditoria.
- **Relatório de Conformidade:** Disponível programaticamente via `scan_database_for_privacy_violations()`, com ateste de conformidade.

---

## 7. Direitos dos Titulares e Contato com a Gestão

Qualquer dúvida ou solicitação referente ao tratamento de dados administrativos no âmbito do Monitor APS Pacujá pode ser encaminhada à:

- **Secretaria Municipal de Saúde de Pacujá - Ceará**
- **Setor Responsável:** Coordenação da Atenção Primária à Saúde
- **E-mail institucional:** saude@pacuja.ce.gov.br
