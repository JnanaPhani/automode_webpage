import { useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle } from 'lucide-react';
import { webSerialService } from '../services/webSerial';

export function StatusBar() {
  const [supported] = useState(webSerialService.isSupported());
  const [hasPermission, setHasPermission] = useState(false);

  useEffect(() => {
    if (!supported) {
      return;
    }

    let active = true;

    (async () => {
      try {
        const ports = await webSerialService.getSavedPorts();
        if (active) {
          setHasPermission(ports.length > 0);
        }
      } catch {
        // ignore
      }
    })();

    return () => {
      active = false;
    };
  }, [supported]);

  const Icon = supported ? CheckCircle : AlertTriangle;
  const bgClass = supported ? 'bg-[#085f63]' : 'bg-red-600';
  const text = supported
    ? hasPermission
      ? 'Web Serial ready — previously authorised device detected.'
      : 'Web Serial ready — select your sensor to begin.'
    : 'Web Serial is not supported in this browser.';

  return (
    <div className={`fixed bottom-0 left-0 right-0 px-4 py-2 text-sm ${bgClass} text-white`}>
      <div className="max-w-7xl mx-auto flex items-center space-x-2">
        <Icon className="h-4 w-4 text-white" />
        <span>{text}</span>
      </div>
    </div>
  );
}
