# Inconnu

[![GitHub](https://img.shields.io/github/stars/0xjgv/inconnu)](https://github.com/0xjgv/inconnu)
[![inconnu.ai](https://img.shields.io/badge/website-inconnu.ai-blue)](https://inconnu.ai)
[![PyPI](https://img.shields.io/pypi/v/inconnu)](https://pypi.org/project/inconnu/)

## What is Inconnu?

Inconnu is a GDPR-compliant data privacy tool designed for entity redaction and de-anonymization. It provides cutting-edge NLP-based tools for anonymizing and pseudonymizing text data while maintaining data utility, ensuring your business meets stringent privacy regulations.

## Why Inconnu?

1. **Seamless Compliance**: Inconnu simplifies the complexity of GDPR and other privacy laws, making sure your data handling practices are always in line with legal standards.

2. **State-of-the-Art NLP**: Utilizing advanced spaCy models and custom entity recognition, Inconnu ensures that personal identifiers are completely detected and properly handled.

3. **Transparency and Trust**: Complete processing documentation with timestamping, hashing, and entity mapping for full audit trails.

4. **Reversible Processing**: Support for both anonymization and pseudonymization with complete de-anonymization capabilities.

5. **Performance Optimized**: Fast processing with singleton pattern optimization and configurable text length limits.

## Installation

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)

### Install from PyPI

```bash
# Using pip
pip install inconnu

# Using UV (Recommended)
uv add inconnu
```

**Note**: Language models are NOT included as optional dependencies. You'll need to download them separately using the `inconnu-download` command after installation (see below).

### Download Language Models

After installing Inconnu, use the `inconnu-download` command to download spaCy language models:

```bash
# Download default (small) models
inconnu-download en              # English
inconnu-download de              # German
inconnu-download en de fr        # Multiple languages
inconnu-download all             # All default models

# Download specific model sizes
inconnu-download en --size large       # Large English model
inconnu-download en --size transformer # Transformer model (English only)

# List available models and check what's installed
inconnu-download --list

# Upgrade existing models
inconnu-download en --upgrade

# Get help for UV environments
inconnu-download --uv-help
```

#### How Model Installation Works

1. **No Optional Dependencies**: spaCy models are NOT included as pip/uv optional dependencies to avoid unnecessary downloads during dependency resolution
2. **On-Demand Downloads**: The `inconnu-download` command downloads only the models you need
3. **Smart Environment Detection**: Automatically detects UV environments and provides appropriate guidance
4. **Verification**: Checks if models are already installed before downloading

#### Available Model Sizes

- **Small (sm)**: Default, fast processing, ~15-50MB, good for high-volume
- **Medium (md)**: Better accuracy, ~50-200MB, moderate speed
- **Large (lg)**: High accuracy, ~200-600MB, slower processing
- **Transformer (trf)**: Highest accuracy, ~400MB+, GPU-optimized (English only)

#### Alternative: Direct spaCy Download

You can also use spaCy directly if preferred:
```bash
python -m spacy download en_core_web_sm   # English small
python -m spacy download de_core_news_lg  # German large
```

### Install from Source

1. **Clone the repository**:
   ```bash
   git clone https://github.com/0xjgv/inconnu.git
   cd inconnu
   ```

2. **Install with UV (recommended for development)**:
   ```bash
   uv sync                      # Install dependencies
   inconnu-download en de       # Download language models
   make test                    # Run tests
   ```

3. **Or install with pip**:
   ```bash
   pip install -e .     # Install in editable mode
   python -m spacy download en_core_web_sm
   ```

### Development Commands

For development, the Makefile provides convenience targets:

```bash
make install        # Install dependencies
make test           # Run tests (auto-downloads required models)
make check          # Run format check, lint, and tests
make lint           # Check code with ruff
make format         # Format code
make clean          # Format, lint, fix, and clean cache
```

To download additional language models, use the CLI directly:

```bash
uv run inconnu-download en de fr   # Download specific models
uv run inconnu-download all        # Download all models
uv run inconnu-download --list     # List available models
```

### Using Different Models in Code

To use a different model size, first download it, then specify it when initializing:

```python
from inconnu import Inconnu
from inconnu.nlp.entity_redactor import SpacyModels

# First, download the model you want
# $ inconnu-download en --size large

# Then use it in your code
inconnu = Inconnu(
    language="en",
    model_name=SpacyModels.EN_CORE_WEB_LG  # Use large model
)

# For highest accuracy (transformer model)
inconnu_trf = Inconnu(
    language="en",
    model_name=SpacyModels.EN_CORE_WEB_TRF
)
```

**Model Selection Guide:**
- `en_core_web_sm`: Fast processing, good for high-volume
- `en_core_web_lg`: Better accuracy, moderate speed
- `en_core_web_trf`: Highest accuracy, GPU-optimized (recommended for sensitive data)

For a complete list of supported models, run `inconnu-download --list`

## Development Setup

### Available Commands

```bash
make install          # Install all dependencies
make test             # Run full test suite (downloads required models)
make check            # Run format check, lint, and tests
make lint             # Check code with ruff
make format           # Format code with ruff
make fix              # Auto-fix linting issues
make clean            # Format, lint, fix, and clean cache
make update-deps      # Update dependencies

# Download language models via CLI
uv run inconnu-download en de it   # Download specific models
uv run inconnu-download all        # Download all supported models
```

### Running Tests

```bash
# Run all tests
make test

# Run with verbose output
uv run pytest -vv

# Run specific test file
uv run pytest tests/test_inconnu.py -vv

# Run specific test class
uv run pytest tests/test_inconnu.py::TestInconnuPseudonymizer -vv
```

## Usage Examples

### Basic Text Anonymization

```python
from inconnu import Inconnu

# Simple initialization - no Config class required!
inconnu = Inconnu()  # Uses sensible defaults

# Simple anonymization - just the redacted text
text = "John Doe from New York visited Paris last summer."
redacted = inconnu.redact(text)
print(redacted)
# Output: "[PERSON] from [GPE] visited [GPE] [DATE]."

# Pseudonymization - get both redacted text and entity mapping
redacted_text, entity_map = inconnu.pseudonymize(text)
print(redacted_text)
# Output: "[PERSON_0] from [GPE_0] visited [GPE_1] [DATE_0]."
print(entity_map)
# Output: {'[PERSON_0]': 'John Doe', '[GPE_0]': 'New York', '[GPE_1]': 'Paris', '[DATE_0]': 'last summer'}

# Advanced usage with full metadata (original API)
result = inconnu(text=text)
print(result.redacted_text)
print(f"Processing time: {result.processing_time_ms:.2f}ms")
```

### Async and Batch Processing

```python
import asyncio

# Async processing for non-blocking operations
async def process_texts():
    inconnu = Inconnu()

    # Single async processing
    text = "John Doe called from +1-555-123-4567"
    redacted = await inconnu.redact_async(text)
    print(redacted)  # "[PERSON] called from [PHONE_NUMBER]"

    # Batch async processing
    texts = [
        "Alice Smith visited Berlin",
        "Bob Jones went to Tokyo",
        "Carol Brown lives in Paris"
    ]
    results = await inconnu.redact_batch_async(texts)
    for result in results:
        print(result)

asyncio.run(process_texts())
```

### Customer Service Email Processing

```python
# Process customer service email with personal data
customer_email = """
Dear SolarTech Team,

I am Max Mustermann living at Hauptstraße 50, 80331 Munich, Germany.
My phone number is +49 89 1234567 and my email is max@example.com.
I need to return my solar modules (Order: ST-78901) due to relocation.

Best regards,
Max Mustermann
"""

# Simple redaction
redacted = inconnu.redact(customer_email)
print(redacted)
# Personal identifiers are automatically detected and redacted
```

### Multi-language Support

```python
# German language processing - simplified!
inconnu_de = Inconnu("de")  # Just specify the language

german_text = "Herr Schmidt aus München besuchte Berlin im März."
redacted = inconnu_de.redact(german_text)
print(redacted)
# Output: "[PERSON] aus [GPE] besuchte [GPE] [DATE]."
```

### Custom Entity Recognition

```python
from inconnu import Inconnu, NERComponent
import re

# Add custom entity recognition
custom_components = [
    NERComponent(
        label="CREDIT_CARD",
        pattern=re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
        processing_function=None
    )
]

# Simple initialization with custom components
inconnu_custom = Inconnu(
    language="en",
    custom_components=custom_components
)

# Test custom entity detection
text = "My card number is 1234 5678 9012 3456"
redacted = inconnu_custom.redact(text)
print(redacted)  # "My card number is [CREDIT_CARD]"
```

### Context Manager for Resource Management

```python
# Automatic resource cleanup
with Inconnu() as inc:
    redacted = inc.redact("Sensitive data about John Doe")
    print(redacted)
# Resources automatically cleaned up
```

### Error Handling

```python
from inconnu import Inconnu, TextTooLongError, ProcessingError

inconnu = Inconnu(max_text_length=100)  # Set small limit for demo

try:
    long_text = "x" * 200  # Exceeds limit
    result = inconnu.redact(long_text)
except TextTooLongError as e:
    print(f"Text too long: {e}")
    # Error includes helpful suggestions for resolution
except ProcessingError as e:
    print(f"Processing failed: {e}")
```

## Use Cases

### 1. **Customer Support Systems**
Automatically redact personal information from customer service emails, chat logs, and support tickets while maintaining context for analysis.

### 2. **Legal Document Processing**
Anonymize legal documents, contracts, and case files for training, analysis, or public release while ensuring GDPR compliance.

### 3. **Medical Record Anonymization**
Process medical records and research data to remove patient identifiers while preserving clinical information for research purposes.

### 4. **Financial Transaction Analysis**
Redact personal financial information from transaction logs and banking communications for fraud analysis and compliance reporting.

### 5. **Survey and Feedback Analysis**
Anonymize customer feedback, survey responses, and user-generated content for analysis while protecting respondent privacy.

### 6. **Training Data Preparation**
Prepare training datasets for machine learning models by removing personal identifiers from text data while maintaining semantic meaning.

## Supported Entity Types

- **Standard Entities**: PERSON, GPE (locations), DATE, ORG, MONEY
- **Custom Entities**: EMAIL, IBAN, PHONE_NUMBER
- **Enhanced Detection**: Person titles (Dr, Mr, Ms), international phone numbers
- **Multilingual**: English, German, Italian, Spanish, and French language support

## Features

- **Robust Entity Detection**: Advanced NLP with spaCy models and custom regex patterns
- **Dual Processing Modes**: Anonymization (`[PERSON]`) and pseudonymization (`[PERSON_0]`)
- **Complete Audit Trail**: Timestamping, hashing, and processing metadata
- **Reversible Processing**: Full de-anonymization capabilities with entity mapping
- **Performance Optimized**: Singleton pattern for model loading, configurable limits
- **GDPR Compliant**: Built-in data retention policies and compliance features

## Contributing

We welcome contributions to Inconnu! As an open source project, we believe in the power of community collaboration to build better privacy tools.

### How to Contribute

#### 1. **Bug Reports & Feature Requests**
- Open an issue on GitHub with detailed descriptions
- Include code examples and expected vs actual behavior
- Tag issues appropriately (bug, enhancement, documentation)

#### 2. **Code Contributions**
```bash
# Fork the repository and create a feature branch
git checkout -b feature/your-feature-name

# Make your changes and ensure tests pass
make test
make lint

# Submit a pull request with:
# - Clear description of changes
# - Test coverage for new features
# - Updated documentation if needed
```

#### 3. **Development Guidelines**
- Follow existing code style and patterns
- Add tests for new functionality
- Update documentation for user-facing changes
- Ensure GDPR compliance considerations are addressed

#### 4. **Areas for Contribution**
- **Language Support**: Add new language models and region-specific entity detection
- **Custom Entities**: Implement detection for industry-specific identifiers
- **Performance**: Optimize processing speed and memory usage
- **Documentation**: Improve examples, tutorials, and API documentation
- **Testing**: Expand test coverage and edge case handling

#### 5. **Code Review Process**
- All contributions require code review
- Automated tests must pass
- Documentation updates are appreciated
- Maintain backward compatibility when possible

### Community Guidelines

- **Be Respectful**: Foster an inclusive environment for all contributors
- **Privacy First**: Always consider privacy implications of changes
- **Security Minded**: Report security issues privately before public disclosure
- **Quality Focused**: Prioritize code quality and comprehensive testing

### Getting Help

- **Discussions**: Use GitHub Discussions for questions and ideas
- **Issues**: Report bugs and request features through GitHub Issues
- **Documentation**: Check existing docs and contribute improvements

Thank you for helping make Inconnu a better tool for data privacy and GDPR compliance!

## Publishing to PyPI

### For Maintainers

To publish a new version to PyPI:

1. **Configure Trusted Publisher** (first time only):
   - Go to https://pypi.org/manage/project/inconnu/settings/publishing/
   - Add a new trusted publisher:
     - Publisher: GitHub
     - Organization/username: `0xjgv`
     - Repository name: `inconnu`
     - Workflow name: `publish.yml`
     - Environment name: `pypi` (optional but recommended)
   - For Test PyPI, do the same at https://test.pypi.org with environment name: `testpypi`

2. **Update Version**: Update the version in `pyproject.toml` and `inconnu/__init__.py`

3. **Create a Git Tag**:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

4. **GitHub Actions**: The workflow will automatically:
   - Run tests on Python 3.10, 3.11, and 3.12
   - Build the package
   - Publish to PyPI using Trusted Publisher (no API tokens needed!)
   - Generate PEP 740 attestations for security

5. **Test PyPI Publishing**:
   - Use workflow_dispatch to manually trigger Test PyPI publishing
   - Go to Actions → Publish to PyPI → Run workflow

### Manual Publishing (if needed)

```bash
# Build the package
uv build

# Check the package
twine check dist/*

# Upload to Test PyPI (requires API token)
twine upload --repository testpypi dist/*

# Upload to PyPI (requires API token)
twine upload dist/*
```

### GitHub Environments (Recommended)

Configure GitHub environments for additional security:
1. Go to Settings → Environments
2. Create `pypi` and `testpypi` environments
3. Add protection rules:
   - Required reviewers
   - Restrict to specific tags (e.g., `v*`)
   - Add deployment branch restrictions

## Additional Resources

- [spaCy Models Directory](https://spacy.io/models) - Complete list of available language models
- [spaCy Model Releases](https://github.com/explosion/spacy-models) - GitHub repository for model updates
- [pgeocode](https://pypi.org/project/pgeocode/) - Geographic location processing (potential future integration)
