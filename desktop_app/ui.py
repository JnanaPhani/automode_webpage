from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from helper_app.controller import SensorType

from desktop_app.runtime import DeviceIdentity, HelperRuntime


class MainWindow(QtWidgets.QMainWindow):
    """Primary window for the desktop helper."""

    def __init__(self, runtime: HelperRuntime) -> None:
        super().__init__()
        self.runtime = runtime
        self._detect_after_connect = False
        self._pending_sensor_type: Optional[SensorType] = None
        self._exit_auto_then_detect = False
        self.setWindowTitle("Zenith Tek Sensor Configuration Tool")
        self.resize(900, 650)
        self._build_ui()
        self._wire_signals()
        self.runtime.publish_ports()

    # UI construction ---------------------------------------------------------
    def _build_ui(self) -> None:
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setSpacing(8)
        layout.setContentsMargins(15, 15, 15, 15)

        # Header with logo and title
        header_widget = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 8)
        header_layout.setSpacing(12)

        # Logo
        logo_label = QtWidgets.QLabel()
        # Try multiple paths: packaged exe location, development location
        logo_paths = [
            Path(__file__).parent.parent / "public" / "zenithtek-logo.png",  # Development
            Path(sys.executable).parent / "public" / "zenithtek-logo.png",  # Packaged (if in same dir)
            Path(sys.executable).parent.parent / "public" / "zenithtek-logo.png",  # Packaged (if in _internal)
        ]
        logo_path = None
        for path in logo_paths:
            if path.exists():
                logo_path = path
                break
        
        if logo_path:
            pixmap = QtGui.QPixmap(str(logo_path))
            # Scale logo to reasonable size (max height 50px, maintain aspect ratio)
            scaled_pixmap = pixmap.scaled(180, 50, QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        else:
            logo_label.setText("Zenith Tek")
            logo_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #008080;")
        header_layout.addWidget(logo_label)

        # Title and subtitle
        title_widget = QtWidgets.QWidget()
        title_layout = QtWidgets.QVBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)

        title_label = QtWidgets.QLabel("Sensor Configuration Tool")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        subtitle_label = QtWidgets.QLabel("Configure Epson Vibration Sensors and IMUs")
        subtitle_label.setStyleSheet("font-size: 11px; color: #666;")

        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle_label)
        header_layout.addWidget(title_widget)
        header_layout.addStretch()

        layout.addWidget(header_widget)

        # Connection controls
        connection_group = QtWidgets.QGroupBox("Connection")
        connection_layout = QtWidgets.QGridLayout(connection_group)
        connection_layout.setSpacing(8)
        connection_layout.setContentsMargins(10, 10, 10, 10)
        connection_layout.setColumnStretch(0, 0)  # Labels don't stretch
        connection_layout.setColumnStretch(1, 1)   # Inputs stretch
        connection_layout.setColumnStretch(2, 0)  # Buttons don't stretch

        self.port_combo = QtWidgets.QComboBox()
        self.port_combo.setMinimumWidth(240)
        self.refresh_ports_btn = QtWidgets.QPushButton("Refresh Ports")

        self.sensor_combo = QtWidgets.QComboBox()
        self.sensor_combo.addItem("Vibration", "vibration")
        self.sensor_combo.addItem("IMU", "imu")

        connection_layout.addWidget(QtWidgets.QLabel("Select Port"), 0, 0)
        connection_layout.addWidget(self.port_combo, 0, 1)
        connection_layout.addWidget(self.refresh_ports_btn, 0, 2)
        connection_layout.addWidget(QtWidgets.QLabel("Select Sensor"), 1, 0)
        connection_layout.addWidget(self.sensor_combo, 1, 1)

        self.connect_btn = QtWidgets.QPushButton("Connect and Detect")
        self.disconnect_btn = QtWidgets.QPushButton("Disconnect")
        self.disconnect_btn.setEnabled(False)
        connection_layout.addWidget(self.connect_btn, 2, 0, 1, 2)
        connection_layout.addWidget(self.disconnect_btn, 2, 2)

        layout.addWidget(connection_group)

        # Sensor info
        sensor_group = QtWidgets.QGroupBox("Sensor")
        sensor_layout = QtWidgets.QGridLayout(sensor_group)
        sensor_layout.setSpacing(8)
        sensor_layout.setContentsMargins(10, 10, 10, 10)
        sensor_layout.setColumnStretch(0, 0)  # Labels don't stretch
        sensor_layout.setColumnStretch(1, 1)   # Inputs stretch

        self.sensor_label = QtWidgets.QLineEdit()
        self.sensor_label.setReadOnly(True)

        self.product_field = QtWidgets.QLineEdit()
        self.product_field.setReadOnly(True)
        self.serial_field = QtWidgets.QLineEdit()
        self.serial_field.setReadOnly(True)

        sensor_layout.addWidget(QtWidgets.QLabel("Detected sensor"), 0, 0)
        sensor_layout.addWidget(self.sensor_label, 0, 1)
        sensor_layout.addWidget(QtWidgets.QLabel("Product ID"), 1, 0)
        sensor_layout.addWidget(self.product_field, 1, 1)
        sensor_layout.addWidget(QtWidgets.QLabel("Serial Number"), 2, 0)
        sensor_layout.addWidget(self.serial_field, 2, 1)

        layout.addWidget(sensor_group)

        # Actions
        actions_group = QtWidgets.QGroupBox("Actions")
        actions_layout = QtWidgets.QHBoxLayout(actions_group)
        self.configure_btn = QtWidgets.QPushButton("Start Configuration")
        self.exit_auto_btn = QtWidgets.QPushButton("Exit Auto Mode")
        self.reset_btn = QtWidgets.QPushButton("Factory Reset")
        for button in (self.configure_btn, self.exit_auto_btn, self.reset_btn):
            button.setEnabled(False)
            actions_layout.addWidget(button)

        layout.addWidget(actions_group)

        # Logs
        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(500)
        self.log_view.setMaximumHeight(200)
        layout.addWidget(QtWidgets.QLabel("Output Logs"))
        layout.addWidget(self.log_view)

        container.setLayout(layout)
        self.setCentralWidget(container)

    def _wire_signals(self) -> None:
        self.connect_btn.clicked.connect(self._handle_connect_clicked)
        self.disconnect_btn.clicked.connect(self.runtime.disconnect_port)
        self.refresh_ports_btn.clicked.connect(self.runtime.publish_ports)
        self.configure_btn.clicked.connect(lambda: self._run_command("configure"))
        self.exit_auto_btn.clicked.connect(lambda: self._run_command("exit_auto"))
        self.reset_btn.clicked.connect(lambda: self._run_command("full_reset"))

        self.runtime.stateChanged.connect(self._on_state_changed)
        self.runtime.detectionFinished.connect(self._on_detection_finished)
        self.runtime.commandFinished.connect(self._on_command_finished)
        self.runtime.operationFailed.connect(self._on_operation_failed)
        self.runtime.logMessage.connect(self._append_log)
        self.runtime.portsUpdated.connect(self._update_ports)
        self.runtime.autoModeDetected.connect(self._on_auto_mode_detected)

    # Slots -------------------------------------------------------------------
    def _handle_connect_clicked(self) -> None:
        port = self.port_combo.currentData()
        if port is None:
            port = self.port_combo.currentText()
        if not port:
            QtWidgets.QMessageBox.warning(self, "Missing port", "Please select a serial port.")
            return
        # Use default baud rate of 460800
        baud = 460800
        self._detect_after_connect = True
        self.runtime.connect_port(port, baud)

    def _run_command(self, command: str) -> None:
        sensor = self._selected_sensor_type()
        if command == "configure":
            self.runtime.configure(sensor)
        elif command == "exit_auto":
            self.runtime.exit_auto(sensor)
        elif command == "full_reset":
            self.runtime.full_reset(sensor)

    def _selected_sensor_type(self) -> SensorType:
        sensor = self.sensor_combo.currentData()
        if sensor in ("vibration", "imu"):
            return sensor
        # default to vibration for legacy behavior
        return "vibration"

    def _on_state_changed(self, connected: bool, port: str, baud: int) -> None:
        self.connect_btn.setEnabled(not connected)
        self.disconnect_btn.setEnabled(connected)
        for button in (self.configure_btn, self.exit_auto_btn, self.reset_btn):
            button.setEnabled(connected)
        status = "Connected" if connected else "Disconnected"
        self._append_log(f"{status} to {port or 'n/a'} @ {baud} bps")
        if connected and self._detect_after_connect:
            self._detect_after_connect = False
            sensor_choice = self.sensor_combo.currentData()
            sensor = sensor_choice if sensor_choice in ("vibration", "imu") else "vibration"
            self._pending_sensor_type = sensor
            # Check auto mode before detecting
            self.runtime.check_auto_mode(sensor)

    def _on_auto_mode_detected(self, is_auto_mode: bool) -> None:
        """Handle auto mode detection result."""
        if is_auto_mode and self._pending_sensor_type:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Sensor in Auto Mode",
                "The sensor is already in auto mode. Would you like to exit auto mode before detecting?",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.Yes,
            )
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self._append_log("Exiting auto mode before detection...")
                # Exit auto mode, then detect after command finishes
                self._exit_auto_then_detect = True
                self.runtime.exit_auto(self._pending_sensor_type)
            else:
                # Proceed with detection anyway
                self._append_log("Proceeding with detection while sensor is in auto mode...")
                self.runtime.detect(self._pending_sensor_type)
                self._pending_sensor_type = None
        elif self._pending_sensor_type:
            # Not in auto mode, proceed with detection
            self.runtime.detect(self._pending_sensor_type)
            self._pending_sensor_type = None

    def _on_detection_finished(self, identity: DeviceIdentity) -> None:
        sensor = identity.sensor_type or self.sensor_combo.currentData() or "vibration"
        self.sensor_label.setText(sensor.title() if isinstance(sensor, str) else "")
        self.product_field.setText(identity.product_id or identity.product_id_raw or "Unknown")
        self.serial_field.setText(identity.serial_number or "Unknown")
        self._append_log("Sensor identity retrieved successfully.")

    def _on_command_finished(self, command: str, result: object) -> None:
        if hasattr(result, "message"):
            message = getattr(result, "message")
        else:
            message = f"{command} completed"
        self._append_log(str(message))
        
        # If we exited auto mode and need to detect, do it now
        if command == "exit_auto" and self._exit_auto_then_detect and self._pending_sensor_type:
            self._exit_auto_then_detect = False
            self._append_log("Auto mode exited. Proceeding with detection...")
            self.runtime.detect(self._pending_sensor_type)
            self._pending_sensor_type = None

    def _on_operation_failed(self, command: str, message: str) -> None:
        QtWidgets.QMessageBox.critical(self, "Operation failed", f"{command} failed:\n{message}")
        self._append_log(f"{command} failed: {message}")
        
        # If exit_auto failed but we were trying to detect, clear the flag
        if command == "exit_auto" and self._exit_auto_then_detect:
            self._exit_auto_then_detect = False
            self._pending_sensor_type = None

    def _append_log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    def _update_ports(self, ports: list) -> None:
        previous = self.port_combo.currentText()
        self.port_combo.blockSignals(True)
        self.port_combo.clear()
        for port in ports:
            label = f"{port['device']} — {port['description']}"
            self.port_combo.addItem(label, port["device"])
        self.port_combo.blockSignals(False)
        if previous:
            idx = self.port_combo.findText(previous)
            if idx >= 0:
                self.port_combo.setCurrentIndex(idx)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # type: ignore[override]
        self.runtime.shutdown()
        super().closeEvent(event)


