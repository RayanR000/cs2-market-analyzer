'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Header } from '@/components';
import StatCard from '@/components/StatCard';
import { useUser } from '@/lib/UserContext';
import { getInventory, getLoginUrl } from '@/lib/api';

interface InventoryItem {
  id: string;
  name: string;
  market_hash_name: string;
  quantity: number;
  current_price: number | null;
  image_url: string | null;
  type: string;
}

export default function PortfolioPage() {
  const { user, loading: userLoading } = useUser();
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [totalValue, setTotalValue] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredRow, setHoveredRow] = useState<string | null>(null);

  useEffect(() => {
    async function fetchPortfolio() {
      if (userLoading) return;
      if (!user) {
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        const data = await getInventory();
        if (data.error) {
          if (data.error === 'unauthorized') {
            setError('Please sign in to view your portfolio');
          } else {
            setError('Failed to fetch inventory. Make sure your Steam profile and inventory are public.');
          }
        } else {
          setItems(data.items || []);
          setTotalValue(data.total_value || 0);
        }
      } catch (err) {
        console.error('Error fetching inventory:', err);
        setError('An unexpected error occurred');
      } finally {
        setLoading(false);
      }
    }

    fetchPortfolio();
  }, [user, userLoading]);

  if (userLoading || loading) {
    return (
      <div className="min-h-screen" style={{ backgroundColor: 'var(--background-primary)' }}>
        <Header />
        <div className="flex flex-col items-center justify-center h-[60vh]">
          <div className="w-12 h-12 border-4 border-t-transparent rounded-full animate-spin mb-4" style={{ borderColor: 'var(--accent-primary)', borderTopColor: 'transparent' }} />
          <p style={{ color: 'var(--text-secondary)' }}>Loading your inventory...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen" style={{ backgroundColor: 'var(--background-primary)' }}>
        <Header />
        <div className="max-w-4xl mx-auto px-4 py-20 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h1 className="text-4xl font-bold mb-6" style={{ color: 'var(--text-primary)' }}>Your Portfolio</h1>
            <p className="text-xl mb-10 max-w-2xl mx-auto" style={{ color: 'var(--text-secondary)' }}>
              Sign in with your Steam account to analyze your CS2 inventory, track performance, and discover market opportunities.
            </p>
            <a 
              href={getLoginUrl()}
              className="inline-flex items-center gap-3 px-8 py-4 rounded-lg text-lg font-semibold transition-all hover:scale-105 active:scale-95"
              style={{ 
                backgroundColor: '#1b2838', 
                color: '#ffffff',
                boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.4)'
              }}
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M11.979 0C5.678 0 .511 4.86.022 11.037l6.432 2.654c.545-.371 1.203-.59 1.912-.59.063 0 .125.004.188.006l2.83-4.146V8.92c0-2.607 2.113-4.72 4.72-4.72 2.607 0 4.72 2.113 4.72 4.72 0 2.607-2.113 4.72-4.72 4.72-.173 0-.341-.013-.506-.035l-4.14 2.831c.002.063.006.125.006.188 0 2.114-1.714 3.828-3.828 3.828-1.55 0-2.891-.918-3.504-2.236L0 15.352c.866 4.887 5.152 8.648 10.285 8.648 5.756 0 10.422-4.666 10.422-10.422C20.707 7.822 16.784 3.322 11.979 0zm2.741 12.01c-1.706 0-3.091-1.385-3.091-3.09 0-1.706 1.385-3.091 3.091-3.091 1.706 0 3.091 1.385 3.091 3.091 0 1.705-1.385 3.09-3.091 3.09zm-3.091-3.09c0 .416.084.81.233 1.168l-2.73 3.999c-.198-.016-.399-.026-.603-.026-1.127 0-2.146.486-2.854 1.261l-5.32-2.193c.312-4.143 3.49-7.447 7.554-8.156.002.016.006.033.006.05v.001zM10.285 17.548c0 1.312-1.063 2.375-2.375 2.375-1.312 0-2.375-1.063-2.375-2.375s1.063-2.375 2.375-2.375c.063 0 .125.004.188.006l2.193-3.193v.001c.416.486 1.035.789 1.724.789h.001c-.149-.358-.233-.752-.233-1.168s.084-.81.233-1.168h-.001c-.689 0-1.308.303-1.724.789l-2.193-3.193c-.063.002-.125.006-.188.006z"/>
              </svg>
              Sign in with Steam
            </a>
          </motion.div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen" style={{ backgroundColor: 'var(--background-primary)' }}>
        <Header />
        <div className="max-w-4xl mx-auto px-4 py-20 text-center">
          <h1 className="text-2xl font-bold mb-4" style={{ color: 'var(--text-primary)' }}>Something went wrong</h1>
          <p className="mb-8" style={{ color: 'var(--text-secondary)' }}>{error}</p>
          <button 
            onClick={() => window.location.reload()}
            className="px-6 py-2 rounded font-medium"
            style={{ backgroundColor: 'var(--accent-primary)', color: 'white' }}
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--background-primary)' }}>
      <Header />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        {/* Header */}
        <div className="mb-10 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h1 className="text-4xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>Portfolio</h1>
            <div className="flex items-center gap-2">
              <span className="text-sm px-2 py-0.5 rounded" style={{ backgroundColor: 'var(--background-tertiary)', color: 'var(--text-secondary)' }}>
                Steam: {user.steam_id}
              </span>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Analyzing {items.length} unique items</p>
            </div>
          </div>
          <button 
            onClick={() => window.location.reload()}
            className="text-sm font-medium hover:underline"
            style={{ color: 'var(--accent-primary)' }}
          >
            Refresh Inventory
          </button>
        </div>

        {/* Portfolio Summary Stats */}
        <motion.div
          initial={{ opacity: 0, y: -15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, staggerChildren: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-4 gap-5 mb-10"
        >
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }} className="md:col-span-2">
            <StatCard
              label="Estimated Inventory Value"
              value={`$${totalValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
              highlight="primary"
            />
          </motion.div>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }}>
            <StatCard
              label="Total Items"
              value={items.reduce((sum, item) => sum + item.quantity, 0).toString()}
              highlight="secondary"
            />
          </motion.div>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}>
            <StatCard
              label="Unique Items"
              value={items.length.toString()}
            />
          </motion.div>
        </motion.div>

        {/* Portfolio Holdings Table */}
        <div
          style={{
            borderColor: 'var(--border)',
            borderWidth: '1px',
            borderRadius: '10px',
            overflow: 'hidden',
            backgroundColor: 'var(--surface)'
          }}
          className="overflow-x-auto shadow-md"
        >
          <table className="w-full text-sm">
            <thead>
              <tr
                style={{
                  borderBottomColor: 'var(--border)',
                  borderBottomWidth: '1px',
                  backgroundColor: 'var(--background-tertiary)'
                }}
              >
                <th className="px-6 py-5 text-left text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>Item</th>
                <th className="px-6 py-5 text-left text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>Type</th>
                <th className="px-6 py-5 text-right text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>Qty</th>
                <th className="px-6 py-5 text-right text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>Current Price</th>
                <th className="px-6 py-5 text-right text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>Total Value</th>
                <th className="px-6 py-5 text-center text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>Market</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, idx) => {
                const totalItemValue = item.current_price ? (item.current_price * item.quantity) : 0;

                return (
                  <motion.tr
                    key={item.id}
                    initial={{ opacity: 0, y: -5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    style={{
                      borderBottomColor: 'var(--divider)',
                      borderBottomWidth: '1px',
                      backgroundColor: hoveredRow === item.id ? 'var(--background-tertiary)' : 'transparent',
                      transition: 'background-color 0.2s ease'
                    }}
                    className="group cursor-pointer"
                    onMouseEnter={() => setHoveredRow(item.id)}
                    onMouseLeave={() => setHoveredRow(null)}
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        {item.image_url && (
                          <img src={item.image_url} alt={item.name} className="w-10 h-8 object-contain" />
                        )}
                        <span
                          className="font-medium transition-opacity"
                          style={{ color: hoveredRow === item.id ? 'var(--accent-primary)' : 'var(--text-primary)' }}
                        >
                          {item.name}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-left text-xs" style={{ color: 'var(--text-secondary)' }}>
                      {item.type}
                    </td>
                    <td className="px-6 py-4 text-right font-mono" style={{ color: 'var(--text-secondary)' }}>
                      {item.quantity}
                    </td>
                    <td className="px-6 py-4 text-right font-mono" style={{ color: 'var(--text-primary)' }}>
                      {item.current_price ? `$${item.current_price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'N/A'}
                    </td>
                    <td className="px-6 py-4 text-right font-mono font-medium" style={{ color: 'var(--accent-secondary)' }}>
                      {totalItemValue > 0 ? `$${totalItemValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'N/A'}
                    </td>
                    <td className="px-6 py-4 text-center">
                      <Link
                        href={`/market?q=${encodeURIComponent(item.market_hash_name)}`}
                        className="text-xs hover:underline"
                        style={{ color: 'var(--accent-primary)' }}
                      >
                        Analyze →
                      </Link>
                    </td>
                  </motion.tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {items.length === 0 && (
          <div className="text-center py-16" style={{ color: 'var(--text-secondary)' }}>
            <p className="mb-4 text-base">No items found in your public CS2 inventory</p>
            <p className="text-sm mb-6 max-w-md mx-auto">Make sure your Steam profile and inventory are set to &quot;Public&quot; in your privacy settings.</p>
            <Link href="/market" className="font-medium transition-opacity hover:opacity-75" style={{ color: 'var(--accent-primary)' }}>
              Browse market →
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
