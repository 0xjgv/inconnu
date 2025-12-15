# Silent helper (set VERBOSE=1 for full output)
SILENT_HELPER := source ./scripts/run_silent.sh

.PHONY: help
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

##@ Setup

.PHONY: install
install: ## Install dependencies (includes dev group)
	@$(SILENT_HELPER) && \
		print_main_header "Installing Dependencies" && \
		run_silent "Sync dev dependencies" "uv sync --group dev"

.PHONY: venv
venv: ## Create virtual environment
	@uv venv

.PHONY: update-deps
update-deps: ## Update dependencies
	@$(SILENT_HELPER) && \
		print_main_header "Updating Dependencies" && \
		run_silent "Update all" "uv update"

.PHONY: install-models
install-models: ## Install models required for testing
	@$(SILENT_HELPER) && \
		print_main_header "Installing Test Models" && \
		run_silent "English model" "uv run inconnu-download en" && \
		run_silent "German model" "uv run inconnu-download de" && \
		run_silent "Italian model" "uv run inconnu-download it"

##@ Code Quality

.PHONY: fix
fix: ## Fix code style issues
	@$(SILENT_HELPER) && run_silent "Fix style issues" "uv run ruff check --fix ."

.PHONY: format
format: ## Format code
	@$(SILENT_HELPER) && run_silent "Format code" "uv run ruff format ."

.PHONY: lint
lint: ## Lint code
	@$(SILENT_HELPER) && run_silent "Lint check" "uv run ruff check ."

.PHONY: check
quality-check: ## Run quality checks
	@$(SILENT_HELPER) && print_main_header "Running Quality Checks"
	@$(MAKE) fix
	@$(MAKE) format
	@$(MAKE) lint

##@ Testing

.PHONY: test
test: install-models ## Run tests
	@$(SILENT_HELPER) && \
		print_main_header "Running Tests" && \
		run_silent_with_test_count "Pytest" "uv run pytest -x" "pytest"

##@ Maintenance

.PHONY: clean
clean: quality-check ## Clean up cache and build artifacts
	@$(SILENT_HELPER) && \
		print_main_header "Cleaning Up" && \
		run_silent "Remove cache" "rm -fr .pytest_cache */__pycache__ */*/__pycache__" && \
		run_silent "Ruff clean" "uv run ruff clean"

.PHONY: check
check: quality-check test ## Run all checks