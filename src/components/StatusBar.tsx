import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle, XOctagon } from 'lucide-react';
import { HelperClient } from '../services/helperClient';
import { getHelperDownload } from '../utils/helperDownloads';

const PLATFORM =
  typeof navigator !== 'undefined'
    ? (navigator as Navigator & { userAgentData?: { platform?: string } }).userAgentData?.platform ??
      navigator.platform ??
      'unknown'
    : 'unknown';
const STATUS_POLL_INTERVAL = 10000;

type HelperState =
  | { level: 'info'; message: string }
  | { level: 'warn'; message: string }
  | { level: 'error'; message: string; showDownload?: boolean };

export function StatusBar() {
  const [helperState, setHelperState] = useState<HelperState>({
    level: 'warn',
    message: 'Waiting for helper pairing. Launch the helper app to connect.',
  });
  const helperDownload = getHelperDownload(PLATFORM);

  useEffect(() => {
    let cancelled = false;

    const pollStatus = async () => {
      const token = localStorage.getItem('helperToken') ?? '';
      const baseUrl = localStorage.getItem('helperBaseUrl') ?? 'http://127.0.0.1:7421';

      if (!token) {
        if (!cancelled) {
          setHelperState({
            level: 'warn',
            message: 'Waiting for helper pairing. Launch the helper app to connect.',
          });
        }
      return;
    }

      const client = new HelperClient(token, baseUrl);

      try {
        const status = await client.status(PLATFORM);
        if (cancelled) {
          return;
        }
        if (status.connected && status.port) {
          setHelperState({
            level: 'info',
            message: `Helper connected to ${status.port} @ ${status.baudRate.toLocaleString()} bps.`,
          });
        } else {
          setHelperState({
            level: 'warn',
            message: 'Helper ready — select a port and click “Connect & Detect Sensor”.',
          });
        }
      } catch (error) {
        if (!cancelled) {
          console.warn('Helper status polling failed', error);
          setHelperState({
            level: 'error',
            message: 'Helper not detected. Install and start the helper application.',
            showDownload: true,
          });
        }
      }
    };

    pollStatus();
    const interval = window.setInterval(pollStatus, STATUS_POLL_INTERVAL);
    const handleStorage = () => pollStatus();
    window.addEventListener('storage', handleStorage);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
      window.removeEventListener('storage', handleStorage);
    };
  }, []);

  const bgClass =
    helperState.level === 'info' ? 'bg-[#085f63]' : helperState.level === 'warn' ? 'bg-yellow-600' : 'bg-red-600';
  const Icon = helperState.level === 'info' ? CheckCircle : helperState.level === 'warn' ? AlertTriangle : XOctagon;

  return (
    <div className={`fixed bottom-0 left-0 right-0 px-4 py-2 text-sm ${bgClass} text-white`}>
      <div className="max-w-7xl mx-auto flex items-center space-x-2">
        <Icon className="h-4 w-4 text-white" />
        <span>{helperState.message}</span>
        {helperState.level === 'error' && helperState.showDownload && (
          <a className="underline text-white ml-2" href={helperDownload.url} target="_blank" rel="noreferrer">
            {helperDownload.label}
          </a>
        )}
      </div>
    </div>
  );
}
