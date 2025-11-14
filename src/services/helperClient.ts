const DEFAULT_BASE_URL = 'http://127.0.0.1:7421';
const TOKEN_HEADER = 'X-Zenith-Token';

export type HelperSensorType = 'vibration' | 'imu';

export interface HelperUpdateInfo {
  version: string;
  downloadUrl?: string;
  checksum?: string | null;
  releaseNotes?: string | null;
}

export interface HelperStatus {
  version: string;
  connected: boolean;
  port: string | null;
  baudRate: number;
  updateAvailable: HelperUpdateInfo | null;
}

export interface HelperUpdateDownload {
  version: string;
  path: string;
  bytes: number;
  checksumVerified?: boolean | null;
  updatesDir?: string;
}

export interface HelperPortInfo {
  device: string;
  description?: string;
  hwid?: string;
  manufacturer?: string;
  vid?: number;
  pid?: number;
  serialNumber?: string | null;
}

export interface HelperDetectionResult {
  success: boolean;
  product_id?: string;
  product_id_raw?: string;
  serial_number?: string;
  message?: string;
}

export interface HelperCommandResult {
  success: boolean;
  message: string;
  requires_restart?: boolean;
  warning?: string | null;
}

export class HelperClient {
  private baseUrl: string;
  private token: string;

  constructor(token: string, baseUrl: string = DEFAULT_BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this.token = token;
  }

  updateToken(token: string) {
    this.token = token;
  }

  private headers(): HeadersInit {
    return {
      'Content-Type': 'application/json',
      [TOKEN_HEADER]: this.token,
    };
  }

  static async pair(baseUrl: string): Promise<{ token: string }> {
    const sanitizedBase = baseUrl.replace(/\/+$/, '');
    const response = await fetch(`${sanitizedBase}/pair`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    const text = await response.text();
    const data = text ? JSON.parse(text) : {};
    if (!response.ok) {
      const message = data?.detail ?? response.statusText;
      throw new Error(message);
    }
    return data as { token: string };
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers: {
        ...(options.headers ?? {}),
        ...this.headers(),
      },
    });

    const text = await response.text();
    const data = text ? JSON.parse(text) : null;

    if (!response.ok) {
      const message = data?.detail ?? response.statusText;
      throw new Error(message);
    }

    return data as T;
  }

  status(platform?: string): Promise<HelperStatus> {
    const query = platform ? `?platform=${encodeURIComponent(platform)}` : '';
    return this.request<HelperStatus>(`/status${query}`, { method: 'GET' });
  }

  triggerUpdate(platform?: string): Promise<{ updateAvailable: HelperUpdateInfo | null }> {
    return this.request('/update', {
      method: 'POST',
      body: JSON.stringify(platform ? { platform } : {}),
    });
  }

  downloadUpdate(platform?: string): Promise<HelperUpdateDownload> {
    return this.request('/update/download', {
      method: 'POST',
      body: JSON.stringify(platform ? { platform } : {}),
    });
  }

  listPorts(): Promise<{ ports: HelperPortInfo[] }> {
    return this.request('/ports', { method: 'GET' });
  }

  connect(port: string, baudRate: number): Promise<{ connected: boolean; port: string; baudRate: number }> {
    return this.request('/connect', {
      method: 'POST',
      body: JSON.stringify({ port, baudRate }),
    });
  }

  disconnect(): Promise<{ connected: boolean }> {
    return this.request('/disconnect', { method: 'POST' });
  }

  detect(sensor: HelperSensorType): Promise<HelperDetectionResult> {
    return this.request('/detect', {
      method: 'POST',
      body: JSON.stringify({ sensor }),
    });
  }

  configure(sensor: HelperSensorType, payload: Record<string, unknown> = {}): Promise<HelperCommandResult> {
    return this.request('/configure', {
      method: 'POST',
      body: JSON.stringify({ sensor, ...payload }),
    });
  }

  exitAuto(sensor: HelperSensorType, persist = true): Promise<HelperCommandResult> {
    return this.request('/exit-auto', {
      method: 'POST',
      body: JSON.stringify({ sensor, persist }),
    });
  }

  fullReset(sensor: HelperSensorType): Promise<HelperCommandResult> {
    return this.request('/reset', {
      method: 'POST',
      body: JSON.stringify({ sensor }),
    });
  }

  openLogStream(onMessage: (event: MessageEvent) => void): WebSocket {
    const wsUrl = this.baseUrl.replace(/^http/, 'ws');
    const tokenParam = this.token ? `?token=${encodeURIComponent(this.token)}` : '';
    const socket = new WebSocket(`${wsUrl}/logs${tokenParam}`);
    socket.addEventListener('message', onMessage);
    return socket;
  }
}

