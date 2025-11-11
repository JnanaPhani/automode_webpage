export function Header() {
  return (
    <header className="bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <img
              src="/app-icon.png"
              alt="App icon"
              className="h-12 w-12 rounded-lg object-contain"
            />
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                Epson Sensor Auto Start Portal
              </h1>
              <p className="text-sm text-gray-500">
                Configure sensors into Auto Mode
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <img
              src="/zenithtek-logo.png"
              alt="Zenith Tek logo"
              className="h-10 w-auto object-contain"
            />
          </div>
        </div>
      </div>
    </header>
  );
}
