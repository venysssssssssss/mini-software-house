# 🏗️ Mini Software House - Documentação

Este diretório contém toda a documentação do projeto organizada por tema.

## 📑 Estrutura

### 📊 [`status/`](status/)
Status atual do projeto e desenvolvimento completo.
- [SYSTEM_STATUS.md](status/SYSTEM_STATUS.md) - Status geral do sistema
- [TIER1_COMPLETE.md](status/TIER1_COMPLETE.md) - Marcos completados (Tier 1)
- [IMPLEMENTATION_COMPLETE.md](status/IMPLEMENTATION_COMPLETE.md) - Implementação Rust
- [RUST_STATUS.md](status/RUST_STATUS.md) - Status dos módulos Rust

### 🏛️ [`architecture/`](architecture/)
Arquitetura, roadmap e otimizações do sistema.
- [PRODUCT_ROADMAP.md](architecture/PRODUCT_ROADMAP.md) - Visão de 4 fases
- [PERFORMANCE_OPTIMIZATION_PLAN.md](architecture/PERFORMANCE_OPTIMIZATION_PLAN.md) - Estratégia de otimização
- [OPTIMIZATION_SUMMARY.md](architecture/OPTIMIZATION_SUMMARY.md) - Resumo executivo

### 📅 Sprint Plans
- [SPRINT_PLAN.md](SPRINT_PLAN.md) - 3-sprint improvement plan (Stability -> Intelligence -> Experience)
  - Sprint 1 (Stability): Complete -- wiring, tests, CI
  - Sprint 2 (Intelligence): Complete -- metrics, dashboard, executor, tester, Rust FFI
  - Sprint 3 (Experience): Not started
- [SPRINT3_PLAN.md](SPRINT3_PLAN.md) - Sprint 3 detailed implementation plan (6 phases)
- [SPRINT_FINETUNE.md](SPRINT_FINETUNE.md) - Fine-tuning sprint: QLoRA SFT/DPO for all 6 agent models on GTX 1050 Ti

### 🔧 [`setup/`](setup/)
Configuração ambiental e checklist de setup.
- [CHECKLIST_SOFTWARE_HOUSE_1050TI.md](setup/CHECKLIST_SOFTWARE_HOUSE_1050TI.md) - Validação HW/SW
- [README_VRAM_OPTIMIZATION.md](setup/README_VRAM_OPTIMIZATION.md) - Constraints de 4GB VRAM

### 🚀 [`quickstart/`](quickstart/)
Guias rápidos para começar a usar o projeto.
- [RUST_QUICK_START.md](quickstart/RUST_QUICK_START.md) - Roadmap Rust 4 semanas
- [WEBPAGE_QUICKSTART.md](quickstart/WEBPAGE_QUICKSTART.md) - Gerador de portfólio
- [dev_plan.md](quickstart/dev_plan.md) - Planejamento de desenvolvimento
- [NAMING_ENGINE.md](quickstart/NAMING_ENGINE.md) - ⭐ Smart project naming (kebab-case automático)
- [DOCKER_QUICKSTART.md](quickstart/DOCKER_QUICKSTART.md) - 🐳 Docker quick start (3 passos)
- [DOCKER_BUILD_GUIDE.md](quickstart/DOCKER_BUILD_GUIDE.md) - 🐳 Docker build options e troubleshooting

### 📦 [`archive/`](archive/)
Documentação legada ou descontinuada.

## 🎯 Por Onde Começar?

1. **Novo ao projeto?** → Leia [../README.md](../README.md)
2. **Quer entender a arquitetura?** → Veja [architecture/PRODUCT_ROADMAP.md](architecture/PRODUCT_ROADMAP.md)
3. **Configuring o ambiente?** → Siga [setup/CHECKLIST_SOFTWARE_HOUSE_1050TI.md](setup/CHECKLIST_SOFTWARE_HOUSE_1050TI.md)
4. **Desenvolvendo Rust?** → [quickstart/RUST_QUICK_START.md](quickstart/RUST_QUICK_START.md)
5. **Status do projeto?** → [status/SYSTEM_STATUS.md](status/SYSTEM_STATUS.md)
