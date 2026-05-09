import os

import uvicorn

from contracts_platform.api.main import app  # noqa: F401 — exposed for `uvicorn main:app`

if __name__ == "__main__":
    uvicorn.run(
        "contracts_platform.api.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info"),
    )
