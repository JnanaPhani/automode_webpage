import { LogEntry } from '../types';

const READ_TIMEOUT_MS = 3000;
const FLASH_BACKUP_TIMEOUT_MS = 5000;
const FLASH_BACKUP_POLL_INTERVAL_MS = 100;
const FLASH_TEST_TIMEOUT_MS = 5000;
const FLASH_TEST_POLL_INTERVAL_MS = 100;
const EXIT_TRANSITION_DELAY_MS = 200;
const RESET_STABILIZATION_DELAY_MS = 800;
const READY_TIMEOUT_MS = 7000;
const READY_POLL_INTERVAL_MS = 50;
const WINDOW_REGISTER = 0xfe;
const WINDOW_ID_CONFIGURATION = 0x00;
const WINDOW_ID_METADATA = 0x01;
const MODE_CTRL_REGISTER = 0x02;
const UART_CTRL_REGISTER = 0x88;
const MSC_CTRL_REGISTER = 0x02;
const DIAG_STAT1_REGISTER = 0x04;
const GLOB_CMD_REGISTER = 0x0a;

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

interface SerialSession {
  port: SerialPort;
  baudRate: number;
  drainAbort?: AbortController;
  drainTask?: Promise<void>;
}

let activeSession: SerialSession | null = null;

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
    summary: ' ',
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
    successMessage: 'Vibration sensor configured successfully.',
    successLogs: [
      'After power cycle, the vibration sensor will start streaming automatically.',
      'Restart or power cycle the sensor now to activate Auto Mode.',
      'Configuration tool by Jnana Phani A @ Zenith Tek.',
    ],
  },
  imu: {
    label: 'IMU Sensor',
    model: 'Epson M-G552PR80',
    summary: ' ',
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
    successMessage: 'IMU configured successfully. Restart the sensor to begin Auto Mode.',
    successLogs: [
      'After power cycle, the IMU will stream 32-bit burst frames automatically.',
      'Restart or power cycle the sensor now to activate Auto Mode.',
      'Configuration tool by Jnana Phani A @ Zenith Tek.',
    ],
  },
};

export const SENSOR_PROFILES = SENSOR_PROFILES_MAP;

const PRODUCT_ID_ALIASES: Record<string, string> = {
  A342VD10: 'M-A542VR1',
  G365PDF1: 'M-G552PR80',
  G552PR80: 'M-G552PR80',
};

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

export interface PreparePortOptions {
  port: SerialPort;
  baudRate: number;
  onLog?: LogSink;
}

export interface ConfigureResult {
  success: boolean;
  message: string;
  requiresRestart?: boolean;
}

export interface DetectSensorOptions {
  port: SerialPort;
  sensor: SensorType;
  baudRate?: number;
  onLog?: LogSink;
}

export interface DetectSensorResult {
  success: boolean;
  message: string;
  productId?: string;
  productIdRaw?: string;
  serialNumber?: string;
}

export interface ExitAutoModeOptions {
  port: SerialPort;
  sensor: SensorType;
  baudRate?: number;
  persistDisableAuto?: boolean;
  onLog?: LogSink;
}

export interface FactoryResetOptions {
  port: SerialPort;
  sensor: SensorType;
  baudRate?: number;
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

  async preparePort(options: PreparePortOptions): Promise<void> {
    const { port, baudRate, onLog } = options;
    const log = createLog(onLog);
    try {
      await ensureSession(port, baudRate, log);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : 'Failed to prepare the serial port session.';
      log(message, 'stderr');
      throw error instanceof Error ? error : new Error(message);
    }
  },

  async disconnect(): Promise<void> {
    await closeActiveSession();
  },

  isConnected(): boolean {
    return activeSession !== null;
  },

  getActivePort(): SerialPort | null {
    return activeSession?.port ?? null;
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

    try {
      const session = await ensureSession(port, baudRate, log);
      return await withSessionIO(session, log, async (writer, reader) => {
    try {
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
          [0, 0x88, 0x03, 0x0d], // UART_CTRL: AUTO_START + UART_AUTO
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

      return {
        success: true,
        message: profile.successMessage,
            requiresRestart: true,
      };
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'An unknown error occurred during configuration';
      log(message, 'stderr');
      return {
        success: false,
        message,
      };
        }
      });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : 'An unknown error occurred while preparing the serial session.';
      log(message, 'stderr');
      return { success: false, message };
    }
  },

  async detectSensor(options: DetectSensorOptions): Promise<DetectSensorResult> {
    const { port, sensor, baudRate, onLog } = options;
    const profile = SENSOR_PROFILES_MAP[sensor];

    if (!profile) {
      const message = `Unsupported sensor type: ${sensor}`;
      createLog(onLog)(message, 'stderr');
      return { success: false, message };
    }

    const effectiveBaud = baudRate ?? profile.defaultBaudRate;
    const log = createLog(onLog);

    try {
      const session = await ensureSession(port, effectiveBaud, log);
      return await withSessionIO(session, log, async (writer, reader) => {
        let uartCtrlBefore = 0;
        let restoreAutoMode = false;
        let exitSequenceCompleted = false;

        try {
          await setRegisterWindow(writer, reader, WINDOW_ID_METADATA);
          log('Reading current UART_CTRL state before detection');
          uartCtrlBefore = await readRegisterWord(writer, reader, UART_CTRL_REGISTER);
          log(`UART_CTRL prior to detection: 0x${uartCtrlBefore.toString(16).padStart(4, '0')}`);
          restoreAutoMode = (uartCtrlBefore & 0x03) !== 0;

          if (restoreAutoMode) {
            log('Sensor is currently streaming. Temporarily disabling auto mode to read identity registers.');
          }

          await exitAutoModeSequence(writer, reader, log, profile, false);
          exitSequenceCompleted = true;

          log('Detecting sensor identity information');
          await setRegisterWindow(writer, reader, WINDOW_ID_METADATA);

          const productWords = [];
          for (const address of [0x6a, 0x6c, 0x6e, 0x70]) {
            log(`Reading product register 0x${address.toString(16)}`);
            productWords.push(await readRegisterWord(writer, reader, address));
          }
          const serialWords = [];
          for (const address of [0x74, 0x76, 0x78, 0x7a]) {
            log(`Reading serial register 0x${address.toString(16)}`);
            serialWords.push(await readRegisterWord(writer, reader, address));
          }

          log(
            `PROD_ID raw words: ${productWords
              .map((word) => `0x${word.toString(16).padStart(4, '0')}`)
              .join(' ')}`,
          );
          log(
            `SERIAL raw words: ${serialWords
              .map((word) => `0x${word.toString(16).padStart(4, '0')}`)
              .join(' ')}`,
          );

          const productIdRaw = decodeAsciiWords(productWords).trim();
          const productId = PRODUCT_ID_ALIASES[productIdRaw] ?? productIdRaw;
          const serialNumber = decodeAsciiWords(serialWords).trim();

          log(`Product ID: ${productId}`);
          log(`Serial Number: ${serialNumber}`);

          await setRegisterWindow(writer, reader, WINDOW_ID_CONFIGURATION);

          return {
            success: true,
            message: 'Sensor identity retrieved successfully.',
            productIdRaw,
            productId,
            serialNumber,
          };
        } catch (error) {
          const message =
            error instanceof Error
              ? `${error.name ?? 'Error'}: ${error.message}`
              : 'An unknown error occurred while detecting sensor identity.';
          log(message, 'stderr');
          return {
            success: false,
            message: error instanceof Error ? error.message : message,
          };
        } finally {
          if (exitSequenceCompleted && restoreAutoMode) {
            try {
              await restoreAutoModeState(writer, reader, log, uartCtrlBefore & 0xff);
              log('Auto mode restored to previous state.');
            } catch (restoreError) {
              const restoreMessage =
                restoreError instanceof Error
                  ? `Failed to restore auto mode after detection: ${restoreError.message}`
                  : 'Failed to restore auto mode after detection.';
              log(restoreMessage, 'stderr');
            }
          }
        }
        });
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
          : 'An unknown error occurred while preparing the serial session.';
        log(message, 'stderr');
      return { success: false, message };
    }
  },

  async exitAutoMode(options: ExitAutoModeOptions): Promise<ConfigureResult> {
    const { port, sensor, baudRate, persistDisableAuto, onLog } = options;
    const profile = SENSOR_PROFILES_MAP[sensor];

    if (!profile) {
      const message = `Unsupported sensor type: ${sensor}`;
      createLog(onLog)(message, 'stderr');
      return { success: false, message };
    }

    const effectiveBaud = baudRate ?? profile.defaultBaudRate;
    const log = createLog(onLog);
    const persist = persistDisableAuto ?? true;

    try {
      const session = await ensureSession(port, effectiveBaud, log);
      return await withSessionIO(session, log, async (writer, reader) => {
        try {
          await exitAutoModeSequence(writer, reader, log, profile, persist);
      log('Auto mode disabled successfully.');
      return {
        success: true,
            message: persist
              ? 'Auto mode disabled and persisted to flash.'
              : 'Auto mode disabled (not persisted).',
      };
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'Failed to disable auto mode.';
      log(message, 'stderr');
      return { success: false, message };
        }
      });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : 'An unknown error occurred while preparing the serial session.';
      log(message, 'stderr');
      return { success: false, message };
    }
  },

  async factoryReset(options: FactoryResetOptions): Promise<ConfigureResult> {
    const { port, sensor, baudRate, onLog } = options;
    const profile = SENSOR_PROFILES_MAP[sensor];

    if (!profile) {
      const message = `Unsupported sensor type: ${sensor}`;
      createLog(onLog)(message, 'stderr');
      return { success: false, message };
    }

    const log = createLog(onLog);
    const effectiveBaud = baudRate ?? profile.defaultBaudRate;

    try {
      const session = await ensureSession(port, effectiveBaud, log);
      return await withSessionIO(session, log, async (writer, reader) => {
        try {
          await exitAutoModeSequence(writer, reader, log, profile, true);

          log('Sending reset spell (3 × 0xFF frames)');
          await sendCommands(writer, reader, profile.resetCommands);
          await delay(EXIT_TRANSITION_DELAY_MS);

          let flashTestSucceeded = true;
          try {
            await performFlashTest(writer, reader, log);
          } catch (error) {
            flashTestSucceeded = false;
            const message =
              error instanceof Error ? error.message : 'Flash test reported an unknown error';
            log(message, 'stderr');
          }

          await performSoftwareReset(writer, reader, log);
          log('Allowing sensor to stabilise after reboot...');
          await delay(RESET_STABILIZATION_DELAY_MS);

          const message = flashTestSucceeded
            ? 'Full reset complete. Auto mode disabled and persisted; sensor rebooted.'
            : 'Full reset complete (flash test reported an issue). Auto mode disabled and sensor rebooted.';
          return {
            success: true,
            message,
          };
        } catch (error) {
          const message =
            error instanceof Error ? error.message : 'Full reset sequence failed.';
          log(message, 'stderr');
          return { success: false, message };
        }
        });
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
          : 'An unknown error occurred while preparing the serial session.';
        log(message, 'stderr');
      return { success: false, message };
    }
  },
};

async function setRegisterWindow(
  writer: WritableStreamDefaultWriter<Uint8Array>,
  reader: ReadableStreamDefaultReader<Uint8Array>,
  windowId: number,
) {
  await sendCommands(writer, reader, [[0, WINDOW_REGISTER, windowId, 0x0d]]);
}

async function readRegisterWord(
  writer: WritableStreamDefaultWriter<Uint8Array>,
  reader: ReadableStreamDefaultReader<Uint8Array>,
  registerAddress: number,
): Promise<number> {
  const response = await sendCommand(writer, reader, [4, registerAddress, 0x00, 0x0d]);
  if (response.length < 4) {
    throw new Error(`Unexpected response length reading register 0x${registerAddress.toString(16)}`);
  }
  const high = response[1] ?? 0;
  const low = response[2] ?? 0;
  return (high << 8) | low;
}

function decodeAsciiWords(words: number[]): string {
  return words
    .map((word) => {
      const low = word & 0xff;
      const high = (word >> 8) & 0xff;
      const lowChar = low === 0 ? '' : String.fromCharCode(low);
      const highChar = high === 0 ? '' : String.fromCharCode(high);
      return `${lowChar}${highChar}`;
    })
    .join('')
    .trim();
}

async function exitAutoModeSequence(
  writer: WritableStreamDefaultWriter<Uint8Array>,
  reader: ReadableStreamDefaultReader<Uint8Array>,
  log: ReturnType<typeof createLog>,
  profile: SensorProfile,
  persistDisableAuto: boolean,
): Promise<void> {
  log('Stopping sensor sampling and requesting configuration mode');
      await sendCommands(writer, reader, [
    [0, WINDOW_REGISTER, WINDOW_ID_CONFIGURATION, 0x0d],
    [0, 0x83, 0x02, 0x0d],
  ]);
  await delay(EXIT_TRANSITION_DELAY_MS);

  await setRegisterWindow(writer, reader, WINDOW_ID_CONFIGURATION);
  const modeCtrl = await readRegisterWord(writer, reader, MODE_CTRL_REGISTER);
  if ((modeCtrl & 0x0400) === 0) {
    throw new Error(
      `Sensor did not report configuration mode (MODE_CTRL=0x${modeCtrl.toString(16).padStart(4, '0')})`,
    );
  }
  log(`Sensor reports configuration mode (MODE_CTRL=0x${modeCtrl.toString(16).padStart(4, '0')})`);

  log('Clearing UART auto-start bits');
  await setRegisterWindow(writer, reader, WINDOW_ID_METADATA);
  await sendCommands(writer, reader, [[0, 0x88, 0x00, 0x0d]]);

  if (persistDisableAuto) {
    log('Persisting UART auto-disable state via flash backup');
    await sendCommands(writer, reader, profile.flashBackupCommands);
    log('Waiting for flash backup to complete...');
    await pollFlashBackup(writer, reader, log);
    log('Verifying flash backup result');
    await verifyFlashBackup(writer, reader);
    log('Flash backup verified successfully');
  }

  await setRegisterWindow(writer, reader, WINDOW_ID_CONFIGURATION);
}

async function restoreAutoModeState(
  writer: WritableStreamDefaultWriter<Uint8Array>,
  reader: ReadableStreamDefaultReader<Uint8Array>,
  log: ReturnType<typeof createLog>,
  uartCtrlValue: number,
): Promise<void> {
  log('Restoring UART auto-start bits');
  await setRegisterWindow(writer, reader, WINDOW_ID_METADATA);
  await sendCommands(writer, reader, [[0, UART_CTRL_REGISTER, uartCtrlValue & 0xff, 0x0d]]);
  await delay(EXIT_TRANSITION_DELAY_MS);
  await setRegisterWindow(writer, reader, WINDOW_ID_CONFIGURATION);
}

async function ensureSession(
  port: SerialPort,
  baudRate: number,
  log: ReturnType<typeof createLog>,
): Promise<SerialSession> {
  if (activeSession && activeSession.port !== port) {
    await closeActiveSession();
  }

  if (!activeSession) {
    activeSession = { port, baudRate };
  }

  const session = activeSession;
  session.port = port;

  const needsReopen =
    !port.readable ||
    !port.writable ||
    session.baudRate !== baudRate;

  if (needsReopen) {
    await stopDrain(session);
    try {
      if (port.readable || port.writable) {
        await port.close();
      }
    } catch {
      // ignore close errors
    }

    try {
      await port.open({
        baudRate,
        dataBits: 8,
        stopBits: 1,
        parity: 'none',
        flowControl: 'none',
        bufferSize: 8192,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to open port';
      log(`Failed to open serial port: ${message}`, 'stderr');
      throw error instanceof Error ? error : new Error(message);
    }
  }

  session.baudRate = baudRate;
  startDrain(session, log);

  return session;
}

async function closeActiveSession(): Promise<void> {
  if (!activeSession) {
    return;
  }

  const session = activeSession;
  activeSession = null;

  await stopDrain(session);

  try {
    if (session.port.readable || session.port.writable) {
      await session.port.close();
    }
  } catch {
    // ignore
  }
}

function startDrain(session: SerialSession, log?: ReturnType<typeof createLog>): void {
  if (!session.port.readable || session.drainAbort) {
    return;
  }

  const abort = new AbortController();
  session.drainAbort = abort;

  const run = async () => {
    let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;
    try {
      const stream = session.port.readable;
      if (!stream) {
        return;
      }

      reader = stream.getReader();
      while (!abort.signal.aborted) {
        const { done } = await reader.read();
        if (done) {
          break;
        }
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        return;
      }
      if (error instanceof DOMException && error.name === 'NotAllowedError') {
        return;
      }
      if (!(error instanceof DOMException && error.name === 'AbortError')) {
        log?.(
          `Background drain loop stopped: ${
            error instanceof Error ? error.message : String(error)
          }`,
          'stderr',
        );
      }
    } finally {
      if (reader) {
        try {
          reader.releaseLock();
        } catch {
          // ignore lock release errors
        }
      }
    }
  };

  session.drainTask = run().finally(() => {
    session.drainAbort = undefined;
    session.drainTask = undefined;
  });
}

async function stopDrain(session: SerialSession): Promise<void> {
  if (session.drainAbort) {
    session.drainAbort.abort();
  }
  if (session.drainTask) {
    try {
      await session.drainTask;
      } catch {
        // ignore
      }
    }
  session.drainAbort = undefined;
  session.drainTask = undefined;
}

async function withSessionIO<T>(
  session: SerialSession,
  log: ReturnType<typeof createLog>,
  handler: (
    writer: WritableStreamDefaultWriter<Uint8Array>,
    reader: ReadableStreamDefaultReader<Uint8Array>,
  ) => Promise<T>,
): Promise<T> {
  await stopDrain(session);

  if (!session.port.readable || !session.port.writable) {
    try {
      if (session.port.readable || session.port.writable) {
        try {
          await session.port.close();
        } catch {
          // ignore
        }
      }

      await session.port.open({
        baudRate: session.baudRate,
        dataBits: 8,
        stopBits: 1,
        parity: 'none',
        flowControl: 'none',
        bufferSize: 8192,
      });
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : 'Failed to open serial port for command sequence.';
      log(`Port reconnection failed: ${message}`, 'stderr');
      throw error instanceof Error ? error : new Error(message);
    }
  }

  if (!session.port.readable || !session.port.writable) {
    throw new Error('Serial port is not open or readable/writable streams unavailable');
  }

  const writer = session.port.writable!.getWriter();
  const reader = session.port.readable!.getReader();

  try {
    return await handler(writer, reader);
  } finally {
    try {
      writer.releaseLock();
    } catch {
      // ignore lock release errors
    }
    try {
      reader.releaseLock();
    } catch {
      // ignore lock release errors
    }
    startDrain(session, log);
  }
}

async function performFlashTest(
  writer: WritableStreamDefaultWriter<Uint8Array>,
  reader: ReadableStreamDefaultReader<Uint8Array>,
  log: ReturnType<typeof createLog>,
): Promise<void> {
  log('Running flash test');
  await setRegisterWindow(writer, reader, WINDOW_ID_METADATA);
  await sendCommands(writer, reader, [[0, 0x83, 0x08, 0x0d]]);

  let completed = false;
  const start = Date.now();
  while (Date.now() - start < FLASH_TEST_TIMEOUT_MS) {
    await setRegisterWindow(writer, reader, WINDOW_ID_METADATA);
    const response = await sendCommand(writer, reader, [4, MSC_CTRL_REGISTER, 0x00, 0x0d]);
    if (response.length >= 4) {
      const high = response[1] ?? 0;
      const low = response[2] ?? 0;
      const value = (high << 8) | low;
      if ((value & 0x0400) === 0) {
        log(`FLASH_TEST bit cleared (MSC_CTRL=0x${value.toString(16).padStart(4, '0')})`);
        completed = true;
        break;
      }
    }
    await delay(FLASH_TEST_POLL_INTERVAL_MS);
  }

  if (!completed) {
    throw new Error('Flash test timed out before completion.');
  }

  const diagResponse = await sendCommands(writer, reader, [
    [0, WINDOW_REGISTER, WINDOW_ID_CONFIGURATION, 0x0d],
    [4, DIAG_STAT1_REGISTER, 0x00, 0x0d],
  ]);
  if (diagResponse.length >= 4) {
    const diagLow = diagResponse[2] ?? 0;
    if ((diagLow & 0x04) !== 0) {
      throw new Error('FLASH_ERR flag set after flash test.');
    }
  }
  log('Flash test completed with no FLASH_ERR flag.');
}

async function performSoftwareReset(
  writer: WritableStreamDefaultWriter<Uint8Array>,
  reader: ReadableStreamDefaultReader<Uint8Array>,
  log: ReturnType<typeof createLog>,
): Promise<void> {
  log('Issuing software reset (SOFT_RST)');
  await setRegisterWindow(writer, reader, WINDOW_ID_METADATA);
  await sendCommands(writer, reader, [[0, 0x8a, 0x80, 0x0d]]);

  log('Waiting for sensor to signal ready state...');
  const ready = await waitForSensorReady(writer, reader, log);
  if (!ready) {
    throw new Error('Timed out waiting for sensor readiness after software reset.');
  }
  log('Sensor reports ready state after software reset.');
}

async function waitForSensorReady(
  writer: WritableStreamDefaultWriter<Uint8Array>,
  reader: ReadableStreamDefaultReader<Uint8Array>,
  log: ReturnType<typeof createLog>,
): Promise<boolean> {
  const start = Date.now();
  while (Date.now() - start < READY_TIMEOUT_MS) {
    await setRegisterWindow(writer, reader, WINDOW_ID_METADATA);
    const response = await sendCommand(writer, reader, [4, GLOB_CMD_REGISTER, 0x00, 0x0d]);
    if (response.length >= 4) {
      const high = response[1] ?? 0;
      const low = response[2] ?? 0;
      const value = (high << 8) | low;
      if ((value & 0x0400) === 0) {
        return true;
      }
    }
    await delay(READY_POLL_INTERVAL_MS);
  }
  log('Timed out waiting for sensor ready state', 'stderr');
  return false;
}

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

