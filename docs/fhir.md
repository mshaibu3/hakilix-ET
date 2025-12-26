# FHIR profiling + validation

This repo includes a minimal FHIR Observation builder/validator for demo purposes (`hakilix/fhir_validation.py`).

Production recommendations:
- Adopt an NHS integration route (e.g., MESH, PDS, GP Connect, Virtual Ward vendor APIs) and align to the required UK FHIR profiles.
- Validate against official profile artifacts (StructureDefinitions) using a dedicated validator (HAPI FHIR validator, Smile CDR validator, etc.)
- Enforce profile invariants in CI (contract tests) and in the message pipeline.
