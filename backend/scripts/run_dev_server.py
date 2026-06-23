import os
import sys
from pathlib import Path

import uvicorn


def main() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(backend_dir))

    # WSL and OneDrive-mounted folders can break watchfiles' native watcher.
    os.environ.setdefault("WATCHFILES_FORCE_POLLING", "true")

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[str(backend_dir)],
        reload_excludes=[
            ".pytest_cache/*",
            "__pycache__/*",
            "*.pyc",
            "data.json",
        ],
    )


if __name__ == "__main__":
    main()
