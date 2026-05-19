'use client';

export default function Header() {
  return (
    <header className="bg-gradient-to-r from-blue-600 to-blue-800 text-white shadow-lg">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center">
              <span className="font-bold text-blue-600">CS</span>
            </div>
            <h1 className="text-2xl font-bold">CS2 Market Intelligence</h1>
          </div>
          <nav className="hidden md:flex gap-8">
            <a href="/" className="hover:text-blue-200 transition">Home</a>
            <a href="/items" className="hover:text-blue-200 transition">Items</a>
            <a href="/opportunities" className="hover:text-blue-200 transition">Opportunities</a>
          </nav>
        </div>
      </div>
    </header>
  );
}
