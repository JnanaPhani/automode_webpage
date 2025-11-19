from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from helper_app.controller import SensorType

from desktop_app.runtime import DeviceIdentity, HelperRuntime

LOG = logging.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    """Primary window for the desktop helper."""

    def __init__(self, runtime: HelperRuntime) -> None:
        super().__init__()
        self.runtime = runtime
        self._pending_sensor_type: Optional[SensorType] = None
        self._exit_auto_then_detect = False
        self._detection_in_progress = False
        self._auto_disconnecting = False  # Flag to track auto-disconnect operations
        self.setWindowTitle("Zenith Tek Sensor Configuration Tool")
        self.setFixedSize(900, 650)  # Fixed size - prevents resizing
        self._build_ui()
        self._wire_signals()
        self.runtime.publish_ports()
        # Remove maximize button while explicitly keeping close and minimize buttons
        flags = QtCore.Qt.WindowType.Window | QtCore.Qt.WindowType.WindowCloseButtonHint | QtCore.Qt.WindowType.WindowMinimizeButtonHint
        self.setWindowFlags(flags)

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
            Path(sys.executable).parent / "_internal" / "public" / "zenithtek-logo.png",  # Packaged (in _internal)
            Path(sys.executable).parent / "public" / "zenithtek-logo.png",  # Packaged (if in same dir)
            Path(sys.executable).parent.parent / "public" / "zenithtek-logo.png",  # Packaged (alternative)
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

        self.connect_btn = QtWidgets.QPushButton("Connect")
        self.detect_btn = QtWidgets.QPushButton("Detect")
        self.disconnect_btn = QtWidgets.QPushButton("Disconnect")
        self.detect_btn.setEnabled(False)  # Disabled until connected
        self.disconnect_btn.setEnabled(False)  # Disabled until connected
        
        connection_layout.addWidget(self.connect_btn, 2, 0)
        connection_layout.addWidget(self.detect_btn, 2, 1)
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

        # IMU Configuration (only shown for IMU sensors)
        self.imu_config_group = QtWidgets.QGroupBox("IMU Configuration")
        imu_config_layout = QtWidgets.QGridLayout(self.imu_config_group)
        imu_config_layout.setSpacing(8)
        imu_config_layout.setContentsMargins(10, 10, 10, 10)
        imu_config_layout.setColumnStretch(0, 0)
        imu_config_layout.setColumnStretch(1, 1)

        # Sampling rate combo box
        self.sampling_rate_combo = QtWidgets.QComboBox()
        # Add supported sampling rates
        supported_rates = [2000, 1000, 500, 400, 250, 200, 125, 100, 80, 62.5, 50, 40, 31.25, 25, 20, 15.625]
        default_rate = 125
        for rate in supported_rates:
            if rate == default_rate:
                # Add "(default)" label for the default rate
                self.sampling_rate_combo.addItem(f"{rate} SPS (default)", rate)
            elif isinstance(rate, int):
                self.sampling_rate_combo.addItem(f"{rate} SPS", rate)
            else:
                self.sampling_rate_combo.addItem(f"{rate:.3f} SPS", rate)
        # Set default to 125 SPS
        default_idx = supported_rates.index(default_rate)
        self.sampling_rate_combo.setCurrentIndex(default_idx)

        imu_config_layout.addWidget(QtWidgets.QLabel("Sampling Rate"), 0, 0)
        imu_config_layout.addWidget(self.sampling_rate_combo, 0, 1)

        # Initially hide IMU config (only show for IMU)
        self.imu_config_group.setVisible(False)
        layout.addWidget(self.imu_config_group)

        # Vibration Sensor Info (only shown for vibration sensors)
        self.vibration_info_group = QtWidgets.QGroupBox("Vibration Sensor Information")
        vibration_info_layout = QtWidgets.QVBoxLayout(self.vibration_info_group)
        vibration_info_layout.setSpacing(8)
        vibration_info_layout.setContentsMargins(10, 10, 10, 10)

        info_label = QtWidgets.QLabel(
            "⚠️ <b>IMPORTANT:</b> RAW data sampling rates are <b>FIXED</b> and cannot be changed.\n\n"
            "• Velocity RAW: <b>3000 Sps</b> (FIXED)\n"
            "• Displacement RAW: <b>300 Sps</b> (FIXED)\n\n"
            # "Only RMS/P-P (Root Mean Square / Peak-to-Peak) rates can be configured."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; padding: 5px;")
        vibration_info_layout.addWidget(info_label)

        # Initially hide vibration info (only show for vibration)
        self.vibration_info_group.setVisible(False)
        layout.addWidget(self.vibration_info_group)

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
        self.detect_btn.clicked.connect(self._handle_detect_clicked)
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
        self.sensor_combo.currentIndexChanged.connect(self._on_sensor_type_changed)

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
        self.runtime.connect_port(port, baud)

    def _handle_detect_clicked(self) -> None:
        """Handle detect button click."""
        try:
            if not self.disconnect_btn.isEnabled():
                QtWidgets.QMessageBox.warning(self, "Not Connected", "Please connect to a port first.")
                return
            # Prevent multiple simultaneous detection attempts
            if self._detection_in_progress:
                QtWidgets.QMessageBox.warning(self, "Detection in Progress", "A detection is already in progress. Please wait for it to complete.")
                return
            # Disable detect button during detection
            self.detect_btn.setEnabled(False)
            self._detection_in_progress = True
            sensor_choice = self.sensor_combo.currentData()
            sensor = sensor_choice if sensor_choice in ("vibration", "imu") else "vibration"
            self._pending_sensor_type = sensor
            # Check auto mode before detecting
            self.runtime.check_auto_mode(sensor)
        except Exception as exc:
            LOG.error("Error in _handle_detect_clicked: %s", exc, exc_info=True)
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to start detection:\n{exc}")
            self._append_log(f"Error starting detection: {exc}")
            # Re-enable detect button on error
            if self.disconnect_btn.isEnabled():
                self.detect_btn.setEnabled(True)
            self._pending_sensor_type = None
            self._detection_in_progress = False

    def _set_action_buttons_enabled(self, enabled: bool) -> None:
        """Enable or disable all action buttons."""
        for button in (self.configure_btn, self.exit_auto_btn, self.reset_btn):
            button.setEnabled(enabled)

    def _run_command(self, command: str) -> None:
        # Disable all action buttons and detect button while operation is in progress
        self._set_action_buttons_enabled(False)
        self.detect_btn.setEnabled(False)
        
        sensor = self._selected_sensor_type()
        if command == "configure":
            # For IMU, pass sampling rate (TAP = 128 is now standard and handled by backend)
            if sensor == "imu":
                sampling_rate = self.sampling_rate_combo.currentData()
                # TAP value is always 128 (standard), so pass None to use default
                self.runtime.configure(sensor, sampling_rate=sampling_rate, tap_value=None)
            else:
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

    def _perform_auto_disconnect(self) -> None:
        """Perform the auto-disconnect operation (called via QTimer)."""
        try:
            self.runtime.disconnect_port()
        except Exception as exc:
            LOG.error("Auto-disconnect failed: %s", exc)
            self._append_log(f"Auto-disconnect failed: {exc}")
            self._auto_disconnecting = False

    def _on_state_changed(self, connected: bool, port: str, baud: int) -> None:
        # Connect button: disabled when connected
        self.connect_btn.setEnabled(not connected)
        # Detect button: enabled when connected (unless action is in progress)
        self.detect_btn.setEnabled(connected)
        # Disconnect button: enabled when connected
        self.disconnect_btn.setEnabled(connected)
        # Only enable action buttons if connected (and not during an operation)
        self._set_action_buttons_enabled(connected)
        status = "Connected" if connected else "Disconnected"
        self._append_log(f"{status} to {port or 'n/a'} @ {baud} bps")
        
        # Show completion dialog (skip if this is an auto-disconnect to avoid duplicate dialogs)
        if connected:
            QtWidgets.QMessageBox.information(
                self,
                "Connection Established",
                f"Successfully connected to {port or 'sensor'} @ {baud} bps.\n\n"
                f"You can now detect and configure the sensor."
            )
        else:
            # Only show disconnect dialog if it's not an auto-disconnect
            if not self._auto_disconnecting:
                QtWidgets.QMessageBox.information(
                    self,
                    "Disconnected",
                    "Disconnected from sensor successfully."
                )
            else:
                # Reset the flag after auto-disconnect completes
                self._auto_disconnecting = False

    def _on_auto_mode_detected(self, is_auto_mode: bool) -> None:
        """Handle auto mode detection result."""
        try:
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
                    # Disable buttons during operation
                    self._set_action_buttons_enabled(False)
                    self.detect_btn.setEnabled(False)
                    try:
                        self.runtime.exit_auto(self._pending_sensor_type)
                    except Exception as exc:
                        LOG.error("Failed to start exit_auto: %s", exc)
                        QtWidgets.QMessageBox.critical(self, "Error", f"Failed to exit auto mode:\n{exc}")
                        self._append_log(f"Failed to exit auto mode: {exc}")
                        # Re-enable buttons on error
                        if self.disconnect_btn.isEnabled():
                            self._set_action_buttons_enabled(True)
                            self.detect_btn.setEnabled(True)
                        self._exit_auto_then_detect = False
                        self._pending_sensor_type = None
                else:
                    # User chose not to exit auto mode - cancel detection
                    QtWidgets.QMessageBox.information(
                        self,
                        "Detection Cancelled",
                        "Detection cancelled. Please exit auto mode first to get accurate sensor information.",
                    )
                    self._append_log("Detection cancelled. Please exit auto mode first to get accurate sensor information.")
                    self._pending_sensor_type = None
                    self._detection_in_progress = False
                    # Re-enable detect button if still connected
                    if self.disconnect_btn.isEnabled():
                        self.detect_btn.setEnabled(True)
            elif self._pending_sensor_type:
                # Not in auto mode, proceed with detection
                self.runtime.detect(self._pending_sensor_type)
                self._pending_sensor_type = None
                # Keep _detection_in_progress = True until detection finishes
        except Exception as exc:
            LOG.error("Error in _on_auto_mode_detected: %s", exc, exc_info=True)
            QtWidgets.QMessageBox.critical(self, "Error", f"Error during auto mode detection:\n{exc}")
            self._append_log(f"Error during auto mode detection: {exc}")
            # Re-enable detect button on error
            if self.disconnect_btn.isEnabled():
                self.detect_btn.setEnabled(True)
            self._pending_sensor_type = None
            self._exit_auto_then_detect = False
            self._detection_in_progress = False

    def _on_detection_finished(self, identity: DeviceIdentity) -> None:
        try:
            sensor = identity.sensor_type or self.sensor_combo.currentData() or "vibration"
            self.sensor_label.setText(sensor.title() if isinstance(sensor, str) else "")
            self.product_field.setText(identity.product_id or identity.product_id_raw or "Unknown")
            self.serial_field.setText(identity.serial_number or "Unknown")
            self._append_log("Sensor identity retrieved successfully.")
            
            # Show completion dialog
            sensor_name = identity.product_id or identity.product_id_raw or "Sensor"
            QtWidgets.QMessageBox.information(
                self,
                "Detection Complete",
                f"Sensor detected successfully.\n\n"
                f"Product ID: {sensor_name}\n"
                f"Serial Number: {identity.serial_number or 'Unknown'}\n\n"
                f"You can now configure the sensor settings."
            )
            
            # Re-enable detect button if still connected
            if self.disconnect_btn.isEnabled():
                self.detect_btn.setEnabled(True)
            self._detection_in_progress = False
        except Exception as exc:
            LOG.error("Error in _on_detection_finished: %s", exc, exc_info=True)
            QtWidgets.QMessageBox.critical(self, "Error", f"Error processing detection result:\n{exc}")
            self._append_log(f"Error processing detection result: {exc}")
            # Re-enable detect button on error
            if self.disconnect_btn.isEnabled():
                self.detect_btn.setEnabled(True)
            self._detection_in_progress = False

    def _on_command_finished(self, command: str, result: object) -> None:
        if hasattr(result, "message"):
            message = getattr(result, "message")
        else:
            message = f"{command} completed"
        self._append_log(str(message))
        
        # Show completion dialog with next steps
        requires_restart = getattr(result, "requires_restart", False)
        sensor = self._selected_sensor_type()
        
        if command == "configure":
            if requires_restart:
                QtWidgets.QMessageBox.information(
                    self,
                    "Configuration Complete",
                    "Sensor is set to auto mode.\n\n"
                    "Please restart the sensor (power cycle or reset) to start receiving data."
                )
                # Automatically disconnect after setting sensor to auto mode
                # Use QTimer to defer disconnect slightly to avoid blocking after modal dialog
                if self.disconnect_btn.isEnabled():
                    self._append_log("Auto-disconnecting from COM port after auto mode configuration...")
                    self._auto_disconnecting = True
                    QtCore.QTimer.singleShot(100, self._perform_auto_disconnect)
            else:
                QtWidgets.QMessageBox.information(
                    self,
                    "Configuration Complete",
                    "Sensor configuration completed successfully."
                )
        elif command == "exit_auto":
            QtWidgets.QMessageBox.information(
                self,
                "Auto Mode Disabled",
                "Auto mode has been disabled successfully.\n\n"
                "The sensor is now in configuration mode."
            )
        elif command == "full_reset":
            QtWidgets.QMessageBox.information(
                self,
                "Factory Reset Complete",
                "Factory reset completed successfully.\n\n"
                "Please restart the sensor (power cycle or reset) to apply the changes."
            )
        
        # Re-enable action buttons and detect button if still connected
        if self.disconnect_btn.isEnabled():
            self._set_action_buttons_enabled(True)
            self.detect_btn.setEnabled(True)
        
        # If we exited auto mode and need to detect, do it now
        if command == "exit_auto" and self._exit_auto_then_detect and self._pending_sensor_type:
            self._exit_auto_then_detect = False
            sensor_type = self._pending_sensor_type
            self._pending_sensor_type = None
            self._append_log("Auto mode exited. Proceeding with detection...")
            self.detect_btn.setEnabled(False)  # Disable during detection
            try:
                if self.disconnect_btn.isEnabled():  # Make sure we're still connected
                    self.runtime.detect(sensor_type)
                else:
                    self._append_log("Connection lost. Detection cancelled.")
                    if self.disconnect_btn.isEnabled():
                        self.detect_btn.setEnabled(True)
            except Exception as exc:
                LOG.error("Failed to start detection after exit_auto: %s", exc)
                QtWidgets.QMessageBox.critical(self, "Error", f"Failed to start detection:\n{exc}")
                self._append_log(f"Failed to start detection: {exc}")
                # Re-enable detect button on error
                if self.disconnect_btn.isEnabled():
                    self.detect_btn.setEnabled(True)

    def _on_operation_failed(self, command: str, message: str) -> None:
        # For disconnect timeouts, don't show error dialog - state is already updated
        if command == "disconnect" and "timed out" in message.lower():
            self._append_log(f"Disconnect timed out, but connection state has been updated.")
            # Reset auto-disconnect flag if it was set
            if self._auto_disconnecting:
                self._auto_disconnecting = False
            return
        
        # For other operations, show error dialog
        QtWidgets.QMessageBox.critical(self, "Operation failed", f"{command} failed:\n{message}")
        self._append_log(f"{command} failed: {message}")
        
        # Re-enable action buttons and detect button if still connected
        if self.disconnect_btn.isEnabled():
            self._set_action_buttons_enabled(True)
            self.detect_btn.setEnabled(True)
        
        # If detection failed, clear the detection in progress flag
        if command == "detect":
            self._detection_in_progress = False
        
        # If exit_auto failed but we were trying to detect, clear the flag
        if command == "exit_auto" and self._exit_auto_then_detect:
            self._exit_auto_then_detect = False
            self._pending_sensor_type = None
            self._detection_in_progress = False

    def _append_log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    def _on_sensor_type_changed(self, index: int) -> None:
        """Show/hide sensor-specific configuration based on selected sensor type."""
        sensor = self.sensor_combo.currentData()
        self.imu_config_group.setVisible(sensor == "imu")
        self.vibration_info_group.setVisible(sensor == "vibration")

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


