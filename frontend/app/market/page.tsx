'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Header } from '@/components';
import { getItems, getTrendingItems, getPriceHistory, PricePoint } from '@/lib/api';

type SortKey = 'name' | 'currentPrice' | 'priceChange24h' | 'volatility' | 'volume24h';

interface MarketRow {
  id: string;
  item_id: string;
  name: string;
  type: string;
  currentPrice: number | null;
  priceChange24h: number | null;
  volatility: number | null;
  volume24h: number | null;
}

interface TrendingRow {
  item_id: number;
  name: string;
  type: string;
  latest_price: number;
}

interface CatalogItem {
  id: number;
  item_id: string;
  name: string;
  type: string;
}

const TABLE_LIMIT = 20;

function summarizeHistory(history: PricePoint[]): Omit<MarketRow, 'id' | 'item_id' | 'name' | 'type'> {
  if (!history.length) {
    return { currentPrice: null, priceChange24h: null, volatility: null, volume24h: null };
  }

  const points = [...history].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );
  const latest = points[points.length - 1];
  const latestTs = new Date(latest.timestamp).getTime();
  const cutoff = latestTs - 24 * 60 * 60 * 1000;
  const windowPoints = points.filter(point => new Date(point.timestamp).getTime() >= cutoff);
  const comparisonPoints = windowPoints.length > 1 ? windowPoints : points.slice(-2);
  const first = comparisonPoints[0];
  const last = comparisonPoints[comparisonPoints.length - 1];

  const priceChange24h =
    first && last && first.price > 0
      ? ((last.price - first.price) / first.price) * 100
      : null;

  const volumes = windowPoints.length ? windowPoints : points.slice(-2);
  const volume24h = volumes.reduce((sum, point) => sum + (point.volume ?? 0), 0) || null;

  const returns: number[] = [];
  for (let i = 1; i < points.length; i += 1) {
    const previous = points[i - 1].price;
    const current = points[i].price;
    if (previous > 0) {
      returns.push((current - previous) / previous);
    }
  }

  let volatility: number | null = null;
  if (returns.length > 1) {
    const mean = returns.reduce((sum, value) => sum + value, 0) / returns.length;
    const variance = returns.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / returns.length;
    volatility = Math.sqrt(variance) * 100;
  }

  return { currentPrice: latest.price, priceChange24h, volatility, volume24h };
}

function formatCurrency(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return '\u2014';
  return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatPercent(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return '\u2014';
  return `${value > 0 ? '+' : ''}${value.toFixed(1)}%`;
}

function formatVolume(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return '\u2014';
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return `${value.toFixed(0)}`;
}

export default function MarketPage() {
  const [items, setItems] = useState<MarketRow[]>([]);
  const [trending, setTrending] = useState<TrendingRow[]>([]);
  const [sortBy, setSortBy] = useState<SortKey>('currentPrice');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [searchQuery, setSearchQuery] = useState('');
  const [hoveredRow, setHoveredRow] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadMarketData() {
      setIsLoading(true);
      setError(null);

      try {
        const [itemsResponse, trendingResponse] = await Promise.all([
          getItems(undefined, 0, TABLE_LIMIT),
          getTrendingItems(6),
        ]);

        const catalogItems = Array.isArray(itemsResponse) ? itemsResponse as CatalogItem[] : [];
        const trendingItems = Array.isArray(trendingResponse) ? trendingResponse as CatalogItem[] : [];

        const summaries = await Promise.all(
          catalogItems.map(async (item: CatalogItem) => {
            try {
              const historyData = await getPriceHistory(item.item_id, 30, 0, 500);
              const historyPoints = Array.isArray(historyData) ? historyData as PricePoint[] : [];
              const summary = summarizeHistory(historyPoints);
              return { id: String(item.id), item_id: item.item_id, name: item.name, type: item.type, ...summary };
            } catch {
              return { id: String(item.id), item_id: item.item_id, name: item.name, type: item.type, currentPrice: null, priceChange24h: null, volatility: null, volume24h: null };
            }
          })
        );

        if (!cancelled) {
          setItems(summaries);
          setTrending(trendingItems.map((item: CatalogItem) => ({
            item_id: item.id,
            name: item.name,
            type: item.type,
            latest_price: 0,
          })));
        }
      } catch (fetchError) {
        if (!cancelled) {
          setError(fetchError instanceof Error ? fetchError.message : 'Failed to load market data');
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    loadMarketData();
    return () => { cancelled = true; };
  }, []);

  const filteredItems = useMemo(() => {
    const filtered = searchQuery
      ? items.filter(item => item.name.toLowerCase().includes(searchQuery.toLowerCase()))
      : items;

    return [...filtered].sort((a, b) => {
      if (sortBy === 'name') {
        return sortOrder === 'asc' ? a.name.localeCompare(b.name) : b.name.localeCompare(a.name);
      }
      const aVal = a[sortBy];
      const bVal = b[sortBy];
      return sortOrder === 'asc'
        ? (aVal ?? Number.NEGATIVE_INFINITY) - (bVal ?? Number.NEGATIVE_INFINITY)
        : (bVal ?? Number.NEGATIVE_INFINITY) - (aVal ?? Number.NEGATIVE_INFINITY);
    });
  }, [items, searchQuery, sortBy, sortOrder]);

  const handleSort = (column: SortKey) => {
    if (sortBy === column) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
      return;
    }
    setSortBy(column);
    setSortOrder('desc');
  };

  return (
    <div className="min-h-screen bg-background-primary">
      <Header />

      <div className="max-w-7xl mx-auto px-6 py-10">
        <div className="mb-10">
          <div className="mb-8">
            <span className="font-data text-[10px] font-bold uppercase tracking-[0.3em] text-brand mb-3 block">
              MARKET_OVERVIEW
            </span>
            <h1 className="text-4xl font-bold mb-2 text-primary">Market Overview</h1>
            <p className="text-base text-secondary">
              Live market snapshots and recent movers from the backend API
            </p>
          </div>

          <input
            type="text"
            placeholder="SEARCH ITEMS..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full max-w-[500px] px-4 py-3 bg-surface border border-border rounded-sm text-sm text-primary placeholder:text-muted focus:bg-surface-hover focus:border-accent-primary transition-all outline-none uppercase tracking-widest font-bold"
          />
        </div>

        <div className="mb-10">
          <div className="flex items-baseline justify-between gap-4 mb-4">
            <h2 className="text-lg font-semibold text-primary">Trending now</h2>
            <span className="tag-tech">/items/trending</span>
          </div>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {trending.length > 0 ? trending.map((item) => (
              <motion.div
                key={item.item_id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="widget-block flex items-center justify-between px-4 py-3"
              >
                <div>
                  <div className="font-medium text-primary text-sm">{item.name}</div>
                  <div className="text-xs uppercase tracking-wide text-secondary">{item.type}</div>
                </div>
                <div className="text-right font-data text-sm text-primary">{formatCurrency(item.latest_price)}</div>
              </motion.div>
            )) : !isLoading && (
              <div className="widget-block px-4 py-3 text-sm text-secondary col-span-full">
                No trending items available.
              </div>
            )}
          </div>
        </div>

        {error && (
          <div className="mb-6 rounded-sm border border-data-down/35 bg-data-down-subtle/20 px-4 py-3 text-sm text-primary">
            {error}
          </div>
        )}

        <div className="overflow-x-auto rounded-sm border border-border bg-surface shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-background-tertiary border-b border-border">
                <th className="px-6 py-5 text-left text-xs font-semibold uppercase tracking-wide text-secondary">
                  <button onClick={() => handleSort('name')} className="hover:text-primary transition flex items-center gap-2">
                    Item {sortBy === 'name' && <SortArrow />}
                  </button>
                </th>
                <th className="px-6 py-5 text-left text-xs font-semibold uppercase tracking-wide text-secondary">
                  <span>Type</span>
                </th>
                <th className="px-6 py-5 text-right text-xs font-semibold uppercase tracking-wide text-secondary">
                  <button onClick={() => handleSort('currentPrice')} className="w-full flex justify-end hover:text-primary transition items-center gap-2">
                    Price {sortBy === 'currentPrice' && <SortArrow />}
                  </button>
                </th>
                <th className="px-6 py-5 text-right text-xs font-semibold uppercase tracking-wide text-secondary">
                  <button onClick={() => handleSort('priceChange24h')} className="w-full flex justify-end hover:text-primary transition items-center gap-2">
                    24h Change {sortBy === 'priceChange24h' && <SortArrow />}
                  </button>
                </th>
                <th className="px-6 py-5 text-right text-xs font-semibold uppercase tracking-wide text-secondary">
                  <button onClick={() => handleSort('volatility')} className="w-full flex justify-end hover:text-primary transition items-center gap-2">
                    Vol {sortBy === 'volatility' && <SortArrow />}
                  </button>
                </th>
                <th className="px-6 py-5 text-right text-xs font-semibold uppercase tracking-wide text-secondary">
                  <button onClick={() => handleSort('volume24h')} className="w-full flex justify-end hover:text-primary transition items-center gap-2">
                    Volume {sortBy === 'volume24h' && <SortArrow />}
                  </button>
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-secondary">
                    Loading backend market data...
                  </td>
                </tr>
              ) : filteredItems.length ? (
                filteredItems.map((item, idx) => (
                  <motion.tr
                    key={item.item_id}
                    initial={{ opacity: 0, y: -4 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.02 }}
                    className="stripe-row cursor-pointer"
                    style={{ backgroundColor: hoveredRow === item.item_id ? 'var(--background-tertiary)' : 'transparent' }}
                    onMouseEnter={() => setHoveredRow(item.item_id)}
                    onMouseLeave={() => setHoveredRow(null)}
                  >
                    <td className="px-6 py-4">
                      <Link
                        href={`/items/${item.item_id}`}
                        className="font-medium transition-colors text-primary hover:text-brand"
                      >
                        {item.name}
                      </Link>
                    </td>
                    <td className="px-6 py-4 text-left uppercase tracking-wide text-xs text-secondary">
                      {item.type}
                    </td>
                    <td className="px-6 py-4 text-right font-data font-medium text-primary">
                      {formatCurrency(item.currentPrice)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span
                        className="inline-block px-3 py-1.5 rounded-sm font-data font-semibold text-xs"
                        style={{
                          backgroundColor: (item.priceChange24h ?? 0) >= 0 ? 'var(--data-up-subtle)' : 'var(--data-down-subtle)',
                          color: (item.priceChange24h ?? 0) >= 0 ? 'var(--data-up)' : 'var(--data-down)'
                        }}
                      >
                        {formatPercent(item.priceChange24h)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-6 h-5 bg-grid rounded-[3px] relative overflow-hidden">
                          <div
                            className="absolute bottom-0 left-0 right-0 transition-all"
                            style={{
                              height: `${Math.min(item.volatility ?? 0, 100)}%`,
                              backgroundColor: 'var(--brand)',
                              opacity: 0.5
                            }}
                          />
                        </div>
                        <span className="font-data text-xs text-secondary">
                          {item.volatility == null ? '\u2014' : `${item.volatility.toFixed(1)}%`}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right font-data text-secondary">
                      {formatVolume(item.volume24h)}
                    </td>
                  </motion.tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-secondary">
                    No items match your search
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function SortArrow() {
  return <span className="text-brand text-[10px]">&#9660;</span>;
}
