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

const EASE: [number, number, number, number] = [0.16, 1, 0.3, 1];

function formatCurrency(value: number) {
  return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
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
      if (!user) { setLoading(false); return; }

      setLoading(true);
      try {
        const data = await getInventory();
        if (data.error) {
          if (data.error === 'unauthorized') {
            setError('Please sign in to view your portfolio');
          } else {
            setError('Make sure your Steam profile and inventory are set to public.');
          }
        } else {
          setItems(data.items || []);
          setTotalValue(data.total_value || 0);
        }
      } catch {
        setError('An unexpected error occurred');
      } finally {
        setLoading(false);
      }
    }

    fetchPortfolio();
  }, [user, userLoading]);

  if (userLoading || loading) {
    return (
      <div className="min-h-screen bg-background-primary">
        <Header />
        <div className="flex flex-col items-center justify-center h-[60vh]">
          <div className="relative w-12 h-12 mb-4">
            <div className="absolute inset-0 rounded-full border-2 border-border" />
            <div className="absolute inset-0 rounded-full border-2 border-accent-primary border-t-transparent animate-spin" />
          </div>
          <p className="text-secondary text-sm">Loading your inventory...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-background-primary">
        <Header />
        <div className="max-w-4xl mx-auto px-6 py-20 text-center">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ ease: EASE }}>
            <span className="font-data text-[10px] font-bold uppercase tracking-[0.3em] text-accent-primary mb-3 block">
              PORTFOLIO
            </span>
            <h1 className="text-4xl font-bold mb-6 text-primary tracking-tight">Your Portfolio</h1>
            <p className="text-xl mb-10 max-w-2xl mx-auto text-secondary leading-relaxed">
              Sign in with your Steam account to analyze your CS2 inventory,
              track performance, and discover market opportunities.
            </p>
            <a
              href={getLoginUrl()}
              className="inline-flex items-center gap-3 px-8 py-4 rounded-sm text-sm font-bold uppercase tracking-widest transition-all duration-200 bg-accent text-background-primary hover:bg-brand-hover active:scale-[0.97]"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M11.979 0C5.678 0 .511 4.86.022 11.037l6.432 2.654c.545-.371 1.203-.59 1.912-.59.063 0 .125.004.188.006l2.83-4.146V8.92c0-2.607 2.113-4.72 4.72-4.72 2.607 0 4.72 2.113 4.72 4.72 0 2.607-2.113 4.72-4.72 4.72-.173 0-.341-.013-.506-.035l-4.14 2.831c.002.063.006.125.006.188 0 2.114-1.714 3.828-3.828 3.828-1.55 0-2.891-.918-3.504-2.236L0 15.352c.866 4.887 5.152 8.648 10.285 8.648 5.756 0 10.422-4.666 10.422-10.422C20.707 7.822 16.784 3.322 11.979 0zm2.741 12.01c-1.706 0-3.091-1.385-3.091-3.09 0-1.706 1.385-3.091 3.091-3.091 1.706 0 3.091 1.385 3.091 3.091 0 1.705-1.385 3.09-3.091 3.09zm-3.091-3.09c0 .416.084.81.233 1.168l-2.73 3.999c-.198-.016-.399-.026-.603-.026-1.127 0-2.146.486-2.854 1.261l-5.32-2.193c.312-4.143 3.49-7.447 7.554-8.156.002.016.006.033.006.05v.001zM10.285 17.548c0 1.312-1.063 2.375-2.375 2.375-1.312 0-2.375-1.063-2.375-2.375s1.063-2.375 2.375-2.375c.063 0 .125.004.188.006l2.193-3.193v.001c.416.486 1.035.789 1.724.789h.001c-.149-.358-.233-.752-.233-1.168s.084-.81.233-1.168h-.001c-.689 0-1.308.303-1.724.789l-2.193-3.193c-.063.002-.125.006-.188.006z" />
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
      <div className="min-h-screen bg-background-primary">
        <Header />
        <div className="max-w-4xl mx-auto px-6 py-20 text-center">
          <h1 className="text-2xl font-bold mb-4 text-primary">Something went wrong</h1>
          <p className="mb-8 text-secondary">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-6 py-2 rounded-sm text-sm font-bold uppercase tracking-widest bg-accent text-background-primary hover:bg-brand-hover transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background-primary">
      <Header />

      <div className="max-w-6xl mx-auto px-6 py-10">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: EASE }}
          className="mb-10 flex flex-col md:flex-row md:items-end md:justify-between gap-4"
        >
          <div>
            <span className="font-data text-[10px] font-bold uppercase tracking-[0.3em] text-accent-primary mb-3 block">
              PORTFOLIO
            </span>
            <h1 className="text-4xl font-bold mb-2 text-primary tracking-tight">Portfolio</h1>
            <div className="flex items-center gap-2 text-sm text-secondary">
              <span className="px-2 py-0.5 rounded-sm bg-background-tertiary font-data text-xs">
                Steam: {user.steam_id}
              </span>
              <span>Analyzing {items.length} unique items</span>
            </div>
          </div>
          <button
            onClick={() => window.location.reload()}
            className="text-xs font-bold uppercase tracking-[0.2em] text-accent-primary hover:text-brand-hover transition-colors"
          >
            Refresh Inventory
          </button>
        </motion.div>

        {/* Stats */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.5, ease: EASE }}
          className="grid grid-cols-1 md:grid-cols-4 gap-5 mb-10"
        >
          <div className="md:col-span-2">
            <StatCard
              label="Estimated Inventory Value"
              value={totalValue}
              unit="$"
              annotation="TOTAL"
            />
          </div>
          <StatCard
            label="Total Items"
            value={items.reduce((sum, item) => sum + item.quantity, 0)}
            annotation="QTY"
          />
          <StatCard
            label="Unique Items"
            value={items.length}
            annotation="SKUS"
          />
        </motion.div>

        {/* Inventory Table */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.45, ease: EASE }}
          className="overflow-x-auto rounded-sm border border-border bg-surface shadow-sm"
        >
          <table className="w-full text-sm min-w-[640px]">
            <thead>
              <tr className="bg-background-tertiary border-b border-border">
                <th className="px-6 py-5 text-left text-xs font-semibold uppercase tracking-wide text-secondary">Item</th>
                <th className="px-6 py-5 text-left text-xs font-semibold uppercase tracking-wide text-secondary">Type</th>
                <th className="px-6 py-5 text-right text-xs font-semibold uppercase tracking-wide text-secondary">Qty</th>
                <th className="px-6 py-5 text-right text-xs font-semibold uppercase tracking-wide text-secondary">Current Price</th>
                <th className="px-6 py-5 text-right text-xs font-semibold uppercase tracking-wide text-secondary">Total Value</th>
                <th className="px-6 py-5 text-center text-xs font-semibold uppercase tracking-wide text-secondary">Market</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, idx) => {
                const totalItemValue = item.current_price ? (item.current_price * item.quantity) : 0;

                return (
                  <motion.tr
                    key={item.id}
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.25 + idx * 0.02 }}
                    className="stripe-row cursor-pointer group"
                    style={{ backgroundColor: hoveredRow === item.id ? 'var(--background-tertiary)' : 'transparent' }}
                    onMouseEnter={() => setHoveredRow(item.id)}
                    onMouseLeave={() => setHoveredRow(null)}
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        {item.image_url ? (
                          <img src={item.image_url} alt={item.name} className="w-10 h-8 object-contain rounded-sm" />
                        ) : (
                          <div className="w-10 h-8 rounded-sm bg-background-tertiary" />
                        )}
                        <span className="font-medium text-primary group-hover:text-accent-primary transition-colors">
                          {item.name}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-left text-xs uppercase tracking-wide text-secondary">
                      {item.type}
                    </td>
                    <td className="px-6 py-4 text-right font-data text-secondary">
                      {item.quantity}
                    </td>
                    <td className="px-6 py-4 text-right font-data text-primary">
                      {item.current_price ? formatCurrency(item.current_price) : 'N/A'}
                    </td>
                    <td className="px-6 py-4 text-right font-data font-medium text-primary">
                      {totalItemValue > 0 ? formatCurrency(totalItemValue) : 'N/A'}
                    </td>
                    <td className="px-6 py-4 text-center">
                      <Link
                        href={`/market?q=${encodeURIComponent(item.market_hash_name)}`}
                        className="text-xs font-bold uppercase tracking-widest text-accent-primary hover:text-brand-hover transition-colors"
                      >
                        Analyze &rarr;
                      </Link>
                    </td>
                  </motion.tr>
                );
              })}
            </tbody>
          </table>
        </motion.div>

        {/* Empty State */}
        {items.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="text-center py-16"
          >
            <div className="w-16 h-16 rounded-sm border border-border bg-background-secondary mx-auto mb-6 flex items-center justify-center">
              <svg className="w-8 h-8 text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
              </svg>
            </div>
            <p className="mb-4 text-base text-secondary">No items found in your public CS2 inventory</p>
            <p className="text-sm mb-6 max-w-md mx-auto text-tertiary">
              Make sure your Steam profile and inventory are set to &ldquo;Public&rdquo; in your privacy settings.
            </p>
            <Link href="/market" className="text-xs font-bold uppercase tracking-widest text-accent-primary hover:text-brand-hover transition-colors">
              Browse market &rarr;
            </Link>
          </motion.div>
        )}
      </div>
    </div>
  );
}
