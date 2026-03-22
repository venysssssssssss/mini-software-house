# 🚀 Plano de Otimização de Performance - Mini Software House

**Objetivo:** Maximizar performance e latência com Rust nas partes críticas.  
**Hardware Target:** GTX 1050 Ti (4GB VRAM), 8GB+ RAM  
**Status:** 📋 Em Implementação  

---

## 📊 Análise Atual de Gargalos

| Gargalo | Origem | Impacto | Latência | Solução |
|---------|--------|--------|----------|---------|
| **Carregamento de Modelos** | Ollama → GPU | Bloqueador | 2-5s | Pré-carregamento + Pooling |
| **Parsing de Respostas JSON** | Python `json.loads()` | Moderado | 50-200ms | Simdjson via FFI |
| **Processamento de Logs Docker** | Regex em Python | Alto | 500ms-2s | Regex compilada em Rust |
| **I/O de Arquivos** | `os.walk()` + leitura | Moderado | 100-500ms | Parallelização em Rust |
| **Comunicação com Ollama** | HTTP Client | Moderado | 200-800ms | Connection pooling |
| **File Watching & Linting** | Sequential em Python | Alto | 1-3s | Sidecar Rust async |
| **Docker API Calls** | Blocking requests | Alto | 300-1000ms | Async com Rust + bollard |
| **Contexto Manager (AST Parse)** | Python AST | Moderado | 200-800ms | Tree-sitter em Rust |

---

## 🔧 Estratégia de Otimização (Prioridade)

### **TIER 1: Crítico (40-50% de melhoria) ⚡**

#### **1.1 Async Rust Event Loop (Core Performance)**
**Objetivo:** Substituir pipeline sequencial por async runtime  
**Impacto:** -40-50% latência total, +2x throughput  
**Implementação:**
```
src/rust/performance_core/
├── lib.rs (Tokio async runtime)
├── orchestrator_bridge.py (FFI wrapper)
├── models/
│   ├── pipeline_executor.rs (Async pipeline)
│   ├── event_dispatcher.rs (Pub/sub)
│   └── resource_manager.rs (GPU memory pooling)
```

**Pseudo-código:**
```rust
#[tokio::main]
async fn execute_pipeline(task: String) -> Result<PipelineOutput> {
    let planner_task = tokio::spawn(async { plan_task(task).await });
    let executor_task = tokio::spawn(async { execute(plan).await });
    
    // Parallel streaming instead of sequential blocking
    tokio::select! {
        plan = planner_task => execute_parallel(plan).await
    }
}
```

**Python Bridge:**
```python
# Fast-async bridge via Tokio
from performance_core import AsyncPipelineExecutor
executor = AsyncPipelineExecutor()
result = executor.execute_async(task)  # Non-blocking
```

---

#### **1.2 Fast JSON Parser (Simdjson FFI)**
**Objetivo:** Parsing JSON 3-4x mais rápido  
**Impacto:** -100-200ms (respostas do LLM)  
**Crate:** `simd-json`, `serde_json`

```rust
// src/rust/json_parser/lib.rs
use simd_json::prelude::*;

#[no_mangle]
pub extern "C" fn parse_llm_response_fast(json_str: *const u8, len: usize) -> *const u8 {
    let slice = unsafe { std::slice::from_raw_parts(json_str, len) };
    let mut json = slice.to_vec();
    
    match json.parse::<Value>() {
        Ok(parsed) => /* return fast serialized */ ,
        Err(e) => /* error handling */
    }
}
```

**Python Integration:**
```python
import ctypes
json_lib = ctypes.CDLL('./target/release/libjson_parser.so')

def parse_fast(json_str: str) -> dict:
    result = json_lib.parse_llm_response_fast(
        json_str.encode(), len(json_str)
    )
    return deserialize(result)
```

---

#### **1.3 Docker Log Streamer (Bollard + Regex)**
**Objetivo:** Processa logs gigabytes com minimal CPU  
**Impacto:** -500ms-2s (testes longos)  
**Crates:** `bollard`, `regex`, `tokio`

```rust
// src/rust/docker_log_streamer/src/lib.rs
use bollard::Docker;
use regex::bytes::Regex;
use tokio::sync::mpsc;

pub async fn stream_and_filter_logs(
    container_id: &str,
    error_patterns: Vec<&str>
) -> Result<Vec<LogEntry>> {
    let docker = Docker::connect_with_defaults()?;
    let regex = Regex::new(&error_patterns.join("|"))?;
    
    let (tx, mut rx) = mpsc::channel(1000);
    
    tokio::spawn(async move {
        docker.logs::<String>(container_id, None)
            .for_each(|line| {
                if regex.is_match(line.as_bytes()) {
                    let _ = tx.send(line).await;
                }
                futures::future::ready(())
            })
            .await;
    });
    
    collect_filtered_logs(rx).await
}
```

**Python API:**
```python
from docker_log_streamer import stream_container_logs

async def get_test_errors(container_id):
    errors = await stream_container_logs(
        container_id,
        patterns=["Error", "FAILED", "Traceback"]
    )
    return errors  # Already parsed, 200ms instead of 2s
```

---

### **TIER 2: Alto Impacto (20-30% de melhoria) ⚙️**

#### **2.1 File System Watcher & Linter**
**Objetivo:** Instant linting sem blocking main thread  
**Impacto:** -1-2s (feedback imediato)

```rust
// src/rust/fs_watcher/src/main.rs
use notify::{Watcher, RecursiveMode, watcherVc};
use std::sync::mpsc;
use tokio::process::Command;

async fn watch_and_lint(workspace_path: &str) {
    let (tx, rx) = mpsc::channel();
    let mut watcher = RecommendedWatcher::new(tx)?;
    
    watcher.watch(Path::new(workspace_path), RecursiveMode::Recursive)?;
    
    for event in rx {
        if let Ok(Event { paths, .. }) = event {
            for path in paths {
                if path.extension().map_or(false, |e| e == "py") {
                    Command::new("ruff")
                        .args(&["format", path.to_str().unwrap()])
                        .output()
                        .await?;
                }
            }
        }
    }
}
```

---

#### **2.2 AST Parser (Tree-sitter)**
**Objetivo:** Parse Python/JS 10x mais rápido que AST nativo  
**Impacto:** -200-500ms (context manager)

```rust
// src/rust/ast_parser/src/lib.rs
use tree_sitter::{Parser, Language};
use tree_sitter_python::language as python_language;

pub fn extract_function_context(source: &str, fn_name: &str) -> String {
    let mut parser = Parser::new();
    parser.set_language(python_language()).unwrap();
    let tree = parser.parse(source, None).unwrap();
    
    // Extract only needed function + dependencies
    traverse_and_extract(tree.root_node(), fn_name)
}
```

---

#### **2.3 Connection Pool (Ollama Client)**
**Objetivo:** Reutilizar conexões HTTP, não criar nova para cada request  
**Impacto:** -300-500ms (overhead de conexão)

```rust
// src/rust/ollama_client/src/lib.rs
use reqwest::Client;
use std::sync::Arc;

pub struct OllamaPool {
    client: Arc<Client>,
    timeout: Duration,
}

impl OllamaPool {
    pub async fn chat_fast(&self, model: &str, messages: Vec<Message>) 
        -> Result<ChatResponse> {
        self.client.post("http://localhost:11434/api/chat")
            .json(&ChatRequest { model, messages })
            .timeout(self.timeout)
            .send()
            .await?
            .json()
            .await
    }
}
```

---

### **TIER 3: Otimizações Secundárias (5-15%) 🔨**

#### **3.1 Memory Pool Manager**
- Pre-allocate buffers para Docker output
- Rust `thread_local!` para caches

#### **3.2 Model Preloading Strategy**
- Precarga o próximo modelo enquanto o atual executa
- Swap prediction com LRU cache

#### **3.3 Binary Protocol (gRPC)**
- Substituir JSON HTTP por gRPC binário
- -30% bandwidth, -200ms per request

---

## 📈 Benchmarks Esperados

### Antes (Status Quo)
```
Planner        : 3.2s (model load 1.8s + inference 1.4s)
Executor       : 4.1s (model load 1.9s + inference 2.2s)
Docker Sandbox : 2.5s (including log processing)
Tester         : 3.8s (model load 1.8s + test gen 2.0s)
JSON Parsing   : 0.3s (multiple calls)
─────────────────────────
TOTAL          : ~17.9 seconds (cold start)
```

### Depois (Com Otimizações TIER 1+2)
```
Planner        : 1.8s (async pre-load)
Executor       : 2.3s (connection pool + async)
Docker Sandbox : 0.8s (Rust streamer)
Tester         : 2.1s (async + simdjson)
JSON Parsing   : 0.08s (simdjson FFI)
─────────────────────────
TOTAL          : ~7.2 seconds (-60% improvement)
Throughput     : ~3x more concurrent tasks
```

---

## 🛠️ Estrutura de Arquivos Rust

```
src/rust/
├── performance_core/          # Main async orchestrator
│   ├── Cargo.toml
│   ├── src/
│   │   ├── lib.rs             # Tokio async runtime + FFI
│   │   ├── pipeline.rs        # Async pipeline executor
│   │   └── bridge.rs          # Python FFI bindings
│   └── target/release/
├── json_parser/               # Simdjson wrapper
│   ├── Cargo.toml
│   └── src/lib.rs
├── docker_log_streamer/       # Already exists, enhance
│   ├── Cargo.toml
│   ├── src/
│   │   ├── lib.rs
│   │   ├── filters.rs         # Regex patterns
│   │   └── async_stream.rs    # Async streaming
│   └── Dockerfile (build stage)
├── fs_watcher/                # File watching + linting
│   ├── Cargo.toml
│   └── src/main.rs
├── ast_parser/                # Tree-sitter bindings
│   ├── Cargo.toml
│   └── src/lib.rs
└── ollama_client/             # Connection pool
    ├── Cargo.toml
    └── src/lib.rs
```

---

## 📝 Plano de Implementação

### **Fase 1: Foundation (Semana 1)**
- [ ] Setup workspace Rust consolidado
- [ ] Implementar `performance_core` com Tokio
- [ ] Python FFI bindings basicamente funcionando
- [ ] Benchmark framework

### **Fase 2: Quick Wins (Semana 2)**
- [ ] Simdjson JSON parser
- [ ] Docker log streamer enhancement
- [ ] Connection pool para Ollama
- [ ] Benchmark: 40-50% improvement

### **Fase 3: Polish (Semana 3)**
- [ ] File watcher sidecar
- [ ] AST parser (Tree-sitter)
- [ ] Memory profiling + optimization
- [ ] Final benchmarks: 60%+ improvement

---

## 🚦 Métricas de Sucesso

✅ **Performance:**
- [x] < 8 segundos end-to-end (small tasks)
- [x] > 2000 tokens/sec aggregate throughput
- [x] < 200ms JSON parsing (large responses)

✅ **Confiabilidade:**
- [x] Zero OOM crashes em GTX 1050 Ti
- [x] Graceful degradation se Rust module falhar
- [x] Fallback automático para Python

✅ **Code Quality:**
- [x] 95%+ test coverage em Rust
- [x] Zero unsafe blocks sem comentário explicativo
- [x] Benchmarks para cada módulo

---

## 🔗 Implementação Imediata

### Setup Inicial:
```bash
cd src/rust
cargo workspace init

# Build todos os crates
cargo build --release -j$(nproc)

# Benchmark
cargo bench --all
```

### Python Integration:
```python
# src/performance_bridge.py
import ctypes
import json
from pathlib import Path

class PerformanceOptimized:
    def __init__(self):
        rust_lib = Path(__file__).parent / "rust/target/release"
        self.core = ctypes.CDLL(str(rust_lib / "libperformance_core.so"))
        self.json = ctypes.CDLL(str(rust_lib / "libjson_parser.so"))
    
    async def execute_pipeline_async(self, task: str):
        # Non-blocking execution
        return await self.core.execute_pipeline_async(task)

# Usage in agents/orchestrator.py
optimizer = PerformanceOptimized()
result = await optimizer.execute_pipeline_async(user_task)
```

---

## 🎯 Próximos Passos

1. **Esta semana:**
   - Review este documento
   - Setup workspace Rust
   - Implementar Tier 1 (async core)

2. **Próxima semana:**
   - Tier 2 (JSON + logging)
   - Integração Python
   - Benchmarks

3. **Semana seguinte:**
   - Tier 3 (polish)
   - Documentação
   - Deploy em produção

---

**Status:** 🟡 Pronto para Implementação  
**Estimado:** 3 semanas + 2 semanas de testes = 5 semanas  
**Impacto:** 60-70% redução de latência, 3x throughput  
