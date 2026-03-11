# 🚀 Roadmap de Produto: The Local-First Autonomous Dev Environment

**Visão:** Transformar o "Mini Software House" de uma pipeline de scripts em um produto de engenharia de software robusto, performático e resiliente, otimizado para execução em hardware de consumidor.

---

## ✅ Fase 1: Fundação da Arquitetura de Produto (The Backbone)
*Objetivo: Mover de uma execução linear e frágil para uma arquitetura orientada a eventos e com estado persistente. Isso é a base para todas as futuras melhorias de performance e funcionalidade.*

- [x] **1.1. Substituir `state.json` por um Banco de Dados Relacional**
    - **Ação:** Implementado `src/core/database.py` e `src/core/models.py` usando `SQLModel`.
    - **Schema:** Criar tabelas para `Projects`, `Tasks`, `TaskRuns`, `AgentLogs`, e `Artifacts`.
    - **Potencial:** Permite histórico de execuções, auditoria, queries complexas ("quais tarefas mais falham?"), e a capacidade de "rebobinar" e re-executar uma tarefa a partir de um estado anterior. Elimina condições de corrida na escrita de um único arquivo JSON.

- [x] **1.2. Desacoplar Agentes com um Event Bus/Message Queue**
    - **Ação:** Implementado `src/core/events.py` (Pub/Sub pattern).
    - **Potencial:**
        - **Paralelismo:** Múltiplos `ExecutorAgents` poderiam trabalhar em diferentes partes de um plano simultaneamente.
        - **Resiliência:** Se o `TesterAgent` falhar, ele pode publicar um evento `TESTS_FAILED` sem que o orquestrador principal precise saber dos detalhes.
        - **Interatividade:** Permite que um comando externo (via UI ou CLI) publique um evento `CANCEL_TASK` que interrompe a execução atual de forma limpa.

- [x] **1.3. Adotar Structured Logging**
    - **Ação:** Implementado `src/core/logger.py` usando `structlog`.
    - **Potencial:** Transforma logs de "texto para humanos" em "dados para máquinas". Permite filtrar, agregar e analisar a performance e os erros de cada agente de forma programática. Essencial para o "Data Flywheel".

---

## 🧠 Fase 2: Inteligência e Otimização de Contexto (The Brain)
*Objetivo: Lidar com a restrição de 4GB de VRAM da GTX 1050 Ti. A ingenuidade no gerenciamento de contexto é mais importante que a força bruta do hardware.*

- [ ] **2.1. Implementar Grammar-Based Sampling para o `PlannerAgent`**
    - **Ação:** Em vez de pedir JSON e usar regex para limpar, forçar o LLM a gerar um JSON sintaticamente perfeito. Backends como `llama.cpp` (usado pelo Ollama) suportam GBNF (Grammar-Based Normal Form).
    - **Potencial:** Elimina 100% dos erros de `json.JSONDecodeError`. Torna a comunicação inter-agentes perfeitamente confiável, removendo uma das maiores fontes de fragilidade em sistemas de agentes.

- [ ] **2.2. Criar um `ContextManager` baseado em AST (Abstract Syntax Tree)**
    - **Ação:** Para o `TesterAgent` e o `ExecutorAgent` (no modo de correção), em vez de ler arquivos inteiros, usar uma biblioteca como `ast` do Python para parsear o código.
    - **Exemplo:** Para testar a função `calculate_price`, extraia apenas o código da função `calculate_price` e as assinaturas das funções que ela chama.
    - **Potencial:** Reduz o tamanho do prompt em 90% ou mais, permitindo que projetos maiores caibam no contexto limitado. Aumenta a relevância do prompt, levando a respostas de maior qualidade do LLM.

- [ ] **2.3. Implementar um RAG (Retrieval-Augmented Generation) Simples para Documentação**
    - **Ação:** Para o `DocumenterAgent`, em vez de colocar todo o código no prompt, vetorize os arquivos do projeto usando uma biblioteca leve como `ChromaDB` (que roda em disco). O agente primeiro faz uma busca por similaridade para encontrar os trechos de código mais relevantes para cada seção do `README.md`.
    - **Potencial:** Permite documentar repositórios arbitrariamente grandes, muito além da capacidade da janela de contexto do modelo.

---

## ⚡ Fase 3: Performance Extrema e Rust (The Muscle)
*Objetivo: Descarregar tarefas de I/O e processamento intensivo do Python (que é limitado pelo GIL) para binários Rust compilados, garantindo que a CPU e a RAM estejam livres para alimentar a GPU.*

- [ ] **3.1. [RUST] Criar um `FileWatcher` Sidecar**
    - **Ação:** Desenvolver um pequeno binário em Rust usando a crate `notify`. Ele monitora o diretório `workspace/` em tempo real.
    - **Workflow:** Assim que o `ExecutorAgent` salva um arquivo `.py`, o watcher de Rust dispara instantaneamente um comando (ex: `ruff format` e `ruff check --fix`).
    - **Potencial:** Performance quase nativa para linting e formatação. O feedback é instantâneo e acontece fora do processo principal do Python, mantendo o orquestrador leve e responsivo.

- [ ] **3.2. [RUST] Criar um `DockerLogStreamer`**
    - **Ação:** Em vez do `container.logs()` do Python, que espera o comando terminar, criar um processo Rust que se conecta ao stream de logs do Docker em tempo real.
    - **Workflow:** O processo Rust usa regex otimizadas (crate `regex`) para filtrar o ruído e identificar padrões de erro em gigabytes de logs, passando apenas o erro estruturado para o orquestrador Python via `stdout` ou `IPC`.
    - **Potencial:** Garante que a pipeline não trave ao executar um comando muito verboso. Permite o monitoramento em tempo real de processos de longa duração dentro do container.

- [ ] **3.3. Otimizar o `DockerRunner` para Reutilização de Camadas**
    - **Ação:** Modificar o `Dockerfile.sandbox` para que as dependências do projeto (`requirements.txt`) sejam instaladas em uma camada separada.
    - **Potencial:** Reduz drasticamente o tempo de build da imagem quando apenas o código-fonte muda, acelerando o ciclo de teste.

---

## 📊 Fase 4: Data Flywheel e Melhoria Contínua (The Memory)
*Objetivo: Transformar cada execução em um ponto de dados para melhorar o sistema ao longo do tempo. Um produto de IA estático está fadado à obsolescência.*

- [ ] **4.1. Coletar Dados para Fine-Tuning (DPO/RLHF)**
    - **Ação:** No banco de dados da Fase 1, salvar tuplas de `{prompt, código_gerado, resultado_dos_testes, código_corrigido_se_falhou}`.
    - **Potencial:** Cria um dataset de altíssima qualidade e específico para o seu domínio. Com dados suficientes, você pode usar LoRA para fazer um fine-tuning no `phi3.5` ou `qwen` para que ele se torne progressivamente melhor em gerar código que passa nos seus testes de primeira.

- [ ] **4.2. Dashboard de Métricas de Agentes**
    - **Ação:** Usar os dados do `Structured Logging` e do banco de dados para criar um dashboard (pode ser no próprio Streamlit).
    - **Métricas:**
        - Taxa de sucesso de primeira do `ExecutorAgent`.
        - Tempo médio de resposta de cada agente.
        - Erros mais comuns nos testes.
    - **Potencial:** Fornece insights acionáveis para otimização de prompts e identificação de gargalos na pipeline.

---

## 🎨 Fase 5: Experiência do Desenvolvedor (The Face)
*Objetivo: Criar uma interface que seja poderosa, informativa e não frustrante.*

- [ ] **5.1. Migrar de Streamlit (Polling) para FastAPI + WebSockets**
    - **Ação:** Criar um backend `FastAPI` que gerencia a pipeline e expõe um endpoint WebSocket. O frontend (pode ser `React` ou até `HTMX` para simplicidade) se conecta para receber atualizações em tempo real.
    - **Potencial:** Experiência de usuário fluida. Os logs aparecem no terminal da web no instante em que são gerados. O status da pipeline é atualizado em tempo real, sem a necessidade de um botão "Refresh".

- [ ] **5.2. Integração Real com Git**
    - **Ação:** O `ExecutorAgent` não deve apenas salvar arquivos. Ele deve ser instruído a criar uma nova branch (`git checkout -b feature/task-123`), fazer o commit do código gerado e, opcionalmente, criar um Pull Request (se integrado a uma plataforma como Gitea/GitLab local).
    - **Potencial:** Integra o fluxo de trabalho do agente diretamente no fluxo de trabalho de desenvolvimento padrão, tornando sua adoção muito mais natural para os desenvolvedores.