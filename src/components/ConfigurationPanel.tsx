import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertTriangle, CheckCircle, Loader2, Play, Plug, Power, RefreshCw, XCircle, Copy, Check } from 'lucide-react';
import { HelperClient, HelperPortInfo, HelperStatus, HelperUpdateInfo } from '../services/helperClient';
import {
  SENSOR_PROFILES,
  SensorType,
  IMU_SAMPLING_OPTIONS,
  PRODUCT_ID_SENSOR_LOOKUP,
} from '../services/sensorProfiles';
import { LogEntry } from '../types';
import { LogViewer } from './LogViewer';

const navigatorInfo =
  typeof navigator !== 'undefined'
    ? (navigator as Navigator & { userAgentData?: { platform?: string } })
    : undefined;
const PLATFORM = navigatorInfo?.userAgentData?.platform ?? navigatorInfo?.platform ?? 'unknown';
const LOG_HISTORY_LIMIT = 400;
const DEFAULT_DOWNLOAD_URL =
  'https://dqxfwdaazfzyfrwzkmed.supabase.co/storage/v1/object/public/helper-installers/';

function formatBytes(length: number): string {
  if (!Number.isFinite(length) || length < 0) {
    return `${length}`;
  }
  if (length < 1024) {
    return `${length} B`;
  }
  const units = ['KB', 'MB', 'GB', 'TB'];
  let value = length;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  const decimals = value >= 100 ? 0 : value >= 10 ? 1 : 2;
  return `${value.toFixed(decimals)} ${units[unitIndex]}`;
}

function formatRelativeTime(date: Date | null): string {
  if (!date) {
    return 'never';
  }
  const diffMs = Date.now() - date.getTime();
  if (diffMs < 0) {
    return 'just now';
  }
  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 5) return 'just now';
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function describeHelperState(status: HelperStatus | null, lastSeen: Date | null): string {
  if (!status) {
    return lastSeen ? `Offline (last seen ${formatRelativeTime(lastSeen)})` : 'Offline';
  }
  if (status.connected && status.port) {
    return `Connected to ${status.port} @ ${status.baudRate.toLocaleString()} bps`;
  }
  return `Idle – ready for commands (last seen ${formatRelativeTime(lastSeen)})`;
}

export function ConfigurationPanel() {
  const [helperBaseUrl, setHelperBaseUrl] = useState(
    () => localStorage.getItem('helperBaseUrl') ?? 'http://127.0.0.1:7421',
  );
  const [helperToken, setHelperToken] = useState(() => localStorage.getItem('helperToken') ?? '');
  const [helperStatus, setHelperStatus] = useState<HelperStatus | null>(null);
  const [availablePorts, setAvailablePorts] = useState<HelperPortInfo[]>([]);
  const [selectedPort, setSelectedPort] = useState<string>('');
  const [updateInfo, setUpdateInfo] = useState<HelperUpdateInfo | null>(null);
  const [updateDownloadPath, setUpdateDownloadPath] = useState<string>('');
  const [updateNotice, setUpdateNotice] = useState<string>('');
  const [lastStatusAt, setLastStatusAt] = useState<Date | null>(null);
  const [pairingState, setPairingState] = useState<'idle' | 'pending' | 'error'>('idle');
  const [pairingError, setPairingError] = useState<string>('');
  const [tokenCopied, setTokenCopied] = useState(false);
  const [sensorType, setSensorType] = useState<SensorType>('vibration');
  const [detectedSensorType, setDetectedSensorType] = useState<SensorType | null>(null);
  const [sensorOverrideEnabled, setSensorOverrideEnabled] = useState<boolean>(false);
  const [baudRate, setBaudRate] = useState<number>(SENSOR_PROFILES.vibration.defaultBaudRate);
  const DEFAULT_IMU_OPTION =
    IMU_SAMPLING_OPTIONS.find((option) => option.isDefault) ?? IMU_SAMPLING_OPTIONS[0];
  const [imuSamplingId, setImuSamplingId] = useState<string>(DEFAULT_IMU_OPTION.id);
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState<string>('');
  const [commandWarning, setCommandWarning] = useState<string>('');
  const [uiNotice, setUiNotice] = useState<string>('');
  const [requiresRestart, setRequiresRestart] = useState<boolean>(false);
  const [detecting, setDetecting] = useState<boolean>(false);
  const [sessionActive, setSessionActive] = useState<boolean>(false);
  const [detectedInfo, setDetectedInfo] = useState<{ productId: string; serialNumber: string } | null>(null);

  const logSocketRef = useRef<WebSocket | null>(null);

  const resetDetectionState = useCallback(() => {
    setDetectedSensorType(null);
    setDetectedInfo(null);
    if (!sensorOverrideEnabled) {
      setSensorType('vibration');
    }
    setUiNotice('');
  }, [sensorOverrideEnabled]);

  const selectedProfile = useMemo(() => SENSOR_PROFILES[sensorType], [sensorType]);
  const baudRateOptions = selectedProfile.baudRates;
  const imuSampling = useMemo(
    () => IMU_SAMPLING_OPTIONS.find((option) => option.id === imuSamplingId) ?? IMU_SAMPLING_OPTIONS[0],
    [imuSamplingId],
  );
  const requiresHighBaud = sensorType === 'imu' && imuSampling.rate > 500;
  const HIGH_RATE_NOTICE = 'Sampling rates above 500 sps require 921600 baud.';

  const helperClient = useMemo(() => new HelperClient(helperToken || '', helperBaseUrl), [helperBaseUrl, helperToken]);
  const helperStatusDescription = useMemo(
    () => describeHelperState(helperStatus, lastStatusAt),
    [helperStatus, lastStatusAt],
  );
  const truncatedToken = useMemo(() => {
    if (!helperToken) {
      return '';
    }
    if (helperToken.length <= 12) {
      return helperToken;
    }
    return `${helperToken.slice(0, 6)}…${helperToken.slice(-4)}`;
  }, [helperToken]);

  const attemptPair = useCallback(
    async (force = false) => {
      if (!helperBaseUrl) {
        return;
      }
      if (helperToken && !force) {
        return;
      }
      if (!force && pairingState !== 'idle') {
        return;
      }
      setPairingState('pending');
      setPairingError('');
      try {
        const response = await HelperClient.pair(helperBaseUrl);
        if (!response?.token) {
          throw new Error('Helper did not provide a pairing token.');
        }
        setHelperToken(response.token);
        localStorage.setItem('helperToken', response.token);
        setPairingState('idle');
        setPairingError('');
      } catch (error) {
        setPairingState('error');
        setPairingError(error instanceof Error ? error.message : 'Failed to pair with helper.');
      }
    },
    [helperBaseUrl, helperToken, pairingState],
  );

  const appendLog = useCallback((entry: LogEntry) => {
    setLogs((prev) => [...prev.slice(-LOG_HISTORY_LIMIT + 1), entry]);
  }, []);

  const refreshStatus = useCallback(async () => {
    if (!helperToken) {
      setHelperStatus(null);
      setSessionActive(false);
      setUpdateInfo(null);
      setLastStatusAt(null);
      return;
    }

    try {
      const statusResponse = await helperClient.status(PLATFORM);
      setHelperStatus(statusResponse);
      setSessionActive(statusResponse.connected);
      setUpdateInfo(statusResponse.updateAvailable);
      setLastStatusAt(new Date());
      if (statusResponse.connected && statusResponse.port) {
        setSelectedPort(statusResponse.port);
      }
    } catch (error) {
      console.warn('Helper status check failed', error);
      setHelperStatus(null);
      setSessionActive(false);
      setLastStatusAt(null);
    }
  }, [helperClient, helperToken]);

  const refreshPorts = useCallback(
    async (silent = false): Promise<HelperPortInfo[]> => {
      if (!helperToken) {
        if (!silent) {
          setStatus('error');
          setMessage('Pair with the helper before refreshing ports.');
        }
        return [];
      }

      try {
        const response = await helperClient.listPorts();
        setAvailablePorts(response.ports);
        if (response.ports.length === 1) {
          setSelectedPort(response.ports[0].device);
        }
        if (!silent) {
          setStatus('success');
          setMessage(response.ports.length ? 'Ports refreshed.' : 'No serial ports detected.');
        }
        return response.ports;
      } catch (error) {
        if (!silent) {
          setStatus('error');
          setMessage(error instanceof Error ? error.message : 'Failed to list ports.');
        }
        return [];
      }
    },
    [helperClient, helperToken],
  );

  const ensurePortSelected = useCallback(async (): Promise<string> => {
    if (selectedPort) {
      return selectedPort;
    }
    const ports = await refreshPorts(true);
    if (ports.length > 0) {
      const device = ports[0].device;
      setSelectedPort(device);
      return device;
    }
    throw new Error('No serial device available. Connect the sensor and refresh ports.');
  }, [refreshPorts, selectedPort]);

  useEffect(() => {
    setBaudRate(selectedProfile.defaultBaudRate);
    if (sensorType === 'imu' && !IMU_SAMPLING_OPTIONS.some((option) => option.id === imuSamplingId)) {
      setImuSamplingId(DEFAULT_IMU_OPTION.id);
    }
  }, [selectedProfile, sensorType, imuSamplingId]);

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

  useEffect(() => {
    refreshStatus();
    const interval = window.setInterval(refreshStatus, 10_000);
    return () => {
      window.clearInterval(interval);
    };
  }, [refreshStatus]);

  useEffect(() => {
    setAvailablePorts([]);
    setSelectedPort('');
    resetDetectionState();
    if (helperToken) {
      refreshStatus();
      refreshPorts(true);
    } else {
      setHelperStatus(null);
      setSessionActive(false);
    }
  }, [helperBaseUrl, helperToken, refreshPorts, refreshStatus, resetDetectionState]);

  useEffect(() => {
    if (!helperToken) {
      void attemptPair(false);
    }
  }, [helperToken, attemptPair]);

  useEffect(() => {
    if (!helperToken) {
      return;
    }

    if (logSocketRef.current) {
      logSocketRef.current.close();
      logSocketRef.current = null;
    }

    try {
      const socket = helperClient.openLogStream((event) => {
        try {
          const data = JSON.parse(event.data);
          appendLog({
            type: data.level === 'error' || data.level === 'warning' ? 'stderr' : 'stdout',
            message: data.message ?? '',
            timestamp: data.timestamp ?? new Date().toISOString(),
          });
        } catch (error) {
          console.warn('Failed to parse helper log event', error);
        }
      });
      logSocketRef.current = socket;
    } catch (error) {
      console.warn('Unable to open helper log stream', error);
    }

    return () => {
      if (logSocketRef.current) {
        logSocketRef.current.close();
        logSocketRef.current = null;
      }
    };
  }, [appendLog, helperClient, helperToken]);

  useEffect(() => {
    setTokenCopied(false);
  }, [helperToken]);

  const handleBaseUrlChange = (value: string) => {
    setHelperBaseUrl(value);
    localStorage.setItem('helperBaseUrl', value);
    if (helperToken) {
      setHelperToken('');
      localStorage.removeItem('helperToken');
    }
    setPairingState('idle');
    setPairingError('');
  };

  const buildDetectionOrder = useCallback((): SensorType[] => {
    if (sensorOverrideEnabled) {
      return [sensorType, sensorType === 'imu' ? 'vibration' : 'imu'];
    }
    const ordered: SensorType[] = [];
    if (detectedSensorType) {
      ordered.push(detectedSensorType);
    }
    if (!ordered.includes(sensorType)) {
      ordered.push(sensorType);
    }
    if (ordered.length > 0) {
      const last = ordered[ordered.length - 1];
      ordered.push(last === 'imu' ? 'vibration' : 'imu');
    } else {
      ordered.push('imu', 'vibration');
    }
    return Array.from(new Set(ordered));
  }, [detectedSensorType, sensorOverrideEnabled, sensorType]);

  const detectAcrossCandidates = useCallback(
    async (candidates: SensorType[]) => {
      let lastError = 'Detection failed.';
      for (const candidate of candidates) {
        appendLog({
          type: 'stdout',
          message: `Attempting detection using ${SENSOR_PROFILES[candidate].label}`,
          timestamp: new Date().toISOString(),
        });
        try {
          const result = await helperClient.detect(candidate);
          if (result.success) {
            return { result, usedType: candidate };
          }
          lastError = result.message ?? lastError;
        } catch (error) {
          lastError = error instanceof Error ? error.message : 'Detection failed.';
        }
      }
      throw new Error(lastError);
    },
    [appendLog, helperClient],
  );

  const applyDetectionResult = useCallback(
    (usedType: SensorType, detection: any) => {
      const productId = (detection.product_id ?? '').trim();
      const productIdRaw = (detection.product_id_raw ?? '').trim();
      const canonicalProductId = productId.toUpperCase();
      const canonicalProductIdRaw = productIdRaw.toUpperCase();
      const resolvedType =
        PRODUCT_ID_SENSOR_LOOKUP[canonicalProductId] ??
        PRODUCT_ID_SENSOR_LOOKUP[canonicalProductIdRaw] ??
        usedType;

      setDetectedSensorType(resolvedType);
      if (!sensorOverrideEnabled) {
        setSensorType(resolvedType);
      }
      setDetectedInfo({
        productId: productId || productIdRaw || 'Unknown',
        serialNumber: detection.serial_number ?? 'Unknown',
      });
      setStatus('success');
      setMessage(detection.message ?? 'Sensor identity retrieved.');
    },
    [sensorOverrideEnabled],
  );

  const handleConnectAndDetect = async () => {
    if (!helperToken) {
      setStatus('error');
      setMessage('Pair with the helper first.');
      return;
    }

    setLoading(true);
    setDetecting(true);
    setLogs([]);
    setStatus('idle');
    setMessage('');
    setCommandWarning('');
    setRequiresRestart(false);
    setDetectedInfo(null);

    let lastError: string | null = null;

    try {
      const device = await ensurePortSelected();
      const baudCandidates = Array.from(
        new Set<number>([SENSOR_PROFILES[sensorType].defaultBaudRate, baudRate].filter(Boolean)),
      );

      let detectedSuccessfully = false;

      for (const candidateBaud of baudCandidates) {
        try {
          const connection = await helperClient.connect(device, candidateBaud);
          appendLog({
            type: 'stdout',
            message: `Connected to ${connection.port} @ ${connection.baudRate.toLocaleString()} bps`,
            timestamp: new Date().toISOString(),
          });
          if (baudRate !== candidateBaud) {
            setBaudRate(candidateBaud);
          }
          const { result, usedType } = await detectAcrossCandidates(buildDetectionOrder());
          applyDetectionResult(usedType, result);
          await refreshStatus();
          detectedSuccessfully = true;
          break;
        } catch (error) {
          lastError = error instanceof Error ? error.message : 'Failed to connect or detect sensor.';
          appendLog({
            type: 'stderr',
            message: `Detection attempt failed at ${candidateBaud.toLocaleString()} bps: ${lastError}`,
            timestamp: new Date().toISOString(),
          });
        }
      }

      if (!detectedSuccessfully) {
        throw new Error(lastError ?? 'Failed to connect or detect sensor.');
      }
    } catch (error) {
      setStatus('error');
      setMessage(error instanceof Error ? error.message : 'Failed to connect or detect sensor.');
      setSessionActive(false);
    } finally {
      setLoading(false);
      setDetecting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!sessionActive) {
      resetDetectionState();
      return;
    }

    setLoading(true);
    setStatus('idle');
    setMessage('');
    setCommandWarning('');

    try {
      await helperClient.disconnect();
      appendLog({
        type: 'stdout',
        message: 'Serial device disconnected.',
        timestamp: new Date().toISOString(),
      });
      setStatus('success');
      setMessage('Serial device disconnected.');
      resetDetectionState();
      await refreshStatus();
    } catch (error) {
      setStatus('error');
      setMessage(error instanceof Error ? error.message : 'Failed to disconnect helper.');
    } finally {
      setLoading(false);
    }
  };

  const withHelperCommand = async (task: () => Promise<void>) => {
    setLoading(true);
    setLogs([]);
    setStatus('idle');
    setMessage('');
    setCommandWarning('');
    setRequiresRestart(false);
    setDetectedInfo(null);
    try {
      await ensurePortSelected();
      await task();
      await refreshStatus();
    } catch (error) {
      setStatus('error');
      setMessage(error instanceof Error ? error.message : 'Operation failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyToken = async () => {
    if (!helperToken) {
      return;
    }
    try {
      await navigator.clipboard.writeText(helperToken);
      setTokenCopied(true);
      window.setTimeout(() => setTokenCopied(false), 2000);
    } catch (error) {
      console.warn('Failed to copy helper token', error);
      setStatus('error');
      setMessage('Unable to copy helper token automatically. Copy it manually.');
    }
  };

  useEffect(() => {
    setTokenCopied(false);
  }, [helperToken]);

  const handleConfigure = async () => {
    await withHelperCommand(async () => {
      appendLog({
        type: 'stdout',
        message: `Starting configuration for ${selectedProfile.label} (${selectedProfile.model})`,
        timestamp: new Date().toISOString(),
      });
      const result = await helperClient.configure(sensorType, sensorType === 'imu' ? { imuSamplingId } : {});
      setStatus(result.success ? 'success' : 'error');
      setMessage(result.message ?? '');
      setCommandWarning(result.warning ?? '');
      setRequiresRestart(result.requires_restart ?? false);
      if (!result.success) {
        setDetectedInfo(null);
      }
    });
  };

  const handleExitAutoMode = async () => {
    if (!window.confirm('Disable Auto Mode and return the sensor to configuration state?')) {
      return;
    }
    await withHelperCommand(async () => {
      const result = await helperClient.exitAuto(sensorType, true);
      setStatus(result.success ? 'success' : 'error');
      setMessage(result.message ?? '');
      setCommandWarning(result.warning ?? '');
    });
  };

  const handleFactoryReset = async () => {
    if (!window.confirm('Factory reset will reboot the sensor and restore defaults. Continue?')) {
      return;
    }
    await withHelperCommand(async () => {
      const result = await helperClient.fullReset(sensorType);
      setStatus(result.success ? 'success' : 'error');
      setMessage(result.message ?? '');
      setCommandWarning(result.warning ?? '');
      setRequiresRestart(result.requires_restart ?? false);
    });
  };

  const handleUpdateCheck = async () => {
    if (!helperToken) {
      setStatus('error');
      setMessage('Pair with the helper before checking for updates.');
      return;
    }
    setUpdateDownloadPath('');
    setUpdateNotice('');
    setCommandWarning('');
    try {
      const response = await helperClient.triggerUpdate(PLATFORM);
      setUpdateInfo(response.updateAvailable);
      setStatus('success');
      setMessage(
        response.updateAvailable ? `Update ${response.updateAvailable.version} available.` : 'No updates found.',
      );
    } catch (error) {
      setStatus('error');
      setMessage(error instanceof Error ? error.message : 'Failed to check for updates.');
    }
  };

  const handleUpdateDownload = async () => {
    if (!helperToken) {
      setStatus('error');
      setMessage('Pair with the helper before downloading updates.');
      return;
    }
    if (!updateInfo) {
      setStatus('error');
      setMessage('No update metadata available. Run "Check for helper updates" first.');
      return;
    }
    setLoading(true);
    setStatus('idle');
    setMessage('');
    setCommandWarning('');
    setUpdateNotice('');
    try {
      const download = await helperClient.downloadUpdate(PLATFORM);
      setStatus('success');
      setMessage(`Update ${download.version} downloaded (${formatBytes(download.bytes)}).`);
      setUpdateDownloadPath(download.path);
      if (download.checksumVerified === true) {
        setUpdateNotice('Checksum verified successfully.');
      } else if (download.checksumVerified === false) {
        setUpdateNotice('Checksum verification failed. Delete the downloaded file and retry.');
      } else {
        setUpdateNotice('Checksum not provided; verify the download manually before installing.');
      }
    } catch (error) {
      setStatus('error');
      setMessage(error instanceof Error ? error.message : 'Failed to download update.');
      setUpdateDownloadPath('');
      setUpdateNotice('');
    } finally {
      setLoading(false);
    }
  };

  const helperUnavailable = Boolean(helperToken) && !helperStatus && pairingState !== 'pending';
  const autoDetectedLabel = detectedSensorType ? SENSOR_PROFILES[detectedSensorType].label : null;
  const sensorStatusMessage = sensorOverrideEnabled
    ? detectedSensorType
      ? `Manual override active (auto-detected: ${autoDetectedLabel}).`
      : 'Manual override active. Choose the sensor type below.'
    : detectedSensorType
    ? 'Auto-detected from product identity.'
    : 'Use Connect & Detect Sensor to identify the device automatically.';

  const handleSensorTypeOverrideToggle = () => {
    setSensorOverrideEnabled((prev) => {
      const next = !prev;
      if (!next && detectedSensorType) {
        setSensorType(detectedSensorType);
      }
      return next;
    });
  };

  const handleSensorTypeManualChange = (nextType: SensorType) => {
    setSensorType(nextType);
    if (detectedSensorType !== nextType) {
      setDetectedInfo(null);
    }
  };

  const handleResetSamplingAndBaud = () => {
    if (sensorType === 'imu') {
      setImuSamplingId(DEFAULT_IMU_OPTION.id);
    }
    setBaudRate(SENSOR_PROFILES[sensorType].defaultBaudRate);
    setUiNotice('');
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Sensor Configuration</h2>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Helper Base URL</label>
          <input
            value={helperBaseUrl}
            onChange={(event) => handleBaseUrlChange(event.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#085f63] focus:border-[#085f63]"
          />
          <p className="mt-1 text-xs text-gray-600">
            Leave as <code className="font-mono">http://127.0.0.1:7421</code> unless the helper runs on a custom port.
          </p>
        </div>

        <div className="rounded-md border border-gray-200 bg-gray-50 p-4 text-sm text-gray-800">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-gray-500">Helper status</p>
              <p className="font-semibold text-gray-900">{helperStatusDescription}</p>
              <p className="text-xs text-gray-600">
                Helper version: <span className="font-mono">{helperStatus?.version ?? '—'}</span>
              </p>
            </div>
            <div className="text-xs text-gray-600 text-left sm:text-right">
              <p>
                Update status:{' '}
                <span className="font-medium text-gray-800">
                  {updateInfo ? `Update ${updateInfo.version} available` : 'No updates detected'}
                </span>
              </p>
              {updateInfo?.releaseNotes && (
                <p className="mt-1">Release notes: {updateInfo.releaseNotes}</p>
              )}
            </div>
          </div>
          <div className="mt-3 space-y-2 border-t border-gray-200 pt-3 text-xs text-gray-600">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span>
                Pairing state:{' '}
                <span className="font-medium text-gray-800">
                  {pairingState === 'pending'
                    ? 'Pairing in progress…'
                    : pairingState === 'error'
                    ? 'Pairing failed'
                    : helperToken
                    ? 'Paired'
                    : 'Waiting for helper'}
                </span>
              </span>
              {pairingState === 'error' && (
                <button
                  type="button"
                  onClick={() => attemptPair(true)}
                  className="rounded border border-[#085f63] px-2 py-1 text-[#085f63] hover:bg-[#e0f5f4]"
                >
                  Retry pairing
                </button>
              )}
            </div>
            {pairingState === 'pending' && (
              <div className="flex items-center text-[#4b5563]">
                <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> Attempting to pair with the helper…
              </div>
            )}
            {pairingState === 'error' && (
              <div className="flex items-start space-x-2 text-yellow-700">
                <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                <span>{pairingError || 'Failed to pair with helper. Ensure the helper app is running.'}</span>
              </div>
            )}
            {!helperToken && pairingState === 'idle' && (
              <div>Waiting for the helper service. Launch the helper application to complete pairing.</div>
            )}
            {helperToken && (
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="break-all">
                  Token: <span className="font-mono">{truncatedToken}</span>
                </div>
                <button
                  type="button"
                  onClick={handleCopyToken}
                  className="inline-flex items-center space-x-2 rounded border border-[#085f63] px-2 py-1 text-[#085f63] hover:bg-[#e0f5f4]"
                >
                  {tokenCopied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                  <span>{tokenCopied ? 'Copied' : 'Copy token'}</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {helperUnavailable && (
          <div className="rounded-md border border-yellow-300 bg-yellow-50 p-4 text-sm text-yellow-900">
            <p className="font-semibold">Helper not detected.</p>
            <p className="mt-1">
              Make sure the Zenith Helper application is installed and running on this computer. You can download the
              latest installer from{' '}
              <a href={DEFAULT_DOWNLOAD_URL} className="underline text-[#085f63]" target="_blank" rel="noreferrer">
                the helper releases page
              </a>
              .
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          <button
            onClick={handleConnectAndDetect}
            disabled={loading || !helperToken}
            className="flex items-center justify-center space-x-2 px-4 py-2 bg-[#085f63] text-white rounded-md hover:bg-[#0a7a80] disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {loading && detecting ? <Loader2 className="h-5 w-5 animate-spin" /> : <Plug className="h-5 w-5" />}
            <span>Connect &amp; Detect Sensor</span>
          </button>
          <button
            onClick={handleDisconnect}
            disabled={loading || !sessionActive}
            className="flex items-center justify-center space-x-2 px-4 py-2 rounded-md border border-red-300 text-red-600 hover:bg-red-50 disabled:border-gray-300 disabled:text-gray-400 transition-colors"
          >
            <Power className="h-5 w-5" />
            <span>Disconnect</span>
          </button>
          <button
            onClick={() => refreshPorts(false)}
            disabled={loading || !helperToken}
            className="flex items-center justify-center space-x-2 px-4 py-2 rounded-md border border-gray-300 text-gray-700 hover:bg-gray-100 disabled:text-gray-400 transition-colors"
          >
            <RefreshCw className="h-5 w-5" />
            <span>Refresh Ports</span>
          </button>
        </div>
        <p className="text-xs text-[#8b5e00] bg-[#fff7e6] border border-[#facc15] rounded px-3 py-2">
          <span className="font-semibold uppercase tracking-wide">Reminder:</span> Always click{' '}
          <span className="font-semibold">Disconnect</span> before unplugging or swapping sensors to avoid serial issues.
        </p>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Selected Device</label>
          <select
            value={selectedPort}
            onChange={(event) => setSelectedPort(event.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#085f63] focus:border-[#085f63] disabled:bg-gray-100 disabled:text-gray-500"
            disabled={availablePorts.length === 0}
          >
            <option value="">{availablePorts.length ? 'Select a device' : 'No serial devices detected'}</option>
            {availablePorts.map((portInfo) => (
              <option key={portInfo.device} value={portInfo.device}>
                {portInfo.device} {portInfo.description ? `– ${portInfo.description}` : ''}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-gray-600">
            {sessionActive && selectedPort ? `Connected to ${selectedPort}` : 'Click Refresh Ports after plugging in.'}
          </p>
        </div>

        {detectedInfo && (
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-md border border-gray-200 bg-gray-50 p-3">
              <p className="text-xs uppercase tracking-wide text-gray-500">Product ID</p>
              <p className="text-sm font-semibold text-gray-900 break-words">{detectedInfo.productId}</p>
            </div>
            <div className="rounded-md border border-gray-200 bg-gray-50 p-3">
              <p className="text-xs uppercase tracking-wide text-gray-500">Serial Number</p>
              <p className="text-sm font-semibold text-gray-900 break-words">{detectedInfo.serialNumber}</p>
            </div>
          </div>
        )}

        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-sm font-medium text-gray-700">Sensor</label>
            <button
              type="button"
              onClick={handleSensorTypeOverrideToggle}
              className="rounded border border-[#085f63] px-2 py-0.5 text-xs font-medium text-[#085f63] hover:bg-[#e0f5f4]"
            >
              {sensorOverrideEnabled ? 'Use auto detection' : 'Select manually'}
            </button>
          </div>
          <div className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-800">
            {detectedSensorType
              ? `${selectedProfile.label} (${selectedProfile.model})`
              : '— detect the sensor to populate this field —'}
          </div>
          <p className="mt-1 text-xs text-gray-600">
            {detectedSensorType ? sensorStatusMessage : 'Click Connect & Detect Sensor to identify the connected device.'}
          </p>
          {sensorOverrideEnabled && (
            <select
              value={sensorType}
              onChange={(event) => handleSensorTypeManualChange(event.target.value as SensorType)}
              className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#085f63] focus:border-[#085f63]"
            >
              {Object.entries(SENSOR_PROFILES).map(([key, profile]) => (
                <option key={key} value={key}>
                  {profile.label} ({profile.model})
                </option>
              ))}
            </select>
          )}
          <p className="mt-1 text-xs text-gray-600">{selectedProfile.summary}</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Sampling Rate</label>
          {detectedSensorType || sensorOverrideEnabled ? (
            sensorType === 'imu' ? (
              <select
                value={imuSamplingId}
                onChange={(event) => setImuSamplingId(event.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#085f63] focus:border-[#085f63]"
              >
                {IMU_SAMPLING_OPTIONS.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.label}
                    {option.isDefault ? ' (default)' : ''}
                  </option>
                ))}
              </select>
            ) : (
              <div className="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-sm">
                Velocity RAW fixed at 3000 sps • Displacement RAW fixed at 300 sps
              </div>
            )
          ) : (
            <div className="rounded-md border border-dashed border-gray-300 bg-gray-50 px-3 py-2 text-sm text-gray-500">
              Detect a sensor to view sampling options.
            </div>
          )}
          {uiNotice && <p className="mt-1 text-xs text-yellow-700">{uiNotice}</p>}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Baud Rate</label>
          {detectedSensorType || sensorOverrideEnabled ? (
            <select
              value={baudRate}
              onChange={(event) => setBaudRate(Number(event.target.value))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-[#085f63] focus:border-[#085f63]"
            >
              {baudRateOptions.map((rate) => (
                <option key={rate} value={rate}>
                  {rate.toLocaleString()} bps
                  {rate === selectedProfile.defaultBaudRate ? ' (default)' : ''}
                </option>
              ))}
            </select>
          ) : (
            <div className="rounded-md border border-dashed border-gray-300 bg-gray-50 px-3 py-2 text-sm text-gray-500">
              Detect a sensor to view baud-rate options.
            </div>
          )}
        </div>

        {(detectedSensorType || sensorOverrideEnabled) && (
          <div className="flex justify-end">
            <button
              type="button"
              onClick={handleResetSamplingAndBaud}
              className="px-3 py-1 text-sm font-medium text-[#085f63] border border-[#085f63] rounded-md hover:bg-[#e0f5f4]"
            >
              Restore defaults
            </button>
          </div>
        )}

        <div>
          <div className="rounded-md border border-gray-200 bg-gray-50 p-3 text-sm text-gray-800">
            {status === 'success' && (
              <div className="flex items-center space-x-2 text-green-700">
                <CheckCircle className="h-5 w-5" />
                <span>{message}</span>
              </div>
            )}
            {status === 'error' && (
              <div className="flex items-center space-x-2 text-red-700">
                <XCircle className="h-5 w-5" />
                <span>{message}</span>
              </div>
            )}
            {status === 'idle' && message && (
              <div className="flex items-center space-x-2 text-gray-700">
                <AlertTriangle className="h-5 w-5" />
                <span>{message}</span>
              </div>
            )}
            {commandWarning && (
              <div className="mt-2 flex items-start space-x-2 text-yellow-700">
                <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0" />
                <span>{commandWarning}</span>
              </div>
            )}
            {updateInfo && (
              <div className="mt-2 text-xs text-blue-700">
                Update available: {updateInfo.version}{' '}
                {updateInfo.downloadUrl && (
                  <a href={updateInfo.downloadUrl} className="underline" target="_blank" rel="noreferrer">
                    Download
                  </a>
                )}
              </div>
            )}
            {updateDownloadPath && (
              <div className="mt-2 text-xs text-gray-700 break-all">
                Latest download saved to <code className="font-mono">{updateDownloadPath}</code>
              </div>
            )}
            {updateNotice && (
              <div className="mt-1 text-xs text-yellow-700">{updateNotice}</div>
            )}
          </div>
        </div>

        {requiresRestart && (
          <div className="rounded-md border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-800">
            <strong>Restart required.</strong> Disconnect and power cycle the sensor to apply changes.
          </div>
        )}

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
          <button
            onClick={handleConfigure}
            disabled={loading || detecting || !sessionActive}
            className="flex items-center justify-center space-x-2 px-4 py-2 bg-[#085f63] text-white rounded-md hover:bg-[#0a7a80] disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Play className="h-5 w-5" />}
            <span>Start Configuration</span>
          </button>
          <button
            onClick={handleExitAutoMode}
            disabled={loading || detecting || !sessionActive}
            className="flex items-center justify-center space-x-2 px-4 py-2 rounded-md border border-[#085f63] text-[#085f63] hover:bg-[#e0f5f4] disabled:border-gray-300 disabled:text-gray-400 transition-colors"
          >
            <AlertTriangle className="h-5 w-5" />
            <span>Exit Auto Mode</span>
          </button>
          <button
            onClick={handleFactoryReset}
            disabled={loading || detecting || !sessionActive}
            className="flex items-center justify-center space-x-2 px-4 py-2 rounded-md border border-red-400 text-red-600 hover:bg-red-50 disabled:border-gray-300 disabled:text-gray-400 transition-colors"
          >
            <Power className="h-5 w-5" />
            <span>Factory Reset</span>
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-4 text-sm">
          <button
            onClick={handleUpdateCheck}
            disabled={loading || !helperToken}
            className="text-[#085f63] underline disabled:text-gray-400"
          >
            Check for helper updates
          </button>
          <button
            onClick={handleUpdateDownload}
            disabled={loading || !helperToken || !updateInfo}
            className="text-[#085f63] underline disabled:text-gray-400"
          >
            Download latest update
          </button>
        </div>

        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">Output Logs</h3>
          <LogViewer logs={logs} />
        </div>
      </div>
    </div>
  );
}
