import { Header } from './components/Header';
import { ConfigurationPanel } from './components/ConfigurationPanel';
import { InfoPanel } from './components/InfoPanel';
import { StatusBar } from './components/StatusBar';

function App() {
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
