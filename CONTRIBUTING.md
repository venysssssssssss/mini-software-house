# Contributing to Mini Software House

Thank you for interest in contributing to Mini Software House! This guide will help you get started.

## Code of Conduct

Be respectful, inclusive, and professional. Harassment of any kind is not tolerated.

## Setting Up Development Environment

### Prerequisites
- Python 3.12+
- Rust 1.70+
- Git
- 4GB+ RAM (8GB recommended for development)

### Quick Setup

```bash
# Clone repository
git clone <repository-url>
cd mini-software-house

# Run setup
python scripts/setup/setup_environment.py

# Verify installation
make verify
```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Branch naming convention:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation
- `refactor/` - Code refactoring
- `perf/` - Performance improvements

### 2. Make Your Changes

```bash
# Activate Poetry shell
poetry shell

# Make changes to src/ or tests/

# Test your changes
make test

# Format code
make format

# Run linter
make lint
```

### 3. Commit Changes

```bash
git add .
git commit -m "type: description

- Bullet point 1
- Bullet point 2"
```

Commit types:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `style:` - Formatting
- `refactor:` - Code reorganization
- `perf:` - Performance improvement
- `test:` - Test addition/modification
- `chore:` - Build/dependency changes

### 4. Create Pull Request

Push your branch and create a PR with:

- Clear title describing the change
- Description of what and why
- Reference to any related issues
- Test results showing no regressions

```bash
git push origin feature/your-feature-name
```

## Code Style

### Python

```bash
# Auto-format
make format

# Check
make lint
```

- Use type hints
- Follow PEP 8
- Max line length: 88 characters (Black style)
- Docstrings for public functions/classes

### Rust

```bash
# Format
cd src/rust
cargo fmt

# Check
cargo clippy --all-targets
```

- Follow Rust conventions
- Use `cargo fmt` for formatting
- Run `cargo clippy` for linting

## Testing

### Before Submitting

```bash
# Run all tests
make test

# Run specific test suite
make test-unit
make test-integration

# Watch mode
make test-watch
```

### Writing Tests

#### Python Tests

```python
# tests/unit/test_feature.py
import pytest
from src.agents.base import Agent

def test_agent_initialization():
    agent = Agent("TestAgent", "qwen2.5:3b", "Test prompt")
    assert agent.name == "TestAgent"
    assert len(agent.chat_history) == 0
```

#### Rust Tests

```rust
// src/rust/my_module/src/lib.rs
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parsing() {
        assert_eq!(parse_value("test"), Some("test"));
    }
}
```

## Documentation

### Code Documentation

- Add docstrings to public functions/classes
- Include type hints
- Provide examples for complex logic

```python
def my_function(param: str) -> bool:
    """
    Brief description.
    
    Longer description if needed.
    
    Args:
        param: Description of parameter
        
    Returns:
        Description of return value
        
    Example:
        >>> my_function("test")
        True
    """
    pass
```

### Project Documentation

If making significant changes:

1. Update relevant documentation in `docs/`
2. Update `PROJECT_STRUCTURE.md` if structure changes
3. Update `README.md` if installation/usage changes

## Performance Considerations

This project runs on 4GB VRAM. When making changes:

- ✅ Check memory usage
- ✅ Test with smaller models
- ✅ Profile code for bottlenecks
- ✅ Document performance implications

```bash
# Benchmark
make benchmark
```

## Getting Help

- **Questions?** Check [docs/](docs/INDEX.md)
- **Issues?** Search existing GitHub issues
- **Feature suggestions?** Create a GitHub issue with `[Feature Request]` in title

## Areas for Contribution

### High Priority
- [ ] Unit tests for core modules
- [ ] Integration tests for pipeline
- [ ] Performance optimization for 2GB VRAM targets
- [ ] Additional agent types (DevOps, Security, etc.)

### Medium Priority
- [ ] CLI improvements
- [ ] Dashboard enhancements
- [ ] Documentation examples
- [ ] Docker sandbox improvements

### Nice-to-Have
- [ ] Web UI for task creation
- [ ] Result visualization
- [ ] Metrics/analytics dashboard
- [ ] Slack/Discord integration

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create release branch
4. Run full test suite
5. Tag release: `git tag v1.0.0`
6. Push: `git push --tags`

## Recognition

Contributors are recognized in:
- `CONTRIBUTORS.md` file
- Commit history
- Release notes

Thank you for contributing to Mini Software House! 🚀

---

**Last Updated**: March 2026
