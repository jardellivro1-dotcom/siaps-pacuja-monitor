# Manual do Usuário e Guia de Interpretação dos Indicadores

Bem-vindo ao **Monitor de Desempenho da Atenção Primária à Saúde de Pacujá/CE**. Este manual orienta a equipe técnica da Secretaria de Saúde e a Coordenação da APS sobre o uso do painel e a correta interpretação dos indicadores oficiais.

---

## 1. Visão Geral do Painel

O painel é estruturado em seções executivas projetadas para apoiar o planejamento e a tomada de decisão da gestão municipal:

### 1.1. Barra Superior e Filtros Rápidos
- **Seletor de Quadrimestre:** Permite filtrar os dados por um quadrimestre específico (`2026Q1`, `2025Q3`, `2025Q2`, `2025Q1`) ou selecionar **Todos os Períodos** para análise histórica longitudinal.
- **Seletor de Tipo de Equipe:** Filtra os indicadores para equipes de Saúde da Família (`eSF`), Saúde Bucal (`eSB`), equipes Multiprofissionais (`eMulti`) ou visão consolidada (`Todas`).
- **Botão Sincronizar Siaps (🔄):** Dispara a verificação automatizada junto à API pública oficial do Ministério da Saúde.
- **Botão Auditoria & Hashes (🛡️):** Abre a modal de transparência exibindo cada CSV original, com URL de origem, data de coleta, tamanho e assinatura criptográfica SHA-256.

### 1.2. Cartões de Indicadores-Chave (KPIs)
- **Nota Geral Consolidada:** Média ponderada dos Componentes II e III das equipes do município.
- **Componente II (Vínculo e Acompanhamento Territorial):** Classificação das dimensões de Cadastro e Acompanhamento.
- **Componente III (Qualidade do Cuidado):** Nota ponderada dos 15 indicadores da Nota Técnica nº 8/2026.
- **Equipes Homologadas:** Quantidade de equipes ativas avaliadas pelo Siaps em Pacujá.
- **Indicadores de Atenção:** Total de práticas que obtiveram conceito "Regular" ou que sofreram declínio em relação ao quadrimestre anterior.

---

## 2. Gráficos de Evolução Temporal

O painel traz gráficos interativos desenvolvidos com Chart.js para análise de tendências:
- **Gráfico de Linha Longitudinal:** Apresenta a evolução das notas dos Componentes II e III ao longo dos quadrimestres.
- **Alternativa Textual e Tabela:** Em cumprimento aos padrões de acessibilidade (WCAG 2.2 AA), cada visualização gráfica é complementada por tabela analítica de dados, garantindo acesso pleno por leitores de tela e independência de cores.

---

## 3. Guia de Interpretação Correta dos Indicadores

Para evitar conclusões distorcidas na análise dos relatórios oficiais, a equipe técnica deve observar as seguintes premissas:

### 3.1. Diferença entre "Percentual de Equipes Classificadas" e "Percentual de Execução"
- **Percentual de Equipes:** Indica a proporção de equipes do município que atingiram determinada faixa (ex.: 75% das eSF no conceito "Bom").
- **Percentual de Execução / Cobertura:** Representa a taxa efetiva de usuários atendidos pela equipe em relação ao público-alvo (denominador). **Não confunda a quantidade de equipes na faixa com a taxa de cobertura populacional.**

### 3.2. Ausência de Dados vs Desempenho Zero
- Quando uma equipe não tem dados registrados para determinado indicador (por exemplo, ausência de gestantes elegíveis no período para o indicador C3, ou início recente das atividades da eMulti), o Siaps registra ausência (`-`).
- **O sistema preserva a ausência como ausência.** Não interprete um traço ou ausência como nota zero. A ausência reflete falta de registro ou inexistência de evento no período.

### 3.3. Proibição de Inferência Clínica Individual
- Os relatórios do Siaps são agregados no nível da equipe e do município.
- **Nunca tente reconstruir ou deduzir o atendimento de um paciente específico a partir desses números.** O sistema não constitui prontuário e não emite orientações de conduta clínica para usuários.

---

## 4. Gestão do Plano de Ações de Melhoria

A seção **Plano de Ações** permite registrar intervenções da coordenação para elevar os resultados dos indicadores em alerta:

1. **Criar Nova Ação:**
   - Clique em **+ Nova Ação de Melhoria**.
   - Preencha o título da ação (ex.: *"Oficina de busca ativa de gestantes para pré-natal odontológico"*).
   - Indique o responsável institucional (ex.: *"Coordenação de Saúde Bucal"*).
   - Defina o prazo no formato `AAAA-MM-DD`.
   - Selecione a equipe e o indicador prioritário.
   - **Nota de Privacidade:** O sistema possui proteção automatizada contra dados pessoais (LGPD). **Não insira números de CPF ou Cartão SUS (CNS) nas ações.**
2. **Atualizar Situação:**
   - As ações transitam entre as situações: `Pendente`, `Em Andamento` e `Concluído`.
   - O gestor pode alterar a situação diretamente no painel para acompanhar a execução.

---

## 5. Suporte e Manutenção

Para sugestões, dúvidas ou suporte técnico:
- **Gestão Municipal:** Secretaria de Saúde de Pacujá - CE
- **Coordenação:** Coordenação da Atenção Primária à Saúde (APS)
