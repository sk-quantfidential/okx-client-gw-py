# Contributing to okx-client-gw-py

Thank you for your interest in contributing to the OKX Client Gateway!

## Development Setup

### Prerequisites

- Python 3.13+
- Conda (recommended) or virtualenv
- Git

### Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd okx-client-gw-py

# Create conda environment
conda create -n py313_financial_data python=3.13
conda activate py313_financial_data

# Install dependencies
pip install -e ".[dev,cli]"

# Install client-gw-core (from monorepo)
pip install -e ../client-gw-core-py
```

## Code Style

This project uses:

- **ruff** for linting and formatting
- **Line length**: 100 characters
- **Python version**: 3.13+

### Running Linters

```bash
# Check for issues
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/

# Format code
ruff format src/ tests/
```

## Testing

### Running Tests

```bash
# Unit tests (fast, no network)
PYTHONPATH=src pytest tests/unit/ -v

# Integration tests (requires network)
PYTHONPATH=src pytest tests/integration/ -v

# BDD tests
PYTHONPATH=src pytest tests/features/ -v

# All tests with coverage
PYTHONPATH=src pytest tests/ --cov=okx_client_gw --cov-report=html
```

### Test Requirements

- All new code must have tests
- Maintain or improve code coverage
- Unit tests should not require network access
- Integration tests may hit live APIs

## Pull Request Process

### Branch Naming

Follow the convention: `type/epic-XXX-NNNN-description`

Types:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation
- `refactor/` - Code refactoring
- `test/` - Test improvements

Example: `feature/epic-OKX-0001-public-market-data-client`

### Commit Messages

Follow conventional commits:

```
type(scope): brief description

Detailed explanation if needed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### PR Documentation

1. Create PR documentation in `docs/prs/`
2. Follow the template in `.github/pull_request_template.md`
3. Include:
   - Summary of changes
   - Testing completed
   - What changed (files and descriptions)

### Validation

Before submitting:

```bash
# Run validation script
./scripts/validate-all.sh

# Run all tests
PYTHONPATH=src pytest tests/ -v
```

## Architecture

This project follows Clean Architecture:

```
src/okx_client_gw/
├── domain/       # Business entities (no external deps)
├── application/  # Use cases, commands, services
├── ports/        # Protocol interfaces
├── adapters/     # External implementations
├── presentation/ # CLI, API endpoints
└── core/         # Cross-cutting concerns
```

### Layer Dependencies

- **domain**: No external dependencies
- **application**: Depends on domain and ports
- **adapters**: Implements ports, depends on external libraries
- **presentation**: Uses application layer

## Questions?

Open an issue for questions or discussions about contributing.
