declare global {
  interface SerialPortInfo {
    usbVendorId?: number;
    usbProductId?: number;
  }

  interface SerialPort {
    readonly readable: ReadableStream<Uint8Array> | null;
    readonly writable: WritableStream<Uint8Array> | null;
    open(options: SerialOptions): Promise<void>;
    close(): Promise<void>;
    getInfo?(): SerialPortInfo;
  }

  interface SerialPortFilter {
    usbVendorId?: number;
    usbProductId?: number;
  }

  interface SerialOptions {
    baudRate: number;
    dataBits?: number;
    stopBits?: number;
    parity?: 'none' | 'even' | 'odd';
    bufferSize?: number;
    flowControl?: 'none' | 'hardware';
  }

  interface SerialPortRequestOptions {
    filters: SerialPortFilter[];
  }

  interface Serial {
    getPorts(): Promise<SerialPort[]>;
    requestPort(options?: SerialPortRequestOptions): Promise<SerialPort>;
  }

  interface Navigator {
    serial?: Serial;
  }
}

export {};

