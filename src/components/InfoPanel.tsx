import { ClipboardList, Server, Monitor, BookOpen, SlidersHorizontal } from 'lucide-react';

const steps = [
  {
    icon: <ClipboardList className="h-4 w-4 text-[#085f63]" />,
    title: 'Check connections',
    items: [
      'Connect the Epson logger to your PC using the USB cable.',
      'Ensure the sensor is powered on and the cable is secure.',
    ],
  },
  {
    icon: <Server className="h-4 w-4 text-[#085f63]" />,
    title: 'Install & start the helper',
    items: [
      'Install the Zenith Helper app on Windows, macOS, or Linux.',
      'Launch the helper — copy the token it prints and paste it in the portal.',
      'Keep the helper running while you configure sensors.',
    ],
  },
  {
    icon: <SlidersHorizontal className="h-4 w-4 text-[#085f63]" />,
    title: 'Choose your sensor',
    items: [
      'Click “Select & Connect” once the helper token is set.',
      'Pick your sensor type and, for IMU, choose a sampling rate.',
      'Use “Refresh Ports” if the device list is empty.',
    ],
  },
  {
    icon: <Monitor className="h-4 w-4 text-[#085f63]" />,
    title: 'Pair & configure',
    items: [
      'Keep the default baud rate (460800) unless support asks for a change.',
      'Click “Start Configuration” and watch the status banner turn green.',
      'Wait for the status banner to confirm success.',
    ],
  },
  {
    icon: <BookOpen className="h-4 w-4 text-[#085f63]" />,
    title: 'After configuration',
    items: [
      'Restart the sensor to start streaming data and remember the settings.',
      'Use “Exit Auto Mode” to stop streaming without power cycling.',
      'Use “Factory Reset” only when you need to restore defaults.',
    ],
  },
];

export function InfoPanel() {
  return (
    <div className="bg-white rounded-lg shadow-md p-3">
      <h2 className="text-lg font-semibold text-[#085f63] mb-4">Quick Start Guide</h2>
      <p className="text-sm text-gray-800 mb-4">
        Follow these steps to configure the Epson M-A542VR1 vibration sensor or M-G552PR80 IMU into Auto Mode.
      </p>

      <div className="space-y-4">
        {steps.map((step) => (
          <div key={step.title} className="border border-gray-200 rounded-lg p-3">
            <div className="flex items-center space-x-2 mb-2">
              {step.icon}
              <h3 className="text-sm font-semibold text-[#085f63]">{step.title}</h3>
            </div>
            <ul className="list-disc list-inside text-sm text-gray-800 space-y-0.5">
              {step.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="mt-4 rounded-lg border border-[#0a7a80]/30 bg-[#e0f5f4] p-4">
        <h3 className="text-sm font-semibold text-[#085f63] mb-1">Need help?</h3>
        <p className="text-sm text-gray-800">
          Visit{' '}
          <a href="/help/" className="font-semibold text-[#085f63] underline">
            Help
          </a>{' '}
          for troubleshooting tips. You can also reach us at{' '}
          <a
            href="mailto:contactus@zenithtek.in"
            className="font-semibold text-[#085f63] underline"
          >
            contactus@zenithtek.in
          </a>{' '}
          or call{' '}
          <a href="tel:+918500807481" className="font-semibold text-[#085f63] underline">
            +91 85008 07481
          </a>
          .
        </p>
      </div>
    </div>
  );
}
