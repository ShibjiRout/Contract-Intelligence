# /review-security

Audit the API routes, auth layer, and file upload handler for security issues.

## Usage
```
/review-security [--scope api|auth|upload|all]
```

## Checks

### API Routes (`--scope api`)
- Every function in `contracts_platform/api/routers/` has `current_user` or `api_key` in dependencies
- No endpoint returns raw exception messages (must use RFC 7807 Problem Detail)
- Rate limiting middleware is registered in `api/main.py`

### Auth Layer (`--scope auth`)
- JWT algorithm is not `none` or `HS256` without secret validation
- Access token expiry is set (not None or 0)
- Refresh token rotation is implemented (new token issued on every refresh)
- Passwords hashed with bcrypt (not MD5 or SHA-1)
- No tokens logged anywhere in the auth module

### File Upload (`--scope upload`)
- MIME type check is present (not just extension check)
- File size limit is enforced before reading file content
- SHA-256 duplicate check runs before dispatching to Celery
- File stored to Azure Blob Storage via `file_handling/storage.py` — never local disk
- File path stored encrypted in MongoDB via `core/encryption.py`

### Automated Scans
- Run `bandit -r contracts_platform/ -ll` — report all HIGH severity findings
- Grep `.env.example` for real-looking secrets (API keys, passwords, connection strings with credentials)
- Grep `contracts_platform/` for hardcoded IP addresses

## Output Format
Numbered findings list:
```
[HIGH]   api/routers/admin.py:45  — endpoint GET /admin/users has no auth dependency
[MEDIUM] auth/jwt_handler.py:12   — access token expiry not validated on decode
[LOW]    file_handling/storage.py:88 — file path logged before encryption
```

## Rules
- Never modify files during this check — report only
- If scope not specified, run all checks
