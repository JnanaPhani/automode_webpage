from __future__ import annotations

import sys
from pathlib import Path

from PySide6 import QtGui, QtWidgets

from desktop_app.runtime import HelperRuntime
from desktop_app.ui import MainWindow


def run() -> None:
    """Launch the desktop helper application."""
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Zenith Tek Sensor Configuration Tool")
    app.setOrganizationName("Zenith Tek")
    app.setApplicationVersion("1.0.0")
    
    # Set application icon if available
    icon_paths = [
        Path(__file__).parent.parent / "public" / "app-icon.png",
        Path(sys.executable).parent / "public" / "app-icon.png",
        Path(sys.executable).parent.parent / "public" / "app-icon.png",
    ]
    for icon_path in icon_paths:
        if icon_path.exists():
            app.setWindowIcon(QtGui.QIcon(str(icon_path)))
            break
    
    runtime = HelperRuntime()
    window = MainWindow(runtime)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":  # pragma: no cover
    run()


