# 🤖 Mini Software House de Agentes (GTX 1050 Ti Edition)
**Status do Projeto:** 🚧 Em Desenvolvimento

Este documento rastreia o progresso do desenvolvimento da pipeline de agentes de IA locais.

**Specs Alvo:**
- **GPU:** GTX 1050 Ti (4GB VRAM)
- **Backend:** Python 3.11+
- **LLM Runner:** Ollama
- **Container:** Docker (para execução segura)

---

## 🗓️ Fase 1: Fundação e Setup (Semana 1-2)
*Objetivo: Garantir que o hardware aguenta e o ambiente está pronto.*

- [x] **1.1. Setup de Hardware & Drivers**
    - [x] Atualizar Drivers NVIDIA (Game Ready ou Studio).
    - [x] Instalar NVIDIA CUDA Toolkit (verificar compatibilidade com `nvidia-smi`).
    - [x] Instalar Docker Desktop ou Engine (necessário para o sandbox de testes).

- [x] **1.2. Instalação do Ollama**
    - [x] Instalar Ollama.
    - [x] Configurar variável de ambiente `OLLAMA_HOST` (se necessário, padrão localhost:11434).
    - [x] Verificar se o Ollama está utilizando a GPU.

- [x] **1.3. Download dos Modelos (Quantizados)**
    - [x] `ollama pull phi3.5` (Planner & Tester - ~2.2GB)
    - [x] `ollama pull qwen2.5-coder:7b-instruct-q4_K_M` (Executor - ~4.5GB - *Verificar se cabe na VRAM+RAM*)
    - [x] `ollama pull gemma2:2b` (Documenter - ~1.6GB)

- [x] **1.4. Benchmarking Inicial**
    - [x] Criar script `scripts/benchmark.py`.
    - [x] Medir tokens/segundo (t/s) para cada modelo.
    - [x] Medir tempo de carga (cold start) dos modelos.
    - [x] Validar se o offloading para CPU (para o modelo de 7B) não está lento demais (< 5 t/s é inaceitável).

- [x] **1.5. Estrutura do Repositório**
    - [x] `git init`
    - [x] Criar `.gitignore` (ignorar `venv/`, `__pycache__/`, `.env`, `workspace/`).
    - [x] Criar ambiente virtual: `python -m venv .venv`.
    - [x] Instalar dependências base: `pip install ollama docker pydantic colorama`.

---

## 💻 Fase 2: O Agente Executor (Semana 2-3)
*Objetivo: O sistema consegue escrever código e salvar em disco.*

- [x] **2.1. Core do Orquestrador**
    - [x] Criar `src/main.py` (ponto de entrada).
    - [x] Criar classe base `Agent` em `src/agents/base.py`.
    - [x] Implementar comunicação com Ollama via API (biblioteca `ollama`).

- [x] **2.2. Agente Executor (Coder)**
    - [x] Criar `src/agents/executor.py`.
    - [x] Definir System Prompt para o Qwen2.5-Coder (foco em Clean Code e seguir instruções).
    - [x] Implementar função de parsing: Extrair blocos de código (```python ... ```) da resposta do LLM.
    - [x] Implementar `FileManager`: Salvar o código extraído nos arquivos corretos dentro de `workspace/`.

- [x] **2.3. Sandbox de Execução (Docker)**
    - [x] Criar `Dockerfile.sandbox` (Imagem leve com Python/Node pré-instalados).
    - [x] Implementar `src/utils/docker_runner.py`:
        - [x] Montar volume do `workspace/` no container.
        - [x] Executar comando e capturar `stdout`, `stderr` e `exit_code`.
        - [x] Implementar timeout (ex: 30s) para evitar loops infinitos.

---

## 🔄 Fase 3: Pipeline Completo (Semana 3-4)
*Objetivo: Conectar Planejamento, Execução, Teste e Documentação.*

- [x] **3.1. Agente Planner**
    - [x] Criar `src/agents/planner.py` (Modelo: Phi-3.5).
    - [x] Prompt: Deve receber a user request e retornar um JSON com:
        - [x] Arquitetura.
        - [x] Lista de arquivos a serem criados.
        - [x] Dependências.
        - [x] Passo a passo lógico.

- [x] **3.2. Agente Tester**
    - [x] Criar `src/agents/tester.py` (Modelo: Phi-3.5).
    - [x] Lógica: Ler o código gerado em `workspace/` -> Gerar arquivo de teste (ex: `test_app.py`).
    - [x] Integração com Docker: Rodar `pytest` dentro do container.
    - [x] Parser de Erro: Se falhar, isolar o erro do log para enviar de volta ao Executor.

- [x] **3.3. Loop de Feedback (Self-Healing)**
    - [x] Implementar lógica de retry no `main.py`.
    - [x] Se `exit_code != 0` nos testes:
        - [x] Enviar erro + código atual para o Executor.
        - [x] Solicitar correção.
        - [x] Decrementar contador de tentativas (Max 3 retries).

- [x] **3.4. Agente Documenter**
    - [x] Criar `src/agents/documenter.py` (Modelo: Gemma 2 2B).
    - [x] Ler todos os arquivos do `workspace/`.
    - [x] Gerar `README.md` com instruções de instalação e uso.

---

## 🚀 Fase 4: Refinamento e Interface (Semana 4+)
*Objetivo: Melhorar a usabilidade e a qualidade dos prompts.*

- [x] **4.1. CLI e Logs**
    - [x] Adicionar argumentos via `argparse` (ex: `--task "Criar API Todo"`, `--verbose`).
    - [x] Implementar logs coloridos no terminal para saber qual agente está "pensando".
    - [x] Salvar log de execução em `workspace/run.log`.

- [x] **4.2. Otimização de Prompts**
    - [x] Refinar prompt do Planner para evitar super-engenharia.
    - [x] Refinar prompt do Executor para não esquecer imports.
    - [x] Testar limites de contexto (Context Window Management).

- [x] **4.3. Persistência de Estado**
    - [x] Salvar o estado atual do pipeline em `state.json` (para retomar em caso de crash).

- [x] **4.4. (Opcional) Interface Web**
    - [x] Criar interface simples com Streamlit.
    - [x] Visualizar progresso em tempo real.
