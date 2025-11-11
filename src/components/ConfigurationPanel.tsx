import { useEffect, useMemo, useState } from 'react';
import { Play, Plug, Loader2, CheckCircle, XCircle, Power } from 'lucide-react';
import {
  webSerialService,
  SENSOR_PROFILES,
  SensorType,
  IMU_SAMPLING_OPTIONS,
} from '../services/webSerial';
import { LogEntry } from '../types';
import { LogViewer } from './LogViewer';

const DEFAULT_IMU_SAMPLING_ID =
  IMU_SAMPLING_OPTIONS.find((option) => option.rate === 125)?.id || IMU_SAMPLING_OPTIONS[0].id;

export function ConfigurationPanel() {
  const webSerialSupported = webSerialService.isSupported();
  const [port, setPort] = useState<SerialPort | null>(null);
  const [portLabel, setPortLabel] = useState<string>('No device selected');
  const [sensorType, setSensorType] = useState<SensorType>('vibration');
  const [baudRate, setBaudRate] = useState<number>(SENSOR_PROFILES.vibration.defaultBaudRate);
  const [imuSamplingId, setImuSamplingId] = useState<string>(DEFAULT_IMU_SAMPLING_ID);
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState<string>('');
  const [uiNotice, setUiNotice] = useState<string>('');

  const selectedProfile = useMemo(() => SENSOR_PROFILES[sensorType], [sensorType]);
  const baudRateOptions = selectedProfile.baudRates;
  const imuSampling = useMemo(
    () => IMU_SAMPLING_OPTIONS.find((option) => option.id === imuSamplingId) ?? IMU_SAMPLING_OPTIONS[0],
    [imuSamplingId],
  );
  const requiresHighBaud = sensorType === 'imu' && imuSampling.rate > 500;
  const HIGH_RATE_NOTICE = 'Sampling rates above 500 sps require 921600 baud.';

  useEffect(() => {
    if (!webSerialSupported) {
      return;
    }

    let active = true;

    (async () => {
      try {
        const savedPorts = await webSerialService.getSavedPorts();
        if (active && savedPorts.length > 0) {
          const defaultPort = savedPorts[0];
          setPort(defaultPort);
          setPortLabel(webSerialService.describePort(defaultPort));
        }
      } catch (error) {
        console.warn('Unable to load saved ports', error);
      }
    })();

    return () => {
      active = false;
    };
  }, [webSerialSupported]);

  useEffect(() => {
    setBaudRate(selectedProfile.defaultBaudRate);
    if (sensorType === 'imu') {
      if (!IMU_SAMPLING_OPTIONS.some((option) => option.id === imuSamplingId)) {
        setImuSamplingId(DEFAULT_IMU_SAMPLING_ID);
      }
    }
    if (sensorType === 'vibration') {
      setUiNotice('');
    }
  }, [selectedProfile, sensorType, imuSamplingId]);

  useEffect(() => {
    if (sensorType === 'imu') {
      setImuSamplingId(DEFAULT_IMU_SAMPLING_ID);
    }
  }, [sensorType]);

  useEffect(() => {
    if (sensorType !== 'imu') {
      setUiNotice('');
      return;
    }
    const sampling = IMU_SAMPLING_OPTIONS.find((option) => option.id === imuSamplingId) ?? IMU_SAMPLING_OPTIONS[0];
    if (sampling.rate > 500) {
      if (baudRate < 921600) {
        setBaudRate(921600);
        setUiNotice(`${HIGH_RATE_NOTICE} Baud adjusted automatically.`);
      } else {
        setUiNotice(HIGH_RATE_NOTICE);
      }
    } else {
      setUiNotice('');
    }
  }, [sensorType, imuSamplingId, baudRate, requiresHighBaud]);

  const appendLog = (entry: LogEntry) => {
    setLogs((prev) => [...prev, entry]);
  };

  const handleRequestPort = async () => {
    setLoading(true);
    setLogs([]);
    setStatus('idle');
    setMessage('');

    try {
      const selectedPort = await webSerialService.requestPort();
      setPort(selectedPort);
      const label = webSerialService.describePort(selectedPort);
      setPortLabel(label);
      appendLog({
        type: 'stdout',
        message: `Sensor type: ${selectedProfile.label} (${selectedProfile.model})`,
        timestamp: new Date().toISOString(),
      });
      appendLog({
        type: 'stdout',
        message: `Selected device: ${label}`,
        timestamp: new Date().toISOString(),
      });
      if (sensorType === 'imu') {
        appendLog({
          type: 'stdout',
          message: `Sampling rate: ${imuSampling.label}`,
          timestamp: new Date().toISOString(),
        });
        if (requiresHighBaud) {
          appendLog({
            type: 'stdout',
            message: `${HIGH_RATE_NOTICE} Baud set to 921600 for reliability.`,
            timestamp: new Date().toISOString(),
          });
        }
      }
      setStatus('success');
      setMessage('Serial device selected. Ready to configure.');
    } catch (error) {
      setStatus('error');
      setMessage(
        error instanceof Error ? error.message : 'Serial port selection was cancelled or failed',
      );
    } finally {
      setLoading(false);
    }
  };

  const handleConfigure = async () => {
    if (!port) {
      setMessage('Please select a serial device first');
      setStatus('error');
      return;
    }

    setLoading(true);
    setLogs([]);
    setStatus('idle');
    setMessage('');

    try {
      appendLog({
        type: 'stdout',
        message: `Starting configuration for ${selectedProfile.label} (${selectedProfile.model}) at ${baudRate.toLocaleString()} bps`,
        timestamp: new Date().toISOString(),
      });
      if (sensorType === 'imu') {
        appendLog({
          type: 'stdout',
          message: `Setting sampling rate to ${imuSampling.label}`,
          timestamp: new Date().toISOString(),
        });
        if (requiresHighBaud && baudRate < 921600) {
          appendLog({
            type: 'stderr',
            message: `${HIGH_RATE_NOTICE} Selected ${baudRate.toLocaleString()} bps may overflow the host interface.`,
            timestamp: new Date().toISOString(),
          });
        }
      } else {
        appendLog({
          type: 'stdout',
          message: 'Sampling rate fixed: Velocity RAW 3000 sps, Displacement RAW 300 sps.',
          timestamp: new Date().toISOString(),
        });
      }
      const result = await webSerialService.configureSensor({
        port,
        baudRate,
        sensor: sensorType,
        imuSamplingId: sensorType === 'imu' ? imuSamplingId : undefined,
        onLog: appendLog,
      });
      setStatus(result.success ? 'success' : 'error');
      setMessage(result.message);
    } catch (error) {
      setStatus('error');
      setMessage(error instanceof Error ? error.message : 'Configuration failed');
    } finally {
      setLoading(false);
    }
  };

  const handleExitAutoMode = async () => {
    if (!port) {
      setStatus('error');
      setMessage('Please select a serial device first');
      return;
    }
    if (!window.confirm('Disable Auto Mode and return the sensor to configuration state?')) {
      return;
    }

    setLoading(true);
    setLogs([]);
    setStatus('idle');
    setMessage('');

    try {
      const result = await webSerialService.exitAutoMode({
        port,
        sensor: sensorType,
        baudRate,
        onLog: appendLog,
      });
      setStatus(result.success ? 'success' : 'error');
      setMessage(result.message);
    } catch (error) {
      setStatus('error');
      setMessage(error instanceof Error ? error.message : 'Failed to disable auto mode');
    } finally {
      setLoading(false);
    }
  };

  const handleFactoryReset = async () => {
    if (!port) {
      setStatus('error');
      setMessage('Please select a serial device first');
      return;
    }
    if (
      !window.confirm(
        'Factory reset will reboot the sensor and restore defaults. Continue?',
      )
    ) {
      return;
    }

    setLoading(true);
    setLogs([]);
    setStatus('idle');
    setMessage('');

    try {
      const result = await webSerialService.factoryReset({
        port,
        sensor: sensorType,
        onLog: appendLog,
      });
      setStatus(result.success ? 'success' : 'error');
      setMessage(result.message);
    } catch (error) {
      setStatus('error');
      setMessage(error instanceof Error ? error.message : 'Factory reset failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Sensor Configuration</h2>

      {!webSerialSupported && (
        <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          Your browser does not support the Web Serial API. Please use the latest Chrome,
          Microsoft Edge, or another Chromium-based browser on desktop.
        </div>
      )}

      <div className="space-y-4">
        <div>
          <button
            onClick={handleRequestPort}
            disabled={loading || !webSerialSupported}
            className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-[#085f63] text-white rounded-md hover:bg-[#0a7a80] disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Plug className="h-5 w-5" />
            )}
            <span>Select Sensor</span>
          </button>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Selected Device</label>
          <div className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-800">
            {port ? portLabel : 'No device selected'}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Sensor Type</label>
          <select
            value={sensorType}
            onChange={(event) => setSensorType(event.target.value as SensorType)}
            disabled={!webSerialSupported}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#085f63] focus:border-[#085f63]"
          >
            {Object.entries(SENSOR_PROFILES).map(([key, profile]) => (
              <option key={key} value={key}>
                {profile.label} ({profile.model})
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-gray-600">{selectedProfile.summary}</p>
        </div>

        {sensorType === 'imu' ? (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Sampling Rate</label>
            <select
              value={imuSamplingId}
              onChange={(event) => setImuSamplingId(event.target.value)}
              disabled={!webSerialSupported}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#085f63] focus:border-[#085f63]"
            >
              {IMU_SAMPLING_OPTIONS.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-600">
              {imuSampling.note ||
                ' '}
            </p>
          </div>
        ) : (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Sampling Rate</label>
            <div className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-800">
              Velocity RAW fixed at 3000 sps · Displacement RAW fixed at 300 sps
            </div>
            <p className="mt-1 text-xs text-gray-600">
              Factory default rates per M-A542VR1 datasheet; no additional configuration needed.
            </p>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Baud Rate</label>
          <select
            value={baudRate}
            onChange={(e) => {
              const newBaud = Number(e.target.value);
              setBaudRate(newBaud);
              if (sensorType === 'imu') {
                if (imuSampling.rate > 500) {
                  if (newBaud < 921600) {
                    setUiNotice(
                      `${HIGH_RATE_NOTICE} Selected ${newBaud.toLocaleString()} bps may cause data loss.`,
                    );
                  } else {
                    setUiNotice(HIGH_RATE_NOTICE);
                  }
                } else {
                  setUiNotice('');
                }
              } else {
                setUiNotice('');
              }
            }}
            disabled={!webSerialSupported}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#085f63] focus:border-[#085f63]"
          >
            {baudRateOptions.map((rate) => (
              <option key={rate} value={rate}>
                {rate}
              </option>
            ))}
          </select>
          {uiNotice && (
            <p
              className={`mt-1 text-xs ${requiresHighBaud && baudRate < 921600 ? 'text-red-600' : 'text-[#085f63]'}`}
            >
              {uiNotice}
            </p>
          )}
        </div>

        <div>
          <button
            onClick={handleConfigure}
            disabled={loading || !port || !webSerialSupported}
            className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-[#085f63] text-white rounded-md hover:bg-[#0a7a80] disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Play className="h-5 w-5" />
            )}
            <span>Start Configuration</span>
          </button>
        </div>

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <button
            onClick={handleExitAutoMode}
            disabled={loading || !port || !webSerialSupported}
            className="flex items-center justify-center space-x-2 px-4 py-2 rounded-md border border-[#085f63] text-[#085f63] hover:bg-[#e0f5f4] disabled:border-gray-300 disabled:text-gray-400 transition-colors"
          >
            <Plug className="h-5 w-5" />
            <span>Exit Auto Mode</span>
          </button>
          <button
            onClick={handleFactoryReset}
            disabled={loading || !port || !webSerialSupported}
            className="flex items-center justify-center space-x-2 px-4 py-2 rounded-md border border-red-500 text-red-600 hover:bg-red-50 disabled:border-gray-300 disabled:text-gray-400 transition-colors"
          >
            <Power className="h-5 w-5" />
            <span>Factory Reset</span>
          </button>
        </div>

        {message && (
          <div
            className={`flex items-center space-x-2 p-3 rounded-md ${
              status === 'success'
                ? 'bg-[#e0f5f4] text-[#085f63] border border-[#0a7a80]/20'
                : status === 'error'
                ? 'bg-red-50 text-red-800 border border-red-200'
                : 'bg-blue-50 text-blue-800 border border-blue-200'
            }`}
          >
            {status === 'success' && <CheckCircle className="h-5 w-5" />}
            {status === 'error' && <XCircle className="h-5 w-5" />}
            <span className="text-sm font-medium">{message}</span>
          </div>
        )}
      </div>

      <LogViewer logs={logs} />
    </div>
  );
}
