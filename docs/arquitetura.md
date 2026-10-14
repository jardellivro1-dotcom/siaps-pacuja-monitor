# Arquitetura proposta

## Escolha para a primeira versão

Aplicação Flask em Python, HTML/CSS e JavaScript com Chart.js. Python facilita trabalhar com CSV, validação e cálculos reproduzíveis; uma interface web leve reduz o número de ferramentas que Jardel precisará configurar no Windows. O projeto pode evoluir para hospedagem e banco PostgreSQL sem mudar as regras de domínio.

## Fluxo de dados

```text
Siaps público
    ↓ leitura pública, filtros CE + Pacujá
Capturador Playwright (sem autenticação)
    ↓ arquivos CSV originais + metadados + SHA-256
Validador e normalizador Python
    ↓ tabelas SQLite local / PostgreSQL hospedado
Serviço de cálculos versionado conforme NT 8/2026
    ↓
Painel Flask + gráficos + trilha de atualização
```

## Componentes

1. **Capturador:** navega somente na página pública; valida domínio, filtros e seleção do município; baixa o CSV escolhido no catálogo.
2. **Arquivo bruto:** `data/raw/` na execução local. Em hospedagem, migrar para armazenamento persistente de objetos; o disco efêmero do servidor não será tratado como arquivo durável.
3. **Validador:** verifica extensão, cabeçalho, equipe, componente, UF, município, período, campos obrigatórios e duplicidade por hash.
4. **Normalizador:** converte percentuais e classificações para um esquema interno sem perder o texto e as colunas originais.
5. **Cálculo:** módulo separado com versão da regra e testes para médias, elegibilidade, pesos e limites de classificação.
6. **Painel:** apresenta dados por quadrimestre/equipe/indicador, sempre citando o arquivo fonte e a data da última verificação.
7. **Agendador:** verificação mensal e execução manual local. Em hospedagem, usar tarefa agendada separada do servidor web; não confiar em um processo web que possa dormir.

## Persistência e histórico

O protótipo usa estrutura de diretórios para arquivos brutos e pode iniciar com SQLite. Antes de uso compartilhado pela Secretaria, migrar para PostgreSQL, adicionar autenticação e separar permissões de administração e leitura. A conta que escreve dados deve existir somente no processo servidor/agendador. Nunca enviar uma chave de serviço ao navegador.

Cada execução deve guardar:

- `source_url` público;
- `fetched_at` em UTC e horário local de exibição;
- `uf`, código/nome do município, componente, tipo de equipe e quadrimestre;
- nome e SHA-256 do CSV bruto;
- versão do parser e da metodologia;
- resultado `success`, `unchanged`, `rejected` ou `failed` e motivo;
- linhas importadas/rejeitadas e avisos.

## Agendamento

O trabalho roda mensalmente, com opção de execução manual. Ele compara os quadrimestres encontrados no catálogo com os já arquivados, baixa itens novos e rebaixa um item se o hash público mudar. Não cria uma linha para período ausente, não força exportações repetidas desnecessárias e registra a data de checagem mesmo quando não houver novidade.

## Estratégia de falha segura

- Se o domínio ou a página mudar, não seguir redirecionamento para login ou área restrita; interromper e marcar a coleta como falha.
- Se os filtros não puderem ser confirmados como `CE` e `PACUJÁ`, não baixar.
- Se o CSV mudar de esquema, arquivar o arquivo bruto e bloquear a atualização normalizada até mapear e testar as colunas.
- Nunca substituir o último conjunto válido por uma importação parcial ou inválida.
- Repetir a execução de modo idempotente, sem duplicar a mesma versão.
