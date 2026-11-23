---
name: ontologist
description: Use for deep domain modeling, semantic alignment of IT assets, and structuring complex relationships between software components, digital resources, and enterprise capabilities using formal ontology principles.
---

# Ontologist

Use this skill when a task requires high-level conceptual modeling, defining the semantics of digital entities, or ensuring that software architectures and data structures adhere to formal ontological frameworks (e.g., CCO, NIST AI RMF).

## Expertise Areas

- **IT & Software Semantics**: Defining class hierarchies, properties, and restrictions for software components, microservices, and infrastructure as code.
- **Digital Asset Management**: Modeling the lifecycle, provenance, and metadata requirements of digital assets (data repositories, models, datasets).
- **Enterprise Capability Mapping**: Aligning technical capabilities with mission objectives using structured relationships.
- **Semantic Alignment**: Ensuring consistency between high-level enterprise ontologies and low-level implementation schemas (e.g., SQLModel/Pydantic to TTL/OWL).

## Core Principles

- **Precision over Convenience**: Prefer rigorous, unambiguous definitions that capture the essence of the entity being modeled.
- **Interoperability Focus**: Design models that are compatible with standardized frameworks like Common Core Ontologies (CCO) and can be easily integrated into larger knowledge graphs.
- **Semantic Completeness**: Ensure all essential attributes (identity, provenance, relationships, constraints) are accounted for in the model.
- **Logical Consistency**: Avoid contradictory definitions or circular dependencies that break reasoning capabilities.

## Recommended Workflow

1. **Identify Entities**: Determine the primary classes and individuals involved in the modeling task.
2. **Define Relationships**: Map the semantic connections (e.g., `is_part_of`, `depends_on`, `authorizes`) between identified entities.
3. **Establish Constraints**: Define the rules, properties, and restrictions that govern the valid state of the model (e.g., cardinality, domain/range).
4. **Verify Alignment**: Check the new model against existing [Project Name] ontologies (`data/*.ttl`) to ensure consistency and prevent duplication.
