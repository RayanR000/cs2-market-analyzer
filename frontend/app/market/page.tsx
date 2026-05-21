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
    return {
      currentPrice: null,
      priceChange24h: null,
      volatility: null,
      volume24h: null,
    };
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
    const variance =
      returns.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / returns.length;
    volatility = Math.sqrt(variance) * 100;
  }

  return {
    currentPrice: latest.price,
    priceChange24h,
    volatility,
    volume24h,
  };
}

function formatCurrency(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) {
    return '—';
  }

  return `$${value.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatPercent(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) {
    return '—';
  }

  const prefix = value > 0 ? '+' : '';
  return `${prefix}${value.toFixed(1)}%`;
}

function formatVolume(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) {
    return '—';
  }

  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }

  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }

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

        const catalogItems = Array.isArray(itemsResponse?.items)
          ? (itemsResponse.items as CatalogItem[])
          : [];
        const summaries = await Promise.all(
          catalogItems.map(async (item: CatalogItem) => {
            try {
              const historyResponse = await getPriceHistory(item.item_id, 30, 0, 500);
              const summary = summarizeHistory(historyResponse?.history ?? []);

              return {
                id: String(item.id),
                item_id: item.item_id,
                name: item.name,
                type: item.type,
                ...summary,
              };
            } catch {
              return {
                id: String(item.id),
                item_id: item.item_id,
                name: item.name,
                type: item.type,
                currentPrice: null,
                priceChange24h: null,
                volatility: null,
                volume24h: null,
              };
            }
          })
        );

        if (!cancelled) {
          setItems(summaries);
          setTrending(Array.isArray(trendingResponse?.trending) ? trendingResponse.trending : []);
        }
      } catch (fetchError) {
        if (!cancelled) {
          setError(fetchError instanceof Error ? fetchError.message : 'Failed to load market data');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    loadMarketData();

    return () => {
      cancelled = true;
    };
  }, []);

  const filteredItems = useMemo(() => {
    const filtered = searchQuery
      ? items.filter(item => item.name.toLowerCase().includes(searchQuery.toLowerCase()))
      : items;

    const sorted = [...filtered].sort((a, b) => {
      if (sortBy === 'name') {
        return sortOrder === 'asc'
          ? a.name.localeCompare(b.name)
          : b.name.localeCompare(a.name);
      }

      const numericKey = sortBy as Exclude<SortKey, 'name'>;
      const aVal = a[numericKey];
      const bVal = b[numericKey];
      const aScore = aVal == null ? Number.NEGATIVE_INFINITY : aVal;
      const bScore = bVal == null ? Number.NEGATIVE_INFINITY : bVal;

      return sortOrder === 'asc' ? aScore - bScore : bScore - aScore;
    });

    return sorted;
  }, [items, searchQuery, sortBy, sortOrder]);

  const handleSort = (column: SortKey) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
      return;
    }

    setSortBy(column);
    setSortOrder('desc');
  };

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--background-primary)' }}>
      <Header />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="mb-10">
          <div className="mb-6">
            <h1 className="text-4xl font-bold mb-2" style={{ color: 'var(--text-primary)' }}>
              Market Overview
            </h1>
            <p className="text-base" style={{ color: 'var(--text-secondary)' }}>
              Live market snapshots and recent movers from the backend API
            </p>
          </div>

          <input
            type="text"
            placeholder="Search items..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              maxWidth: '500px',
              padding: '11px 14px',
              backgroundColor: 'var(--surface)',
              borderColor: 'var(--border)',
              borderWidth: '1px',
              color: 'var(--text-primary)',
              borderRadius: '8px',
              fontSize: '14px',
              width: '100%',
              transition: 'all 0.2s ease'
            }}
            className="focus:outline-none"
            onFocus={(e) => {
              e.currentTarget.style.borderColor = 'var(--accent-primary)';
              e.currentTarget.style.backgroundColor = 'var(--surface-hover)';
              e.currentTarget.style.boxShadow = 'inset 0 0 0 1px var(--border-accent), 0 0 12px rgba(59, 130, 246, 0.1)';
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = 'var(--border)';
              e.currentTarget.style.backgroundColor = 'var(--surface)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          />
        </div>

        <div className="mb-8">
          <div className="flex items-baseline justify-between gap-4 mb-4">
            <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
              Trending now
            </h2>
            <span className="text-xs font-mono uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>
              /items/trending
            </span>
          </div>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {trending.map((item) => (
              <div
                key={item.item_id}
                className="flex items-center justify-between rounded-lg border px-4 py-3"
                style={{
                  borderColor: 'var(--border)',
                  backgroundColor: 'var(--surface)',
                }}
              >
                <div>
                  <div className="font-medium" style={{ color: 'var(--text-primary)' }}>
                    {item.name}
                  </div>
                  <div className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-secondary)' }}>
                    {item.type}
                  </div>
                </div>
                <div className="text-right font-mono">
                  <div style={{ color: 'var(--text-primary)' }}>{formatCurrency(item.latest_price)}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {error && (
          <div
            className="mb-6 rounded-lg border px-4 py-3 text-sm"
            style={{
              borderColor: 'rgba(239, 68, 68, 0.35)',
              backgroundColor: 'rgba(239, 68, 68, 0.08)',
              color: 'var(--text-primary)',
            }}
          >
            {error}
          </div>
        )}

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
                <th className="px-6 py-5 text-left text-xs font-semibold uppercase tracking-wide">
                  <button
                    onClick={() => handleSort('name')}
                    className="hover:opacity-80 transition flex items-center gap-2"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    Item {sortBy === 'name' && <span style={{ color: 'var(--accent-primary)' }}>▼</span>}
                  </button>
                </th>
                <th className="px-6 py-5 text-left text-xs font-semibold uppercase tracking-wide">
                  <span style={{ color: 'var(--text-secondary)' }}>Type</span>
                </th>
                <th className="px-6 py-5 text-right text-xs font-semibold uppercase tracking-wide">
                  <button
                    onClick={() => handleSort('currentPrice')}
                    className="w-full flex justify-end hover:opacity-80 transition items-center gap-2"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    Price {sortBy === 'currentPrice' && <span style={{ color: 'var(--accent-primary)' }}>▼</span>}
                  </button>
                </th>
                <th className="px-6 py-5 text-right text-xs font-semibold uppercase tracking-wide">
                  <button
                    onClick={() => handleSort('priceChange24h')}
                    className="w-full flex justify-end hover:opacity-80 transition items-center gap-2"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    24h Change {sortBy === 'priceChange24h' && <span style={{ color: 'var(--accent-primary)' }}>▼</span>}
                  </button>
                </th>
                <th className="px-6 py-5 text-right text-xs font-semibold uppercase tracking-wide">
                  <button
                    onClick={() => handleSort('volatility')}
                    className="w-full flex justify-end hover:opacity-80 transition items-center gap-2"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    Vol {sortBy === 'volatility' && <span style={{ color: 'var(--accent-primary)' }}>▼</span>}
                  </button>
                </th>
                <th className="px-6 py-5 text-right text-xs font-semibold uppercase tracking-wide">
                  <button
                    onClick={() => handleSort('volume24h')}
                    className="w-full flex justify-end hover:opacity-80 transition items-center gap-2"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    Volume {sortBy === 'volume24h' && <span style={{ color: 'var(--accent-primary)' }}>▼</span>}
                  </button>
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center" style={{ color: 'var(--text-secondary)' }}>
                    Loading backend market data...
                  </td>
                </tr>
              ) : filteredItems.length ? (
                filteredItems.map((item, idx) => (
                  <motion.tr
                    key={item.item_id}
                    initial={{ opacity: 0, y: -5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.01 }}
                    style={{
                      borderBottomColor: 'var(--divider)',
                      borderBottomWidth: '1px',
                      backgroundColor: hoveredRow === item.item_id ? 'var(--background-tertiary)' : 'transparent',
                      transition: 'background-color 0.2s ease'
                    }}
                    className="group cursor-pointer"
                    onMouseEnter={() => setHoveredRow(item.item_id)}
                    onMouseLeave={() => setHoveredRow(null)}
                  >
                    <td className="px-6 py-4">
                      <Link
                        href={`/items/${item.item_id}`}
                        className="font-medium transition-opacity hover:opacity-75"
                        style={{ color: hoveredRow === item.item_id ? 'var(--accent-primary)' : 'var(--text-primary)' }}
                      >
                        {item.name}
                      </Link>
                    </td>
                    <td className="px-6 py-4 text-left uppercase tracking-wide text-xs" style={{ color: 'var(--text-secondary)' }}>
                      {item.type}
                    </td>
                    <td className="px-6 py-4 text-right font-mono font-medium" style={{ color: 'var(--text-primary)' }}>
                      {formatCurrency(item.currentPrice)}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span
                        className="inline-block px-3 py-1.5 rounded font-mono font-semibold text-xs"
                        style={{
                          backgroundColor:
                            (item.priceChange24h ?? 0) >= 0 ? 'var(--data-up-subtle)' : 'var(--data-down-subtle)',
                          color: (item.priceChange24h ?? 0) >= 0 ? 'var(--data-up)' : 'var(--data-down)'
                        }}
                      >
                        {formatPercent(item.priceChange24h)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'flex-end',
                          gap: '8px'
                        }}
                      >
                        <div
                          style={{
                            width: '24px',
                            height: '20px',
                            backgroundColor: 'var(--grid)',
                            borderRadius: '3px',
                            position: 'relative',
                            overflow: 'hidden'
                          }}
                        >
                          <div
                            style={{
                              position: 'absolute',
                              bottom: 0,
                              left: 0,
                              right: 0,
                              height: `${Math.min(item.volatility ?? 0, 100)}%`,
                              backgroundColor: 'var(--accent-primary)',
                              opacity: 0.6
                            }}
                          />
                        </div>
                        <span className="font-mono text-xs" style={{ color: 'var(--text-secondary)' }}>
                          {item.volatility == null ? '—' : `${item.volatility.toFixed(1)}%`}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right font-mono" style={{ color: 'var(--text-secondary)' }}>
                      {formatVolume(item.volume24h)}
                    </td>
                  </motion.tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center" style={{ color: 'var(--text-secondary)' }}>
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
