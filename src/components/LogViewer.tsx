import { LogEntry } from '../types';
import { Terminal } from 'lucide-react';

interface LogViewerProps {
  logs: LogEntry[];
}

export function LogViewer({ logs }: LogViewerProps) {
  if (logs.length === 0) {
    return null;
  }

  return (
    <div className="mt-6 bg-gray-900 rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center space-x-2">
          <Terminal className="h-4 w-4 text-white" />
          <span className="text-sm font-medium text-gray-300">Output Logs</span>
        </div>
        <span className="text-xs text-gray-500">{logs.length} entries</span>
      </div>
      <div className="p-4 max-h-96 overflow-y-auto">
        <div className="font-mono text-sm space-y-1">
          {logs.map((log, index) => (
            <div
              key={index}
              className={`text-white`}
            >
              <span className="text-white mr-2">
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
              {log.message}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
