"""Console entry point for running the helper during development."""

from __future__ import annotations

import pathlib
import sys

if __package__ is None or __package__ == "":  # pragma: no cover
    project_root = pathlib.Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from helper_app.worker import main


if __name__ == "__main__":  # pragma: no cover
    main()

