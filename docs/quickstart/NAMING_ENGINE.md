# 🏗️ Intelligent Project Naming Engine

Automatic generation of smart, descriptive project names following a consistent kebab-case pattern.

## Overview

The **Naming Engine** automatically generates project names based on the **problem the project solves**, not generic defaults like "workspace" or "project-123".

### Pattern

```
action-object-purpose (kebab-case)
```

**Examples:**
- "Build a REST API for user management" → `build-user-api`
- "Create a real-time chat application" → `create-message-rt-app`
- "Machine learning image recognition" → `dev-image-classification-learn`
- "Data ETL pipeline with streaming" → `build-data-analytics-rt`
- "Monitoring dashboard for metrics" → `create-dashboard`

---

## How It Works

### 1. **Automatic Analysis**

The engine extracts:
- **Action**: What's being done (build, create, develop, etc.)
- **Object**: What's being created (API, dashboard, model, etc.)
- **Purpose**: What problem it solves (user management, real-time chat, etc.)
- **Tech features**: Special capabilities (real-time, async, DB, ML, etc.)

### 2. **Intelligent Combination**

Combines these elements into a meaningful kebab-case name:

```
action + purpose + tech + object → final-name
```

### 3. **Integration with Agents**

- **PlannerAgent**: Generates `project_name` in JSON response
- **ExecutorAgent**: Creates files in directory named after project_name
- **Dashboard**: Displays projects with meaningful names

---

## Usage

### Quick Start

```python
from src.naming_engine import NamingEngine

engine = NamingEngine()

# Generate name from task description
project_name = engine.generate_project_name_from_task(
    task_description="Build a REST API for user authentication",
    dependencies=["fastapi", "sqlalchemy"]
)

print(project_name)  # Output: "build-user-api"
```

### Full Analysis

```python
# Get detailed analysis and name
analysis = engine.analyze_project(
    files=["main.py", "models.py", "routes.py"],
    dependencies=["fastapi", "pydantic", "sqlalchemy"],
    task_description="Build a REST API with database"
)

name, description = engine.generate_name(
    analysis, 
    task_description="Build a REST API with database"
)
```

### In Agents

The **PlannerAgent** automatically generates project names:

```python
from src.agents.planner import PlannerAgent

planner = PlannerAgent()
plan = planner.plan_task("Build a REST API for user management")

# plan now contains "project_name": "build-user-api"
print(plan["project_name"])  # Output: "build-user-api"
```

---

## Configuration

### Action Verbs

Recognized action verbs (customize in `src/naming_engine.py`):

```
build, create, develop, generate, analyze, process, manage,
monitor, track, stream, sync, transform
```

### Object Keywords

Project type identifiers:

```
api, rest, graphql, dashboard, interface, website, application,
service, tool, engine, pipeline, model, bot, chat, server,
client, framework, library
```

### Purpose Keywords

Problem domain identifiers:

```
user, admin, product, order, inventory, task, message, payment,
report, analytics, data, content, media, image, video, etc.
```

### Tech Features

Special capabilities that influence naming:

```
api, async, realtime, websocket, db, mongodb, postgres, 
ml, ai, docker, kubernetes, microservice
```

---

## Generated Names - Examples

| Task | Generated Name |
|------|---|
| "Build REST API for users" | `build-user-api` |
| "Create real-time chat" | `create-message-rt-app` |
| "ML image recognition" | `dev-image-classification-learn` |
| "ETL data pipeline" | `build-data-analytics-rt` |
| "Monitoring dashboard" | `create-dashboard` |
| "Notification service" | `dev-notification-svc` |
| "Search engine" | `build-search-engine` |
| "Video processing tool" | `create-video-tool` |
| "Admin panel" | `build-admin-ui` |
| "Cache layer" | `create-cache-redis` |

---

## Advanced Usage

### Custom Words

Add custom words to influence naming:

```python
name = engine.generate_project_name_from_task(
    task_description="Build a payment processing system",
    dependencies=["stripe", "fastapi", "sqlalchemy"]
)
# Output: "build-payment-api"
```

### Batch Generation

Generate names for multiple projects:

```python
projects = [
    {"files": [...], "dependencies": [...], "description": "..."},
    {"files": [...], "dependencies": [...], "description": "..."},
]

results = engine.generate_batch(projects)
# Returns: [(name, description, analysis), ...]
```

---

## Benefits

✅ **Consistency**: Always follows kebab-case pattern  
✅ **Semantics**: Names reflect actual project purpose  
✅ **Intelligence**: Extracts meaning from task description  
✅ **Automation**: No manual naming needed  
✅ **Integration**: Works seamlessly with agents  
✅ **Flexibility**: Easy to customize keywords  

---

## Testing

Run the demo to see various naming examples:

```bash
python scripts/test_naming_engine.py
```

Output shows:
- 8+ real-world examples
- Generated names in kebab-case
- Dependencies used for analysis

---

## Implementation Details

### Architecture

```
NamingEngine
├── analyze_project()          → Classify type & features
├── generate_name()            → Create intelligent name
├── generate_project_name_from_task()  → Quick name generation
├── _generate_kebab_name()     → Kebab-case formatting
└── load_project_metadata()    → Load from workspace
```

### File Location

- **Main**: `src/naming_engine.py` (450+ lines)
- **Integration**: `src/agents/planner.py` (auto-generation)
- **Demo**: `scripts/test_naming_engine.py`

---

## Future Enhancements

- [ ] Machine learning for better keyword extraction
- [ ] Multi-language support
- [ ] Custom naming templates
- [ ] Naming metrics and analytics
- [ ] Collision detection (avoid duplicate names)
- [ ] Historical trending of project naming patterns

---

## Related Files

- 📄 [README.md](../README.md) - Main project guide
- 🔧 [PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) - Code architecture
- 🤖 [src/agents/planner.py](../../src/agents/planner.py) - Planning agent integration
- 📊 [scripts/test_naming_engine.py](../test_naming_engine.py) - Demo script

---

**Version**: 1.0  
**Last Updated**: March 22, 2026  
**Pattern**: `action-object-purpose` (kebab-case)
