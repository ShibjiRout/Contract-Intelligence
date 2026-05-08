# /scaffold-module

Generate a complete new module with router + schemas + service + tests.

## Usage
```
/scaffold-module <module_name> <HTTP_METHOD> <path>
```

## Example
```
/scaffold-module indemnity_clause GET /clauses/indemnity
```

## What It Creates
1. `contracts_platform/api/routers/<module_name>.py` — FastAPI router with one stub endpoint
2. `contracts_platform/api/schemas/<module_name>.py` — Pydantic v2 request + response models
3. `contracts_platform/<domain>/<module_name>_service.py` — async service class stub
4. `tests/unit/test_<module_name>.py` — pytest stubs for the service
5. Registers the new router in `contracts_platform/api/main.py`

## Reference Pattern
Before generating, read `contracts_platform/api/routers/contracts.py` and
`contracts_platform/api/schemas/contract.py` to match the existing import style,
decorator pattern, auth dependency pattern, and error handling style.

## Rules
- All endpoints must include `Depends(require_role(...))` — ask user which role if not specified
- Response models must be Pydantic v2 with `model_config = ConfigDict(from_attributes=True)`
- Service class must be async — all methods use `async def`
- Test file must import and test the service class directly (not the HTTP layer)
