#!/usr/bin/env python3
"""
Multilingual Data Processing Example

This example demonstrates how to use Inconnu for processing text in multiple
languages including German, Italian, Spanish, and French, showcasing the
library's international capabilities and GDPR compliance features.

Use Cases:
- International business communications
- Multilingual customer support
- Cross-border legal documents
- Global employee data
- Multi-country research studies
"""

from inconnu import Inconnu

print("=" * 60)
print("Multilingual Data Processing with Inconnu")
print("=" * 60)

# Example 1: German Business Communication
print("\n1. GERMAN (DEUTSCH) - BUSINESS EMAIL")
print("-" * 30)

inconnu_de = Inconnu(language="de")

german_email = """
Betreff: Vertragsverlängerung - Kunde: Müller GmbH
Von: thomas.schmidt@beispielfirma.de
An: vertrieb@lieferant.de
Datum: 28. März 2024

Sehr geehrte Frau Wagner,

ich möchte Sie über die Vertragsverlängerung unseres Kunden Müller GmbH 
informieren. Herr Klaus Müller (Geschäftsführer) hat die Verlängerung für 
weitere 24 Monate bestätigt.

Kundendaten:
- Firma: Müller GmbH
- Geschäftsführer: Klaus Müller
- Adresse: Hauptstraße 123, 10115 Berlin
- Telefon: +49 30 12345678
- E-Mail: k.mueller@mueller-gmbh.de
- Umsatzsteuer-ID: DE123456789

Ansprechpartner:
- Einkauf: Frau Anna Schmidt (a.schmidt@mueller-gmbh.de)
- Buchhaltung: Herr Peter Weber (Tel: 030-12345679)

Der Jahresumsatz beträgt 250.000 EUR. Die IBAN für Lastschriften lautet:
DE89 3704 0044 0532 0130 00

Bitte senden Sie den neuen Vertrag an meine Assistentin Frau Lisa Becker
(l.becker@beispielfirma.de) mit Kopie an unseren Geschäftsführer Herrn 
Dr. Michael Hoffmann.

Mit freundlichen Grüßen
Thomas Schmidt
Vertriebsleiter
Mobil: +49 171 9876543
"""

redacted_de = inconnu_de.redact(german_email)
print("Anonymized German Email:")
print(redacted_de[:600] + "...")

# Example 2: Italian Customer Data
print("\n\n2. ITALIAN (ITALIANO) - CUSTOMER RECORD")
print("-" * 30)

inconnu_it = Inconnu(language="it")

italian_customer = """
SCHEDA CLIENTE
Azienda: Rossi & Partners S.r.l.
Data: 28 marzo 2024

INFORMAZIONI AZIENDALI
Ragione Sociale: Rossi & Partners S.r.l.
Partita IVA: IT12345678901
Codice Fiscale: 12345678901
Sede Legale: Via Roma 45, 20121 Milano
Telefono: +39 02 12345678
Email: info@rossipartners.it

CONTATTI PRINCIPALI
Amministratore Delegato: Dott. Giuseppe Rossi
Email: g.rossi@rossipartners.it
Cellulare: +39 335 1234567

Responsabile Acquisti: Sig.ra Maria Bianchi
Email: m.bianchi@rossipartners.it
Tel. diretto: +39 02 12345679

Responsabile Amministrativo: Dott. Marco Ferrari
Email: m.ferrari@rossipartners.it

RIFERIMENTI BANCARI
Banca: Intesa Sanpaolo
IBAN: IT60 X054 2811 1010 0000 0123 456
SWIFT: BCITITMM

INFORMAZIONI COMMERCIALI
Fatturato annuo: € 2.500.000
Limite di credito: € 150.000
Condizioni di pagamento: 60 giorni d.f.f.m.

Note: Il Sig. Rossi preferisce essere contattato nel pomeriggio. La Sig.ra 
Bianchi è in maternità fino a maggio 2024, sostituita da Paolo Verdi 
(p.verdi@rossipartners.it, cell. 348 9876543).
"""

redacted_it = inconnu_it.redact(italian_customer)
print("Anonymized Italian Customer Record:")
print(redacted_it[:600] + "...")

# Example 3: Spanish Legal Document
print("\n\n3. SPANISH (ESPAÑOL) - LEGAL CONTRACT")
print("-" * 30)

inconnu_es = Inconnu(language="es")

spanish_contract = """
CONTRATO DE PRESTACIÓN DE SERVICIOS

En Madrid, a 28 de marzo de 2024

REUNIDOS

De una parte, D. Carlos García Rodríguez, con DNI 12345678-A, en calidad 
de Administrador Único de TECNOLOGÍA AVANZADA S.L., con CIF B-12345678, 
domicilio social en Calle Gran Vía 123, 28013 Madrid, email: 
cgarcia@tecnologiaavanzada.es, teléfono: +34 91 123 4567.

De otra parte, Dña. Isabel Martínez López, con DNI 87654321-B, autónoma 
con domicilio profesional en Avenida de América 45, 28028 Madrid, email: 
isabel.martinez@consultoría.es, móvil: +34 666 123 456.

EXPONEN

PRIMERO.- Que la empresa necesita servicios de consultoría especializada 
en transformación digital, área en la que la Sra. Martínez cuenta con 
15 años de experiencia, habiendo trabajado previamente con empresas como 
Banco Santander (contacto: Jorge Fernández, jfernandez@santander.es) e 
Iberdrola (contacto: Ana Sánchez, asanchez@iberdrola.es).

SEGUNDO.- Que el proyecto tendrá una duración de 6 meses con un presupuesto 
total de 45.000 EUR más IVA, pagaderos mensualmente a la cuenta 
ES12 1234 5678 9012 3456 7890.

CLÁUSULAS...

Firmado:
Carlos García Rodríguez          Isabel Martínez López
TECNOLOGÍA AVANZADA S.L.        Consultora
"""

redacted_es = inconnu_es.redact(spanish_contract)
print("Anonymized Spanish Contract:")
print(redacted_es[:600] + "...")

# Example 4: French Medical Record
print("\n\n4. FRENCH (FRANÇAIS) - MEDICAL RECORD")
print("-" * 30)

inconnu_fr = Inconnu(language="fr")

french_medical = """
DOSSIER MÉDICAL CONFIDENTIEL
Hôpital Saint-Louis, Paris
Date: 28 mars 2024

PATIENT
Nom: DUBOIS, Marie-Claire
Date de naissance: 15 juillet 1975
Numéro de Sécurité Sociale: 2 75 07 75 115 234 56
Adresse: 45 rue de la République, 75011 Paris
Téléphone: +33 6 12 34 56 78
Email: marie.dubois@email.fr

MÉDECIN TRAITANT
Dr. Jean-Pierre Martin
Cabinet Médical du Marais
15 rue des Archives, 75003 Paris
Tél: +33 1 42 77 88 99

ANTÉCÉDENTS
- Diabète type 2 (diagnostiqué en 2018)
- Hypertension (traitée depuis 2020)
- Allergie: Pénicilline

CONSULTATION DU JOUR
Motif: Douleurs thoraciques
Accompagnée par: Son mari, M. Pierre Dubois (portable: 06 98 76 54 32)

EXAMEN
Tension: 145/90
Poids: 72 kg
Le Dr. Sophie Bernard (cardiologue) a été consultée. Elle recommande un 
ECG d'effort. Contact: s.bernard@hopital-saintlouis.fr

PRESCRIPTION
- Metformine 850mg: 2 fois/jour
- Amlodipine 5mg: 1 fois/jour

SUIVI
Prochain RDV: 15 avril 2024 à 14h30
Contact secrétariat: Mme Lefebvre au 01 42 49 49 49

Urgences: Contacter le fils, Thomas Dubois: 06 11 22 33 44
"""

redacted_fr = inconnu_fr.redact(french_medical)
print("Anonymized French Medical Record:")
print(redacted_fr[:600] + "...")

# Example 5: Mixed Language Document
print("\n\n5. MIXED LANGUAGE PROCESSING")
print("-" * 30)

# Process a document with mixed languages (using English model)
inconnu_mixed = Inconnu(language="en")

mixed_document = """
INTERNATIONAL TEAM MEETING NOTES
Date: March 28, 2024
Location: Zoom Meeting

ATTENDEES:
- John Smith (USA) - john.smith@globalcorp.com
- Hans Mueller (Germany) - hans.mueller@globalcorp.de
- Giuseppe Rossi (Italy) - g.rossi@globalcorp.it
- María García (Spain) - m.garcia@globalcorp.es
- François Dubois (France) - f.dubois@globalcorp.fr

KEY POINTS DISCUSSED:

John Smith: "Our Q1 revenue was $2.5M, exceeding targets by 15%."

Hans Mueller: "Die deutsche Niederlassung hat 1,8 Millionen Euro erwirtschaftet. 
Kontakt: Frau Schmidt unter +49 30 123456."

Giuseppe Rossi: "Le vendite in Italia sono cresciute del 20%. Il nostro 
cliente principale è Fiat (contatto: Mario Bianchi)."

María García: "Las oficinas de Madrid y Barcelona necesitan más personal. 
Contactar con RRHH: Isabel Martínez (i.martinez@rrhh.es)."

François Dubois: "Le bureau de Paris déménage au 123 Avenue des Champs-Élysées. 
Nouveau téléphone: +33 1 42 86 82 00."

ACTION ITEMS:
- Hans to send report to CEO Michael Johnson (mjohnson@globalcorp.com)
- Maria to coordinate with HR Director Lisa Chen (lchen@hr.globalcorp.com)
- All regional reports due by April 15, 2024
"""

# Note: English model will catch some entities but may miss language-specific ones
redacted_mixed = inconnu_mixed.redact(mixed_document)
print("Anonymized Mixed Language Document:")
print(redacted_mixed[:800] + "...")

# Example 6: Comparative Processing
print("\n\n6. COMPARATIVE LANGUAGE PROCESSING")
print("-" * 30)

# Same content in different languages
test_content = {
    "en": "Mr. John Smith from London called +44 20 7123 4567 about invoice #12345.",
    "de": "Herr Johann Schmidt aus Berlin rief +49 30 1234567 wegen Rechnung #12345 an.",
    "it": "Il Sig. Giovanni Smith da Roma ha chiamato +39 06 123 4567 per fattura #12345.",
    "es": "El Sr. Juan Smith de Madrid llamó al +34 91 123 4567 sobre factura #12345.",
    "fr": "M. Jean Smith de Paris a appelé le +33 1 42 12 34 56 concernant facture #12345."
}

print("Comparative anonymization across languages:")
for lang, text in test_content.items():
    if lang == "en":
        inconnu_lang = Inconnu()
    else:
        inconnu_lang = Inconnu(language=lang)
    
    redacted = inconnu_lang.redact(text)
    print(f"\n{lang.upper()}: {text}")
    print(f"     → {redacted}")

# Best Practices Summary
print("\n\n" + "=" * 60)
print("BEST PRACTICES FOR MULTILINGUAL DATA")
print("=" * 60)
print("""
1. LANGUAGE SELECTION:
   - Always specify the correct language for optimal results
   - Use language detection when processing unknown content
   - Consider regional variations (e.g., DE vs. CH German)

2. GDPR COMPLIANCE:
   - Extra attention to EU data (addresses, IDs, phone formats)
   - Language-specific privacy terms and regulations
   - Cross-border data transfer considerations

3. ENTITY VARIATIONS:
   - Phone formats differ by country (+49, +33, +39, etc.)
   - Name patterns vary (surnames, titles, particles)
   - Address formats are country-specific

4. MIXED CONTENT:
   - Process with primary language model
   - Consider multiple passes for mixed documents
   - Add custom patterns for international formats

5. QUALITY ASSURANCE:
   - Test with native speakers
   - Verify cultural naming conventions
   - Check for language-specific false positives

Available Languages:
- English (en) - Default
- German (de) - GDPR optimized
- Italian (it) - EU compliant
- Spanish (es) - Includes Latin American variants
- French (fr) - Includes Canadian variants
""")

print("\nExample completed successfully!")