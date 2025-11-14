import { useEffect, useMemo, useState } from 'react';
import { Header } from './components/Header';
import { ConfigurationPanel } from './components/ConfigurationPanel';
import { InfoPanel } from './components/InfoPanel';
import { StatusBar } from './components/StatusBar';

function App() {
  const detectMobileDevice = useMemo(
    () => () => {
      if (typeof navigator === 'undefined') {
        return false;
      }

      const nav = navigator as Navigator & { userAgentData?: { mobile?: boolean } };
      if (nav.userAgentData?.mobile !== undefined) {
        return nav.userAgentData.mobile;
      }

      const ua = nav.userAgent || '';
      const mobileRegex = /android|iphone|ipad|ipod|blackberry|iemobile|opera mini|mobile/i;
      if (mobileRegex.test(ua)) {
        return true;
      }

      return nav.maxTouchPoints > 1;
    },
    [],
  );

  const [isMobileDevice] = useState<boolean>(() => detectMobileDevice());

  const [viewportWidth, setViewportWidth] = useState<number>(() =>
    typeof window !== 'undefined' ? window.innerWidth : 0,
  );

  useEffect(() => {
    const handleResize = () => {
      if (typeof window === 'undefined') {
        return;
      }
      setViewportWidth(window.innerWidth);
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  const shouldShowMobileWarning = isMobileDevice && viewportWidth < 1024;

  if (shouldShowMobileWarning) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-900 text-white text-center px-6">
        <div className="max-w-md space-y-4">
          <span className="inline-flex items-center justify-center rounded-full bg-orange-500/20 text-orange-300 px-4 py-1 text-sm font-semibold uppercase tracking-wide">
            Desktop Required
          </span>
          <h1 className="text-2xl font-semibold">Use a Laptop or Desktop Browser</h1>
          <p className="text-base text-gray-200">
            Sensor configuration requires the Zenith Helper application running on the same computer, and a desktop browser to control it.
          </p>
          <p className="text-sm text-gray-400">
            Please reopen this page on a laptop or desktop. Once there, install the helper app and continue the configuration steps.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 font-['Aldrich']">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <ConfigurationPanel />
          </div>

          <div>
            <InfoPanel />
          </div>
        </div>
      </main>

      <StatusBar />
    </div>
  );
}

export default App;
