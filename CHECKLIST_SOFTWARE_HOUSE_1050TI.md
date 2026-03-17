# Checklist Técnico: Mini Software House de Agentes (Otimizado para GTX 1050 Ti - 4GB VRAM)

## 1. Arquitetura e Estratégia de Hardware (4GB VRAM)
Devido à restrição de memória (4GB VRAM na GTX 1050 Ti), **não é possível manter múltiplos LLMs complexos carregados simultaneamente**. A arquitetura da sua software house *deve* ser sequencial, baseada em "swap" de modelos:

- [x] **Orquestrador de Modelos (Ollama/LM Studio):** Configurar o servidor para descarregar o modelo da memória imediatamente após o uso (no Ollama, ajustar a variável de ambiente `OLLAMA_KEEP_ALIVE=0` ou tempo curto).
- [x] **Quantização Obrigatória:** Utilizar apenas modelos em formato GGUF com quantização de 4 bits ou 5 bits (ex: `Q4_K_M`). Modelos maiores que 3.5GB farão *offload* para a CPU e ficarão extremamente lentos.
- [x] **Gerenciamento Estrito de Contexto:** Limitar o histórico passado ao LLM (no seu `src/agents/context_manager.py`) a um máximo de ~4096 tokens para evitar overflow da VRAM.
- [x] **Embeddings Ultra Leves (RAG):** Usar o modelo `nomic-embed-text` (ocupa menos de 300MB de RAM) para a vetorização no seu `rag.py`.

---

## 2. Seleção de Modelos Especializados
Recomendações específicas para modelos locais que rodam fluidamente em 4GB VRAM (parâmetros entre 1.3B e 3B).

- [] **Arquiteto / Planejador (`planner.py`)**
  - **Função:** Entender o requisito do usuário, quebrar em tarefas (backend, frontend, BD) e definir o plano de execução.
  - **Modelo Recomendado:** `Qwen2.5-3B-Instruct` (GGUF Q4) ou `Llama-3.2-3B-Instruct`. Possuem raciocínio lógico e habilidade de seguir formatos JSON/Markdown excepcionais para o tamanho.

- [] **Desenvolvedor Backend (`base.py` / Agent Worker)**
  - **Função:** Escrever código em Python/FastAPI/Rust, focar em lógica de banco de dados e rotas.
  - **Modelo Recomendado:** `Qwen2.5-Coder-3B-Instruct` (O melhor na categoria de 3B) ou `DeepSeek-Coder-1.3B-Instruct` (Extremamente rápido, consome <1GB de VRAM, ótimo para snippets menores).

- [] **Desenvolvedor Frontend (`base.py` / Agent Worker)**
  - **Função:** Gerar HTML/CSS/JS, React ou componentes visuais.
  - **Modelo Recomendado:** `Qwen2.5-Coder-1.5B-Instruct` (Leve, permitindo que você reserve mais VRAM para passar o contexto de bibliotecas CSS ou templates grandes no prompt).

- [] **Engenheiro de Testes/QA (`tester.py`)**
  - **Função:** Ler o código gerado pelo Dev, inferir os casos de borda e escrever testes unitários rigorosos (ex: Pytest).
  - **Modelo Recomendado:** `DeepSeek-Coder-1.3B-Instruct`. Ele é rápido, exato e excelente em gerar `asserts` e mocks baseados no código fornecido.

- [] **Documentador (`documenter.py`)**
  - **Função:** Documentar rotas da API, gerar o `README.md`, comentar o código e atualizar o `PRODUCT_ROADMAP.md`.
  - **Modelo Recomendado:** `Gemma-2-2B-It` (Texto fluido, excelente em formatação de relatórios e Markdown) ou `Phi-3-mini-4k-instruct-q4`.

- [] **Pesquisador/Analista de Dados (RAG - `rag.py`)**
  - **Função:** Ler documentações técnicas, bibliotecas locais ou regras de negócio indexadas.
  - **Modelo Recomendado:** `Phi-3-mini-4k-instruct` (Muito capaz de sintetizar informações extensas mantendo a fidelidade aos dados buscados).

---

## 3. Implementação e Ajustes no Código (Projeto Atual)

- [x] **Otimização do `executor.py`:**
  - Garantir que a integração com o sandbox (`Dockerfile.sandbox` e `utils/docker_runner.py`) isole a execução do código de forma segura.
  - Implementar um *timeout* rígido (ex: 30 segundos) no `docker_runner.py` para evitar que códigos em loop gerados pelo LLM travem a máquina.
- [x] **Orquestrador de Contexto (`context_manager.py`):**
  - **Não** enviar a base de código inteira a cada chamada para não estourar os tokens/VRAM. Enviar apenas as *assinaturas das funções* relevantes (AST) e a task da vez.
- [x] **Roteamento de Modelos em `base.py`:**
  - Implementar uma lógica no agente base que determine qual modelo invocar no Ollama dependendo de sua `role` (Especialidade):
    ```python
    def get_model_for_role(role):
        models = {
            "planner": "qwen2.5:3b",
            "backend": "qwen2.5-coder:3b",
            "frontend": "qwen2.5-coder:1.5b",
            "tester": "deepseek-coder:1.3b",
            "documenter": "gemma2:2b"
        }
        return models.get(role, "qwen2.5:3b")
    ```

---

## 4. Pipeline Ideal de Execução (Ciclo de Vida de uma Request)

Para contornar o gargalo da GPU (1050 Ti), implemente o seguinte fluxo sequencial onde apenas **UM** modelo está na VRAM por vez:

1. [] **Entrada:** O usuário envia uma solicitação complexa.
2. [] **Planejamento:** O Arquiteto (`Qwen2.5-3B`) analisa, quebra em *micro-tasks* (Schema, Rotas, UI, Testes) -> **O modelo é descarregado da memória.**
3. [] **Desenvolvimento (Backend):** O Backend Dev (`Qwen Coder 3B` ou `DeepSeek 1.3B`) implementa apenas o Schema e Rotas -> **Descarrega.**
4. [] **Garantia de Qualidade (Testes):** O Tester (`DeepSeek 1.3B`) analisa o código gerado no passo 3, cria os arquivos de teste -> **Descarrega.**
5. [] **Validação (Sandbox):** O `executor.py` roda os testes no container Docker.
6. [] **Auto-Cura (Loop):** Se o Docker retornar erro (stacktrace), o erro volta como contexto para o Backend Dev corrigir.
7. [] **Entrega e Docs:** Quando todos os testes passarem, o Documentador (`Gemma 2 2B`) documenta a entrega final.

---

## 5. Setup de Ambiente Recomendado

- [ ] **Ollama:** Instalar e configurar localmente para servir os modelos GGUF com facilidade.
- [ ] **Driver NVIDIA e CUDA:** Validar se o toolkit CUDA está sendo reconhecido pelo Linux (`nvidia-smi`). Isso é crítico para garantir que o Ollama coloque as camadas dos modelos na VRAM (GPU) e não na RAM (CPU).
- [ ] **Gerenciamento de Dependências:** Garantir que o `poetry.lock` utilize libs leves de orquestração (como `litellm` para padronizar chamadas de API do Ollama) e não frameworks pesados como o LangChain completo, se não for estritamente necessário.
