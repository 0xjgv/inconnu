# Inconnu

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
- UV package manager (recommended) or pip

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/0xjgv/inconnu.git
   cd inconnu
   ```

2. **Install dependencies**:
   ```bash
   make install
   ```

3. **Download required NLP models**:
   ```bash
   make model-install
   ```

4. **Verify installation**:
   ```bash
   make test
   ```

### Manual Installation

If you prefer manual installation:

```bash
# Install dependencies
uv sync --group dev

# Download spaCy model
uv run python -m spacy download en_core_web_sm

# Run tests
uv run pytest -vv
```

### Installing Additional Models

Inconnu supports multiple spaCy models for enhanced accuracy. The default `en_core_web_sm` model is lightweight and fast, but you can install more accurate models:

#### English Models
```bash
# Small model (default) - 15MB, fast processing
uv run python -m spacy download en_core_web_sm

# Large model - 560MB, higher accuracy
uv run python -m spacy download en_core_web_lg

# Transformer model - 438MB, highest accuracy
uv run python -m spacy download en_core_web_trf
```

#### German Models
```bash
# Small German model
uv run python -m spacy download de_core_news_sm

# Medium German model - better accuracy
uv run python -m spacy download de_core_news_md

# Large German model - highest accuracy
uv run python -m spacy download de_core_news_lg
```

#### Using Different Models

To use a different model, specify it when initializing the EntityRedactor:

```python
from inconnu.nlp.entity_redactor import EntityRedactor, SpacyModels

# Use transformer model for highest accuracy
entity_redactor = EntityRedactor(
    custom_components=None,
    language="en",
    model_name=SpacyModels.EN_CORE_WEB_TRF  # High accuracy transformer model
)
```

**Model Selection Guide:**
- `en_core_web_sm`: Fast processing, good for high-volume processing
- `en_core_web_lg`: Better accuracy, moderate processing time
- `en_core_web_trf`: Highest accuracy, slower processing (recommended for sensitive data)

For more models, visit the [spaCy Models Directory](https://spacy.io/models).

## Development Setup

### Available Commands

```bash
# Development workflow
make install          # Install all dependencies
make model-install    # Download required spaCy models
make test            # Run full test suite
make lint            # Check code with ruff
make format          # Format code with ruff
make fix             # Auto-fix linting issues
make clean           # Format, lint, fix, and clean cache
make update-deps     # Update dependencies
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
- **Multilingual**: English and German language support

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

## Additional Resources

- [spaCy Models Directory](https://spacy.io/models) - Complete list of available language models
- [spaCy Model Releases](https://github.com/explosion/spacy-models) - GitHub repository for model updates
- [pgeocode](https://pypi.org/project/pgeocode/) - Geographic location processing (potential future integration)
