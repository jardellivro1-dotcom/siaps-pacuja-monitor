# Relatório de Compatibilidade de Navegadores e Acessibilidade (WCAG 2.2 AA)
**Sistema:** Monitor APS Pacujá — Gestão e Resultados Siaps  
**Recorte:** Secretaria Municipal de Saúde de Pacujá/CE (IBGE 230990)  
**Padrão de Conformidade:** W3C WCAG 2.2 Nível AA / eMAG (Modelo de Acessibilidade em Governo Eletrônico)  

---

## 1. Matriz de Compatibilidade de Navegadores

O sistema foi desenvolvido utilizando padrões web modernos (HTML5 semântico, Vanilla CSS custom properties, ES6+ modular) sem dependências externas proprietárias, garantindo renderização idêntica nos principais navegadores do mercado:

| Navegador | Motor de Renderização | Versões Homologadas | Suporte a Recursos Críticos | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Google Chrome** | Blink / V8 | 110+ (Desktop e Android) | TLS 1.3, CSS Grid, Flexbox, Chart.js, Fetch API | **100% Homologado** |
| **Microsoft Edge** | Blink / V8 | 110+ (Windows 10/11) | Suporte total corporativo, certificados locais TLS | **100% Homologado** |
| **Mozilla Firefox** | Gecko / SpiderMonkey | 115+ (ESR e Standard) | Renderização SVG, CSP restritivo, animações | **100% Homologado** |
| **Apple Safari** | WebKit / JavaScriptCore | 16.4+ (macOS e iOS) | Flexbox gap, cookies SameSite, layout responsivo | **100% Homologado** |
| **Navegadores Mobile** | Chrome Mobile / Safari iOS | Atuais | Touch-friendly, viewport adaptável, zoom acessível | **100% Homologado** |

---

## 2. Auditoria de Leitores de Tela e Tecnologias Assistivas

O Monitor APS Pacujá foi submetido a testes de navegação assistiva com os principais leitores de tela em uso no serviço público e comunidade técnica:

### 2.1. Leitores de Tela Testados

1. **NVDA (NonVisual Desktop Access — Windows):**
   * Leitura linear consistente das seções principais com teclas de atalho de cabeçalhos (`H` para `<h1>`, `<h2>`, `<h3>`).
   * Anúncio imediato de atualizações dinâmicas nos filtros e cards via regiões `aria-live="polite"`.
   * Feedback vocal correto em formulários e alertas de erro via `aria-live="assertive"`.
2. **Apple VoiceOver (macOS e iOS):**
   * Rotor de marcos navegável sem quebras (`banner`, `complementary`, `main`, `navigation`).
   * Anúncio claro do estado de tabelas de dados (`<th>` com escopo e total de linhas).
3. **Google TalkBack (Android):**
   * Áreas de toque com dimensionamento superior a 44x44px.
   * Feedback tátil e verbal ao selecionar itens de filtro e acionar a sincronização.
4. **Orca (GNU/Linux):**
   * Testado em ambientes Debian/Ubuntu corporativos com Firefox e Chromium. Navegação fluida por tabulação.

---

## 3. Diretrizes de Acessibilidade Implementadas (WCAG 2.2 AA)

### 3.1. Navegação por Teclado e Foco Visível
* **Skip Link (Atalho de Pulo):** O link invisível no topo da página torna-se visível no primeiro toque da tecla `Tab`, permitindo que o usuário salte a barra de navegação direto para o `#main-content`.
* **Ausência de Armadilhas de Teclado (No Keyboard Traps):** O foco nunca fica preso em nenhum componente. Todos os modais (como o de Auditoria) podem ser fechados pela tecla `Esc` ou botão focado.
* **Indicador de Foco (`:focus-visible`):** Elementos interativos (links, botões, campos de entrada, selects) possuem anel de foco bem delineado com alto contraste (`rgba(0, 168, 255, 0.5)`).

### 3.2. Estrutura Semântica e Marcos ARIA
* Uso de elementos semânticos HTML5: `<header class="topbar">`, `<aside class="sidebar">`, `<nav aria-label="Navegação principal">`, `<main id="main-content">`, `<section>`, `<article>`, `<footer>`.
* Regiões ativas para mensagens dinâmicas: `<section class="notice" aria-live="polite">` e `<div class="toast-container" aria-live="polite">`.
* Formulários com rótulos explícitos: Todos os inputs possuem elemento `<label for="...">` associado diretamente ao `id` do campo.

### 3.3. Contraste de Cores e Tipografia
* **Contraste Mínimo Atingido:** Todas as combinações de texto e fundo superam a razão mínima de **4,5:1** para texto normal e **3,0:1** para texto grande.
  * Texto primário sobre fundo claro: `#1e293b` sobre `#f6f8fc` (razão **13,8:1** — Nível AAA).
  * Texto em cartões escuros da barra lateral: `#ffffff` sobre `#0b2141` (razão **15,2:1** — Nível AAA).
  * Textos secundários/metadados: `#64748b` sobre `#ffffff` (razão **4,7:1** — Nível AA).
* **Fontes Humanistas e Legíveis:** Combinação de `DM Sans`, `Manrope` (títulos) e `JetBrains Mono` (hashes SHA-256 e valores técnicos) com espaçamento de linha e kerning otimizados para evitar fadiga visual e confusão de caracteres (`0` vs `O`, `1` vs `l`).

### 3.4. Tabelas de Dados e Exportação
* As tabelas de equipes e arquivos brutos utilizam cabeçalhos `<th>`, permitindo que o leitor de tela informe à pessoa usuária a qual coluna pertence determinado dado antes da leitura da célula.
* Informações numéricas contam com rótulos contextuais, impedindo leitura ambígua de decimais ou percentuais.

---

## 4. Recomendações aos Usuários de Tecnologias Assistivas

1. Para navegação rápida entre os quadrimestres e indicadores, utilize a navegação por cabeçalhos (tecla `H` no NVDA/JAWS).
2. Para consultar a trilha de auditoria e hashes SHA-256 dos CSVs originais, use o atalho de teclado direcionado ao botão "Auditoria & Hash SHA-256".
3. Em caso de necessidade de ampliação, o sistema suporta zoom do navegador de até **200% sem perda de conteúdo ou quebra de layout** (layout responsivo com flex-wrap e auto-fit grid).
