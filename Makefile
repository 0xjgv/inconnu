# Silent runner script
SCRIPTS := ./scripts/run_silent.sh

.PHONY: help
help: # Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?# .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?# "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

.PHONY: install
install: # Install dependencies (includes dev group)
	@. $(SCRIPTS) && \
		print_header "install" "Installing dependencies" && \
		run_silent "Sync dev dependencies" "uv sync --group dev"

.PHONY: venv
venv: # Create virtual environment
	uv venv

.PHONY: update-deps
update-deps: # Update dependencies
	@. $(SCRIPTS) && \
		print_header "update" "Updating dependencies" && \
		run_silent "Update all" "uv update"

.PHONY: fix
fix: # Fix code style issues
	@. $(SCRIPTS) && run_silent "Fix style issues" "uv run ruff check --fix ."

.PHONY: format
format: # Format code
	@. $(SCRIPTS) && run_silent "Format code" "uv run ruff format ."

.PHONY: lint
lint: # Lint code
	@. $(SCRIPTS) && run_silent "Lint check" "uv run ruff check ."

.PHONY: check
check: install-models # Run all checks (format, lint, test)
	@. $(SCRIPTS) && \
		print_header "check" "Running all checks" && \
		run_silent "Format check" "uv run ruff format --check ." && \
		run_silent "Lint" "uv run ruff check ." && \
		run_silent_with_test_count "Tests" "uv run pytest" "pytest"

.PHONY: clean
clean: # Clean up cache and build artifacts
	@. $(SCRIPTS) && \
		print_header "clean" "Cleaning up" && \
		run_silent "Fix style" "uv run ruff check --fix ." && \
		run_silent "Format" "uv run ruff format ." && \
		run_silent "Lint" "uv run ruff check ." && \
		run_silent "Remove cache" "rm -fr .pytest_cache */__pycache__ */*/__pycache__" && \
		run_silent "Ruff clean" "uv run ruff clean"

.PHONY: install-models
install-models: # Install models required for testing
	@. $(SCRIPTS) && \
		print_header "models" "Installing test models" && \
		run_silent "English model" "uv run inconnu-download en" && \
		run_silent "German model" "uv run inconnu-download de" && \
		run_silent "Italian model" "uv run inconnu-download it"

.PHONY: test
test: install-models # Run tests
	@. $(SCRIPTS) && \
		print_header "test" "Running tests" && \
		run_silent_with_test_count "Pytest" "uv run pytest" "pytest"