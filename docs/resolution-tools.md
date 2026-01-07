# Resolution Tools

Possible libraries and other tools to consider for implementing resolvers.

**These are ChatGPT Suggestions, with some edits by Brandizi.**

Here are practical options for implementing a simple real (non-mock) AbstractResolver for entity resolution in Python, focusing on string matching and RDF analysis:

## String Matching Approaches

- **RapidFuzz**: Fast, pure Python fuzzy string matching. Great for comparing entity labels, names, or IDs.
  - [RapidFuzz Documentation](https://maxbachmann.github.io/RapidFuzz/)
  - Use: Compare entity names/labels for similarity, return matches above a threshold.

- **TheFuzz**: FuzzyWuzzy migrated to [this](https://github.com/seatgeek/thefuzz). TODO: check how it compares to RapidFuzz.

- **FuzzyWuzzy**: Popular fuzzy string matching library (RapidFuzz is faster and more maintained). Migrated (see above).
  
## RDF Structure Analysis

- **OWLReady2**: For ontology-based reasoning (class hierarchies, equivalence).
  - [OWLReady2 Documentation](https://owlready2.readthedocs.io/en/latest/)
  - Use: Resolve entities based on ontology semantics, not just string similarity.

## Hybrid Approaches

- **spaCy**: For advanced NLP-based matching, extract and compare entity names, descriptions, or other text fields.
  - [spaCy Documentation](https://spacy.io/)

- **SKOSProvider**: If RDF data uses SKOS, use libraries/tools for SKOS concept matching (label, synonym, broader/narrower).
  - [Python SKOSProvider](https://github.com/edsu/skosprovider)
