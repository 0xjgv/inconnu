# Inconnu Examples

This directory contains practical examples demonstrating various use cases for the Inconnu data privacy library. Each example includes real-world scenarios, sample data, and comprehensive usage patterns.

## 📚 Available Examples

### Core Use Cases

1. **[Healthcare Records](01_healthcare_records.py)** - Anonymize patient data, medical records, and clinical trial information
2. **[Legal Documents](02_legal_documents.py)** - Redact sensitive information from court documents, contracts, and legal correspondence
3. **[HR & Employment](03_hr_employment.py)** - Process resumes, employee records, and recruitment data for bias-free handling
4. **[Financial Services](04_financial_services.py)** - Anonymize banking transactions, customer communications, and financial reports
5. **[Customer Support](05_customer_support.py)** - Redact personal information from support tickets, chat logs, and feedback

### Additional Scenarios

6. **[Education Data](06_education_data.py)** - Protect student privacy in academic records and research
7. **[Research & Surveys](07_research_surveys.py)** - Anonymize interview transcripts and survey responses
8. **[Multilingual Processing](08_multilingual.py)** - Examples in German, Italian, Spanish, and French
9. **[Batch Processing](09_batch_processing.py)** - High-volume data processing with async operations
10. **[Custom Entities](10_custom_entities.py)** - Industry-specific pattern recognition (SSN, passport numbers, etc.)

## 🚀 Getting Started

### Installation

```bash
# Install Inconnu
pip install inconnu

# Download required language models
inconnu-download en  # English
inconnu-download de  # German (for multilingual examples)
inconnu-download all # All supported languages
```

### Running Examples

Each example is a standalone Python script:

```bash
# Run a specific example
python examples/01_healthcare_records.py

# Run all examples
for example in examples/*.py; do
    echo "Running $example..."
    python "$example"
done
```

## 📊 Example Structure

Each example follows a consistent structure:

1. **Use Case Description** - Real-world scenario explanation
2. **Sample Data** - Realistic test data for the domain
3. **Basic Usage** - Simple anonymization example
4. **Advanced Features** - Pseudonymization, de-anonymization, custom entities
5. **Best Practices** - Domain-specific tips and GDPR considerations

## 🔑 Key Features Demonstrated

- **Anonymization**: Replace PII with generic labels (`[PERSON]`, `[EMAIL]`)
- **Pseudonymization**: Replace with indexed labels (`[PERSON_0]`) for de-anonymization
- **Entity Mapping**: Track original values for data recovery
- **Custom Patterns**: Add domain-specific entity recognition
- **Batch Processing**: Handle multiple documents efficiently
- **Async Operations**: Non-blocking processing for web applications
- **Multi-language**: Support for EN, DE, IT, ES, FR

## 📋 Quick Reference

### Basic Anonymization

```python
from inconnu import Inconnu

inconnu = Inconnu()
text = "John Doe lives in New York"
redacted = inconnu.redact(text)
# Output: "[PERSON] lives in [GPE]"
```

### Pseudonymization with Mapping

```python
redacted_text, entity_map = inconnu.pseudonymize(text)
# redacted_text: "[PERSON_0] lives in [GPE_0]"
# entity_map: {'[PERSON_0]': 'John Doe', '[GPE_0]': 'New York'}
```

### Custom Entity Detection

```python
from inconnu import Inconnu, NERComponent
import re

custom_components = [
        processing_func=None
]

inconnu = Inconnu(custom_components=custom_components)
```

## 🛡️ GDPR Compliance Notes

- All examples demonstrate GDPR-compliant data handling
- Personal data is never logged or stored permanently
- Examples include data retention and deletion patterns
- Audit trail capabilities are highlighted where relevant

## 📝 Contributing

To add a new example:

1. Create a new numbered Python file (e.g., `11_new_usecase.py`)
2. Follow the structure of existing examples
3. Include realistic sample data
4. Add error handling and edge cases
5. Update this README with the new example

## 🤝 Support

For questions about these examples:

- Check the [main documentation](../README.md)
- Review the [API reference](https://inconnu.ai/docs)
- Open an issue on [GitHub](https://github.com/0xjgv/inconnu)
