export type SensorType = 'vibration' | 'imu';

export interface ImuSamplingOption {
  id: string;
  rate: number;
  label: string;
  doutValue: number;
  filterValue: number;
  filterLabel: string;
  note?: string;
  isDefault?: boolean;
}

export const IMU_SAMPLING_OPTIONS: ImuSamplingOption[] = [
  { id: '2000', rate: 2000, label: '2000 sps', doutValue: 0x00, filterValue: 0b00111, filterLabel: 'Moving average filter, TAP = 128', note: 'Requires 921600 baud to avoid bandwidth overflow.' },
  { id: '1000', rate: 1000, label: '1000 sps', doutValue: 0x01, filterValue: 0b00111, filterLabel: 'Moving average filter, TAP = 128', note: 'Works best at 460800 baud or higher; 921600 recommended for headroom.' },
  { id: '500', rate: 500, label: '500 sps', doutValue: 0x02, filterValue: 0b00111, filterLabel: 'Moving average filter, TAP = 128' },
  { id: '250', rate: 250, label: '250 sps', doutValue: 0x04, filterValue: 0b00111, filterLabel: 'Moving average filter, TAP = 128' },
  { id: '125', rate: 125, label: '125 sps', doutValue: 0x06, filterValue: 0b00111, filterLabel: 'Moving average filter, TAP = 128', isDefault: true },
  { id: '62.5', rate: 62.5, label: '62.5 sps', doutValue: 0x09, filterValue: 0b00111, filterLabel: 'Moving average filter, TAP = 128' },
  { id: '31.25', rate: 31.25, label: '31.25 sps', doutValue: 0x0c, filterValue: 0b00111, filterLabel: 'Moving average filter, TAP = 128' },
  { id: '15.625', rate: 15.625, label: '15.625 sps', doutValue: 0x0f, filterValue: 0b00111, filterLabel: 'Moving average filter, TAP = 128' },
];

export interface SensorProfile {
  label: string;
  model: string;
  summary: string;
  defaultBaudRate: number;
  baudRates: number[];
}

export const SENSOR_PROFILES: Record<SensorType, SensorProfile> = {
  vibration: {
    label: 'Vibration Sensor',
    model: 'Epson M-A542VR1',
    summary: ' ',
    defaultBaudRate: 460800,
    baudRates: [230400, 460800, 921600],
  },
  imu: {
    label: 'IMU Sensor',
    model: 'Epson M-G552PR80',
    summary: ' ',
    defaultBaudRate: 460800,
    baudRates: [230400, 460800, 921600],
  },
};

export const PRODUCT_ID_SENSOR_LOOKUP: Record<string, SensorType> = {
  'M-A542VR1': 'vibration',
  A342VD10: 'vibration',
  'M-G552PR80': 'imu',
  G365PDF1: 'imu',
};

