import os

import uvicorn


def main() -> None:
    reload = os.getenv("LITERAG_RELOAD", "").lower() in {"1", "true", "yes"}
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=reload)


if __name__ == "__main__":
    main()
