# /add-clause-type

Add a new clause type consistently across all layers.

## Usage
```
/add-clause-type <CLAUSE_TYPE_NAME> [--required] [--jurisdiction <code>]
```

## Example
```
/add-clause-type FORCE_MAJEURE --required --jurisdiction US
```

## Steps
1. Add to `ClauseType` enum in `contracts_platform/core/constants.py`
2. Add to `clause_type_registry` PostgreSQL table via new Alembic migration file
3. If `--required`: insert row into `playbook_rules` marking this type as required for the jurisdiction
4. Add to required clause list in `contracts_platform/pipeline/clause_extraction/missing_clause_detector.py`
5. Add test case stub in `tests/unit/test_clause_validator.py`
6. Print checklist of what still needs manual update:
   - [ ] LLM extraction prompt (add examples for this clause type)
   - [ ] Qdrant: seed accepted wording examples if available
   - [ ] Neo4j: add clause type to allowed node type list

## Rules
- Read the existing `ClauseType` enum and latest Alembic migration before generating
- Follow the exact same migration file naming pattern as existing versions
- Never skip the test stub step
