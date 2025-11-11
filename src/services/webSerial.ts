import { LogEntry } from '../types';

const READ_TIMEOUT_MS = 3000;
const FLASH_BACKUP_TIMEOUT_MS = 5000;
const FLASH_BACKUP_POLL_INTERVAL_MS = 100;
const EXIT_TRANSITION_DELAY_MS = 200;
const SOFTWARE_RESET_DELAY_MS = 2500;
const MAX_CONFIG_ATTEMPTS = 2;
const RECONNECT_DELAY_MS = 4000;

type LogSink = (entry: LogEntry) => void;

const createLog = (sink?: LogSink) => (message: string, type: LogEntry['type'] = 'stdout') => {
  sink?.({
    type,
    message,
    timestamp: new Date().toISOString(),
  });
};

export type SensorType = 'vibration' | 'imu';

export interface ImuSamplingOption {
  id: string;
  rate: number; // samples per second
  label: string;
  doutValue: number;
  filterValue: number;
  filterLabel: string;
  note?: string;
}

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const IMU_SAMPLING_OPTIONS: ImuSamplingOption[] = [
  {
    id: '2000',
    rate: 2000,
    label: '2000 sps',
    doutValue: 0x00,
    filterValue: 0b00001,
    filterLabel: 'Moving average filter, TAP = 2',
    note: 'Requires 921600 baud to avoid bandwidth overflow.',
  },
  {
    id: '1000',
    rate: 1000,
    label: '1000 sps',
    doutValue: 0x01,
    filterValue: 0b00010,
    filterLabel: 'Moving average filter, TAP = 4',
    note: 'Works best at 460800 baud or higher; 921600 recommended for headroom.',
  },
  {
    id: '500',
    rate: 500,
    label: '500 sps',
    doutValue: 0x02,
    filterValue: 0b00011,
    filterLabel: 'Moving average filter, TAP = 8',
  },
  {
    id: '250',
    rate: 250,
    label: '250 sps',
    doutValue: 0x04,
    filterValue: 0b00100,
    filterLabel: 'Moving average filter, TAP = 16',
  },
  {
    id: '125',
    rate: 125,
    label: '125 sps',
    doutValue: 0x06,
    filterValue: 0b00101,
    filterLabel: 'Moving average filter, TAP = 32',
  },
  {
    id: '62.5',
    rate: 62.5,
    label: '62.5 sps',
    doutValue: 0x09,
    filterValue: 0b00101,
    filterLabel: 'Moving average filter, TAP = 32',
  },
  {
    id: '31.25',
    rate: 31.25,
    label: '31.25 sps',
    doutValue: 0x0c,
    filterValue: 0b00110,
    filterLabel: 'Moving average filter, TAP = 64',
  },
  {
    id: '15.625',
    rate: 15.625,
    label: '15.625 sps',
    doutValue: 0x0f,
    filterValue: 0b00111,
    filterLabel: 'Moving average filter, TAP = 128',
  },
];

const IMU_SAMPLING_MAP = new Map<string, ImuSamplingOption>(
  IMU_SAMPLING_OPTIONS.map((option) => [option.id, option]),
);

interface SensorProfile {
  label: string;
  model: string;
  summary: string;
  defaultBaudRate: number;
  baudRates: number[];
  resetCommands: number[][];
  configureCommands: number[][];
  configureLog: string;
  flashBackupCommands: number[][];
  successMessage: string;
  successLogs: string[];
}

const SENSOR_PROFILES_MAP: Record<SensorType, SensorProfile> = {
  vibration: {
    label: 'Vibration Sensor',
    model: 'Epson M-A542VR1',
    summary: 'Programs the vibration sensor into Auto Start mode.',
    defaultBaudRate: 460800,
    baudRates: [230400, 460800, 921600],
    resetCommands: [
      [0, 0xff, 0xff, 0x0d],
      [0, 0xff, 0xff, 0x0d],
      [0, 0xff, 0xff, 0x0d],
    ],
    configureCommands: [
      [0, 0xfe, 0x01, 0x0d],
      [0, 0x88, 0x03, 0x0d],
    ],
    configureLog: 'Setting UART_CTRL register to AUTO_START and UART_AUTO (0x03).',
    flashBackupCommands: [
      [0, 0xfe, 0x01, 0x0d],
      [0, 0x8a, 0x08, 0x0d],
    ],
    successMessage: 'Vibration sensor configured successfully!',
    successLogs: [
      'After power cycle, the vibration sensor will start streaming automatically.',
      'Configuration tool by Jnana Phani A @ Zenith Tek.',
    ],
  },
  imu: {
    label: 'IMU Sensor',
    model: 'Epson M-G552PR80',
    summary: 'Programs the IMU into Auto Start mode.',
    defaultBaudRate: 460800,
    baudRates: [230400, 460800, 921600],
    resetCommands: [
      [0, 0xff, 0xff, 0x0d],
      [0, 0xff, 0xff, 0x0d],
      [0, 0xff, 0xff, 0x0d],
    ],
    configureCommands: [
      [0, 0xfe, 0x01, 0x0d],
      [0, 0x85, 0x04, 0x0d],
      [0, 0x86, 0x04, 0x0d],
      [0, 0x88, 0x03, 0x0d],
      [0, 0x8c, 0x02, 0x0d],
      [0, 0x8d, 0xf0, 0x0d],
      [0, 0x8f, 0x70, 0x0d],
    ],
    configureLog: 'Programming IMU sampling and burst registers for Auto Start output.',
    flashBackupCommands: [
      [0, 0xfe, 0x01, 0x0d],
      [0, 0x8a, 0x08, 0x0d],
    ],
    successMessage: 'IMU configured successfully!',
    successLogs: [
      'After power cycle, the IMU will stream 32-bit burst frames automatically.',
      'Configuration tool by Jnana Phani A @ Zenith Tek.',
    ],
  },
};

export const SENSOR_PROFILES = SENSOR_PROFILES_MAP;

const FLASH_BACKUP_STATUS_COMMAND: number[] = [4, 0x0a, 0x00, 0x0d];
const FLASH_BACKUP_VERIFY_COMMANDS: number[][] = [
  [0, 0xfe, 0x00, 0x0d],
  [4, 0x04, 0x00, 0x0d],
];
const FILTER_STATUS_COMMAND: number[] = [4, 0x06, 0x00, 0x0d];

const FILTER_SETTLE_TIMEOUT_MS = 4000;
const FILTER_SETTLE_POLL_INTERVAL_MS = 50;

async function readBytes(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  expected: number,
  timeoutMs: number,
): Promise<number[]> {
  const result: number[] = [];
  const start = Date.now();

  while (result.length < expected) {
    const elapsed = Date.now() - start;
    if (elapsed > timeoutMs) {
      throw new Error('Read timeout while waiting for sensor response');
    }

    const { value, done } = await reader.read();
    if (done) {
      break;
    }

    if (value) {
      for (let i = 0; i < value.length && result.length < expected; i += 1) {
        result.push(value[i]);
      }
    }
  }

  if (result.length !== expected) {
    throw new Error(`Expected ${expected} bytes, received ${result.length}`);
  }

  return result;
}

async function sendCommand(
  writer: WritableStreamDefaultWriter<Uint8Array>,
  reader: ReadableStreamDefaultReader<Uint8Array>,
  command: number[],
): Promise<number[]> {
  const expected = command[0];
  const payload = new Uint8Array(command.length - 1);
  for (let i = 1; i < command.length; i += 1) {
    payload[i - 1] = command[i];
  }

  await writer.write(payload);

  if (expected > 0) {
    return readBytes(reader, expected, READ_TIMEOUT_MS);
  }

  return [];
}

async function sendCommands(
  writer: WritableStreamDefaultWriter<Uint8Array>,
  reader: ReadableStreamDefaultReader<Uint8Array>,
  commands: number[][],
): Promise<number[]> {
  let combined: number[] = [];
  for (const command of commands) {
    const response = await sendCommand(writer, reader, command);
    combined = combined.concat(response);
  }
  return combined;
}

async function pollFlashBackup(
  writer: WritableStreamDefaultWriter<Uint8Array>,
  reader: ReadableStreamDefaultReader<Uint8Array>,
  log: ReturnType<typeof createLog>,
): Promise<void> {
  const start = Date.now();
  while (Date.now() - start < FLASH_BACKUP_TIMEOUT_MS) {
    await sendCommand(writer, reader, [0, 0xfe, 0x01, 0x0d]);
    const response = await sendCommand(writer, reader, FLASH_BACKUP_STATUS_COMMAND);
    if (response.length >= 4) {
      const globCmdLow = response[2] ?? 0;
      if ((globCmdLow & 0b00001000) === 0) {
        log('Flash backup completed successfully');
        return;
      }
    }
    await new Promise((resolve) => setTimeout(resolve, FLASH_BACKUP_POLL_INTERVAL_MS));
  }
  throw new Error('Flash backup timeout - backup may not have completed');
}

async function verifyFlashBackup(
  writer: WritableStreamDefaultWriter<Uint8Array>,
  reader: ReadableStreamDefaultReader<Uint8Array>,
): Promise<void> {
  const response = await sendCommands(writer, reader, FLASH_BACKUP_VERIFY_COMMANDS);
  if (response.length >= 4) {
    const diagStat1Low = response[2] ?? 0;
    if ((diagStat1Low & 0b00000001) !== 0) {
      throw new Error('Flash backup error detected (FLASH_BU_ERR = 1)');
    }
    return;
  }

  throw new Error('Failed to read DIAG_STAT1 for flash verification');
}

function formatPortLabel(port: SerialPort): string {
  try {
    const info = port.getInfo?.();
    const parts: string[] = [];
    if (info?.usbVendorId !== undefined) {
      parts.push(`VID ${info.usbVendorId.toString(16).padStart(4, '0').toUpperCase()}`);
    }
    if (info?.usbProductId !== undefined) {
      parts.push(`PID ${info.usbProductId.toString(16).padStart(4, '0').toUpperCase()}`);
    }
    return parts.length > 0 ? parts.join(' • ') : 'Serial device';
  } catch {
    return 'Serial device';
  }
}

export interface ConfigureOptions {
  port: SerialPort;
  baudRate?: number;
  sensor: SensorType;
  imuSamplingId?: string;
  onLog?: LogSink;
}

export interface ConfigureResult {
  success: boolean;
  message: string;
}

export interface ExitAutoModeOptions {
  port: SerialPort;
  sensor: SensorType;
  baudRate?: number;
  onLog?: LogSink;
}

export interface FactoryResetOptions {
  port: SerialPort;
  sensor: SensorType;
  onLog?: LogSink;
}

export const webSerialService = {
  isSupported(): boolean {
    return typeof navigator !== 'undefined' && 'serial' in navigator;
  },

  async getSavedPorts(): Promise<SerialPort[]> {
    if (!this.isSupported()) {
      return [];
    }
    return navigator.serial!.getPorts();
  },

  async requestPort(): Promise<SerialPort> {
    if (!this.isSupported()) {
      throw new Error('Web Serial API is not available in this browser');
    }
    return navigator.serial!.requestPort();
  },

  describePort(port: SerialPort): string {
    return formatPortLabel(port);
  },

  listImuSamplingOptions(): ImuSamplingOption[] {
    return IMU_SAMPLING_OPTIONS;
  },

  listProfiles(): SensorProfile[] {
    return Object.values(SENSOR_PROFILES_MAP);
  },

  async configureSensor(options: ConfigureOptions): Promise<ConfigureResult> {
    const { port, sensor, onLog } = options;
    const profile = SENSOR_PROFILES_MAP[sensor];

    if (!profile) {
      const message = `Unsupported sensor type: ${sensor}`;
      createLog(onLog)(message, 'stderr');
      return { success: false, message };
    }

    const imuSampling =
      sensor === 'imu'
        ? IMU_SAMPLING_MAP.get(options.imuSamplingId || IMU_SAMPLING_OPTIONS[0].id) ||
          IMU_SAMPLING_OPTIONS[0]
        : undefined;

    const baudRate = options.baudRate ?? profile.defaultBaudRate;
    const log = createLog(onLog);

    const ensurePortOpen = async () => {
      if (!port.readable || !port.writable) {
        await port.open({
          baudRate,
          dataBits: 8,
          stopBits: 1,
          parity: 'none',
          flowControl: 'none',
        });
      }
    };

    for (let attempt = 1; attempt <= MAX_CONFIG_ATTEMPTS; attempt += 1) {
      let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
      let writer: WritableStreamDefaultWriter<Uint8Array> | null = null;

      const safeClose = async () => {
        try {
          reader?.releaseLock();
        } catch {
          // ignore
        }
        try {
          writer?.releaseLock();
        } catch {
          // ignore
        }
        reader = null;
        writer = null;
        try {
          await port.close();
        } catch {
          // ignore close errors
        }
      };

      try {
        await ensurePortOpen();

        if (!port.readable || !port.writable) {
          throw new Error('Failed to access serial streams after opening the port');
        }

        reader = port.readable.getReader();
        writer = port.writable.getWriter();

        log(`Configuring ${profile.label} (${profile.model}) at ${baudRate.toLocaleString()} bps`);
        log(profile.summary);

        log('Sending sensor reset sequence');
        await sendCommands(writer, reader, profile.resetCommands);

        if (sensor === 'imu') {
          if (!imuSampling) {
            throw new Error('No sampling option provided for IMU sensor.');
          }
          if (imuSampling.rate > 500 && baudRate < 921600) {
            log(
              `Warning: ${imuSampling.label} typically requires 921600 baud. Selected ${baudRate.toLocaleString()} bps may overflow the host interface.`,
              'stderr',
            );
          }
          await configureImuSampling(writer, reader, log, imuSampling);

          const imuBaseCommands: number[][] = [
            [0, 0xfe, 0x01, 0x0d],
            [0, 0x88, 0x03, 0x0d], // UART_AUTO + AUTO_START
            [0, 0x8c, 0x02, 0x0d], // BURST_CTRL1: COUNT on, checksum off
            [0, 0x8d, 0xf0, 0x0d], // BURST_CTRL2: FLAG, TEMP, GYRO, ACCL
            [0, 0x8f, 0x70, 0x0d], // BURST_CTRL4: 32-bit outputs
          ];
          await sendCommands(writer, reader, imuBaseCommands);
        } else {
          log(profile.configureLog);
          await sendCommands(writer, reader, profile.configureCommands);
        }

        log('Triggering flash backup to persist settings');
        await sendCommands(writer, reader, profile.flashBackupCommands);

        log('Waiting for flash backup to complete...');
        await pollFlashBackup(writer, reader, log);

        log('Verifying flash backup status');
        await verifyFlashBackup(writer, reader);

        profile.successLogs.forEach((line) => log(line));
        await safeClose();

        return {
          success: true,
          message: profile.successMessage,
        };
      } catch (error) {
        const message =
          error instanceof Error ? error.message : 'An unknown error occurred during configuration';
        const isDeviceLostError =
          error instanceof DOMException && message.toLowerCase().includes('device has been lost');

        await safeClose();

        if (isDeviceLostError && attempt < MAX_CONFIG_ATTEMPTS) {
          log('Sensor rebooted during configuration. Waiting for reconnection before retrying...');
          await delay(RECONNECT_DELAY_MS);
          continue;
        }

        log(message, 'stderr');
        return {
          success: false,
          message,
        };
      }
    }

    return {
      success: false,
      message: 'Configuration aborted after repeated reconnect attempts.',
    };
  },

  async exitAutoMode(options: ExitAutoModeOptions): Promise<ConfigureResult> {
    const { port, sensor, baudRate, onLog } = options;
    const profile = SENSOR_PROFILES_MAP[sensor];

    if (!profile) {
      const message = `Unsupported sensor type: ${sensor}`;
      createLog(onLog)(message, 'stderr');
      return { success: false, message };
    }

    const effectiveBaud = baudRate ?? profile.defaultBaudRate;
    const log = createLog(onLog);

    if (!port.readable || !port.writable) {
      try {
        await port.open({
          baudRate: effectiveBaud,
          dataBits: 8,
          stopBits: 1,
          parity: 'none',
          flowControl: 'none',
        });
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : 'Unable to open serial connection. Please check the cable and permissions.';
        log(message, 'stderr');
        throw new Error(message);
      }
    }

    if (!port.readable || !port.writable) {
      throw new Error('Failed to access serial streams after opening the port');
    }

    const reader = port.readable.getReader();
    const writer = port.writable.getWriter();

    try {
      log('Stopping sensor sampling and returning to configuration mode');
      await sendCommands(writer, reader, [
        [0, 0xfe, 0x00, 0x0d],
        [0, 0x83, 0x02, 0x0d],
      ]);
      await delay(EXIT_TRANSITION_DELAY_MS);

      log('Clearing UART auto-start bits');
      await sendCommands(writer, reader, [
        [0, 0xfe, 0x01, 0x0d],
        [0, 0x88, 0x00, 0x0d],
      ]);

      log('Persisting change with flash backup');
      await sendCommands(writer, reader, profile.flashBackupCommands);

      log('Auto mode disabled successfully.');
      return {
        success: true,
        message: 'Auto mode disabled successfully.',
      };
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to disable auto mode.';
      log(message, 'stderr');
      return { success: false, message };
    } finally {
      reader.releaseLock();
      writer.releaseLock();
      try {
        await port.close();
      } catch {
        // ignore
      }
    }
  },

  async factoryReset(options: FactoryResetOptions): Promise<ConfigureResult> {
    const { port, sensor, onLog } = options;
    const profile = SENSOR_PROFILES_MAP[sensor];

    if (!profile) {
      const message = `Unsupported sensor type: ${sensor}`;
      createLog(onLog)(message, 'stderr');
      return { success: false, message };
    }

    const log = createLog(onLog);

    if (!port.readable || !port.writable) {
      try {
        await port.open({
          baudRate: profile.defaultBaudRate,
          dataBits: 8,
          stopBits: 1,
          parity: 'none',
          flowControl: 'none',
        });
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : 'Unable to open serial connection. Please check the cable and permissions.';
        log(message, 'stderr');
        throw new Error(message);
      }
    }

    if (!port.readable || !port.writable) {
      throw new Error('Failed to access serial streams after opening the port');
    }

    const reader = port.readable.getReader();
    const writer = port.writable.getWriter();

    try {
      log('Issuing software reset (SOFT_RST)');
      await sendCommands(writer, reader, [
        [0, 0xfe, 0x01, 0x0d],
        [0, 0x8a, 0x80, 0x0d],
      ]);
      log('Waiting for sensor to reboot...');
      await delay(SOFTWARE_RESET_DELAY_MS);
      log('Software reset completed. Sensor restored to defaults.');
      return {
        success: true,
        message: 'Sensor reset to defaults. Reconnect before configuring again.',
      };
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Software reset failed.';
      log(message, 'stderr');
      return { success: false, message };
    } finally {
      reader.releaseLock();
      writer.releaseLock();
      try {
        await port.close();
      } catch {
        // ignore
      }
    }
  },
};

async function configureImuSampling(
  writer: WritableStreamDefaultWriter<Uint8Array>,
  reader: ReadableStreamDefaultReader<Uint8Array>,
  log: ReturnType<typeof createLog>,
  option: ImuSamplingOption,
) {
  log(`Applying sampling rate ${option.label}`);
  await sendCommands(writer, reader, [
    [0, 0xfe, 0x01, 0x0d], // WINDOW = 1
    [0, 0x85, option.doutValue, 0x0d], // SMPL_CTRL DOUT_RATE
  ]);

  log(`Selecting filter: ${option.filterLabel}`);
  await sendCommands(writer, reader, [
    [0, 0xfe, 0x01, 0x0d],
    [0, 0x86, option.filterValue, 0x0d],
  ]);
  await waitForFilterReady(writer, reader, log);

  if (option.note) {
    log(option.note);
  }
}

async function waitForFilterReady(
  writer: WritableStreamDefaultWriter<Uint8Array>,
  reader: ReadableStreamDefaultReader<Uint8Array>,
  log: ReturnType<typeof createLog>,
) {
  const start = Date.now();
  while (Date.now() - start < FILTER_SETTLE_TIMEOUT_MS) {
    await sendCommand(writer, reader, [0, 0xfe, 0x01, 0x0d]); // ensure WINDOW = 1
    const response = await sendCommand(writer, reader, FILTER_STATUS_COMMAND);
    if (response.length >= 4) {
      const status = response[2] ?? 0;
      const busy = (status & 0b0010_0000) !== 0;
      if (!busy) {
        log('Filter configuration complete');
        return;
      }
    }
    await new Promise((resolve) => setTimeout(resolve, FILTER_SETTLE_POLL_INTERVAL_MS));
  }
  throw new Error('Filter configuration timed out before completion');
}

