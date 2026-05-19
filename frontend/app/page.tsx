'use client';

import { useState } from 'react';
import { Header, Search, StatCard, ItemCard } from '@/components';

export default function Home() {
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearch = (query: string) => {
    setSearchQuery(query);
    // TODO: Implement search functionality
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      {/* Hero Section */}
      <div className="bg-gradient-to-b from-blue-50 to-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-4">
              CS2 Market Intelligence
            </h1>
            <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
              Track, analyze, and understand the Counter-Strike 2 in-game economy.
              Discover opportunities with real-time market data and predictive insights.
            </p>
          </div>

          {/* Search Bar */}
          <div className="max-w-2xl mx-auto">
            <Search onSearch={handleSearch} />
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        
        {/* Statistics Section */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12">
          <StatCard 
            title="Total Items"
            value="1,247"
            icon="📦"
          />
          <StatCard 
            title="Avg Price 7d"
            value="$45.32"
            change={2.5}
            icon="📈"
          />
          <StatCard 
            title="Market Volume"
            value="856K"
            change={-1.2}
            icon="📊"
          />
          <StatCard 
            title="Trending Now"
            value="23"
            icon="🔥"
          />
        </div>

        {/* Quick Navigation */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <div className="bg-white rounded-lg shadow p-6 hover:shadow-md transition cursor-pointer">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">📈 Trending Items</h3>
            <p className="text-gray-600 text-sm">
              Discover the hottest skins and cases gaining momentum
            </p>
          </div>
          <div className="bg-white rounded-lg shadow p-6 hover:shadow-md transition cursor-pointer">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">💡 Opportunities</h3>
            <p className="text-gray-600 text-sm">
              Find undervalued, overheated, and momentum-driven items
            </p>
          </div>
          <div className="bg-white rounded-lg shadow p-6 hover:shadow-md transition cursor-pointer">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">📅 Market Events</h3>
            <p className="text-gray-600 text-sm">
              Track tournaments, operations, and market-moving announcements
            </p>
          </div>
        </div>

        {/* Featured Items */}
        <div className="mb-12">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Featured Items</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <ItemCard
                key={i}
                itemId={`item-${i}`}
                name={`Sample Item ${i}`}
                type={['skin', 'case', 'sticker'][i % 3] as any}
                currentPrice={Math.random() * 100 + 10}
                priceChange7d={(Math.random() - 0.5) * 20}
                trendDirection={['bullish', 'neutral', 'bearish'][i % 3] as any}
              />
            ))}
          </div>
        </div>

        {/* Features Section */}
        <div className="bg-white rounded-lg shadow p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Platform Features</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">📊 Price History Charts</h3>
              <p className="text-gray-600">
                View complete price history from item release date or earliest recorded data
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">🎯 Trend Analysis</h3>
              <p className="text-gray-600">
                Get bullish, neutral, or bearish signals with confidence scores
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">🔮 Price Prediction</h3>
              <p className="text-gray-600">
                Forecast short-term price ranges using moving averages and regression
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">🎪 Event Tracking</h3>
              <p className="text-gray-600">
                Correlate market movements with tournaments, operations, and updates
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-gray-900 text-white mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div>
              <h3 className="font-semibold mb-4">CS2 Market Intelligence</h3>
              <p className="text-gray-400 text-sm">
                Analytics platform for Counter-Strike 2 in-game economy
              </p>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Quick Links</h3>
              <ul className="text-gray-400 text-sm space-y-2">
                <li><a href="#" className="hover:text-white transition">Items</a></li>
                <li><a href="#" className="hover:text-white transition">Opportunities</a></li>
                <li><a href="#" className="hover:text-white transition">Events</a></li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Resources</h3>
              <ul className="text-gray-400 text-sm space-y-2">
                <li><a href="#" className="hover:text-white transition">Documentation</a></li>
                <li><a href="#" className="hover:text-white transition">API Docs</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400 text-sm">
            <p>&copy; 2025 CS2 Market Intelligence. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

