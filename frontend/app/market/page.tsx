'use client';

import { useEffect, useMemo, useState, Suspense } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Header } from '@/components';
import { getMarketSummary, getTrendingItems, GroupedMarketItem, QualityVariant } from '@/lib/api';

type SortKey = 'name' | 'priceAvg' | 'priceChange24h' | 'volatility' | 'volume24h';

interface TrendingRow {
  item_id: string;
  name: string;
  type: string;
  icon_url: string | null;
  latest_price: number;
}

const PAGE_SIZE = 100;
const TYPES = ['all', 'skin', 'case', 'sticker'] as const;
const TYPE_LABELS: Record<string, string> = { all: 'All', skin: 'Skins', case: 'Cases', sticker: 'Stickers' };

const EASE: [number, number, number, number] = [0.16, 1, 0.3, 1];

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

function SortArrow({ direction }: { direction: 'asc' | 'desc' }) {
  return (
    <span className="text-accent-primary text-[10px] leading-none">
      {direction === 'desc' ? '\u25BC' : '\u25B2'}
    </span>
  );
}

function SkeletonRow() {
  return (
    <tr className="stripe-row">
      <td className="px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-sm bg-background-tertiary animate-pulse" />
          <div className="h-4 w-48 bg-background-tertiary rounded-sm animate-pulse" />
        </div>
      </td>
      <td className="px-6 py-4">
        <div className="h-4 w-12 bg-background-tertiary rounded-sm animate-pulse" />
      </td>
      <td className="px-6 py-4">
        <div className="h-4 w-20 bg-background-tertiary rounded-sm animate-pulse ml-auto" />
      </td>
      <td className="px-6 py-4">
        <div className="h-6 w-16 bg-background-tertiary rounded-sm animate-pulse ml-auto" />
      </td>
      <td className="px-6 py-4">
        <div className="h-4 w-16 bg-background-tertiary rounded-sm animate-pulse ml-auto" />
      </td>
      <td className="px-6 py-4">
        <div className="h-4 w-12 bg-background-tertiary rounded-sm animate-pulse ml-auto" />
      </td>
    </tr>
  );
}

function readUrlParams() {
  if (typeof window === 'undefined') return {};
  const params = new URLSearchParams(window.location.search);
  const result: Record<string, string> = {};
  for (const [key, value] of params) result[key] = value;
  return result;
}

function MarketPageInner() {
  const [urlParams] = useState(readUrlParams);

  const initialType = TYPES.includes(urlParams.type as typeof TYPES[number])
    ? (urlParams.type as typeof TYPES[number]) : 'all';
  const initialQ = urlParams.q ?? '';
  const initialPage = parseInt(urlParams.page ?? '0', 10) || 0;
  const initialSortBy = (urlParams.sortBy as SortKey) ?? 'priceAvg';
  const initialSortOrder = urlParams.sortOrder === 'asc' ? ('asc' as const) : ('desc' as const);

  const [items, setItems] = useState<GroupedMarketItem[]>([]);
  const [trending, setTrending] = useState<TrendingRow[]>([]);
  const [sortBy, setSortBy] = useState<SortKey>(initialSortBy);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>(initialSortOrder);
  const [searchQuery, setSearchQuery] = useState(initialQ);
  const [debouncedQuery, setDebouncedQuery] = useState(initialQ);
  const [activeType, setActiveType] = useState<string>(initialType);
  const [hoveredRow, setHoveredRow] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pageOffset, setPageOffset] = useState(initialPage);
  const [hasMore, setHasMore] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQuery(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const filterKey = `${debouncedQuery}|${activeType}`;
  const [prevFilterKey, setPrevFilterKey] = useState(filterKey);
  const page = prevFilterKey === filterKey ? pageOffset : 0;

  if (prevFilterKey !== filterKey) {
    setPrevFilterKey(filterKey);
    setPageOffset(0);
  }

  const fetchKey = `${debouncedQuery}|${activeType}|${page}`;

  useEffect(() => {
    let cancelled = false;

    async function loadMarketData() {
      setError(null);
      if (!items.length) setIsLoading(true);

      try {
        const raw = await Promise.all([
          getMarketSummary(
            activeType === 'all' ? undefined : activeType,
            debouncedQuery || undefined,
            page * PAGE_SIZE,
            PAGE_SIZE + 1,
          ),
          getTrendingItems(6),
        ]);
        const summaryResponse = raw[0];
        const trendingResponse = raw[1];

        const hasNext = Array.isArray(summaryResponse) && summaryResponse.length > PAGE_SIZE;
        const pageItems = Array.isArray(summaryResponse) ? summaryResponse.slice(0, PAGE_SIZE) : [];

        const summaryItems: GroupedMarketItem[] = pageItems.map((r: Record<string, unknown>) => ({
          base_name: String(r.base_name ?? ''),
          type: String(r.type ?? ''),
          icon_url: (r.icon_url as string) ?? null,
          price_avg: (r.price_avg as number) ?? null,
          price_min: (r.price_min as number) ?? null,
          price_max: (r.price_max as number) ?? null,
          price_change_24h: (r.price_change_24h as number) ?? null,
          volatility: (r.volatility as number) ?? null,
          volume_24h: (r.volume_24h as number) ?? null,
          quality_count: (r.quality_count as number) ?? 1,
          qualities: (r.qualities as QualityVariant[]) ?? [],
        }));

        if (!cancelled) {
          setItems(summaryItems);
          setHasMore(hasNext);
          const trendingArr = Array.isArray(trendingResponse) ? trendingResponse : [];
          setTrending(trendingArr.map((item: Record<string, unknown>) => ({
            item_id: String(item.item_id ?? ''),
            name: String(item.name ?? ''),
            type: String(item.type ?? ''),
            icon_url: (item.icon_url as string) ?? null,
            latest_price: (item.latest_price as number) ?? 0,
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
  }, [fetchKey]);

  useEffect(() => {
    const next = new URLSearchParams();
    if (activeType !== 'all') next.set('type', activeType);
    if (searchQuery) next.set('q', searchQuery);
    if (page > 0) next.set('page', String(page));
    if (sortBy !== 'priceAvg') next.set('sortBy', sortBy);
    if (sortOrder !== 'desc') next.set('sortOrder', sortOrder);
    const qs = next.toString();
    window.history.replaceState(null, '', `${window.location.pathname}${qs ? `?${qs}` : ''}`);
  }, [activeType, searchQuery, page, sortBy, sortOrder]);

  const setAndSearch = (type: string) => {
    setActiveType(type);
  };

  const sortedItems = useMemo(() => {
    return [...items].sort((a, b) => {
      if (sortBy === 'name') {
        return sortOrder === 'asc' ? a.base_name.localeCompare(b.base_name) : b.base_name.localeCompare(a.base_name);
      }
      const fieldMap: Record<string, keyof GroupedMarketItem> = {
        priceAvg: 'price_avg',
        priceChange24h: 'price_change_24h',
        volatility: 'volatility',
        volume24h: 'volume_24h',
      };
      const field = fieldMap[sortBy] ?? sortBy;
      const aVal = a[field] as number | null;
      const bVal = b[field] as number | null;
      return sortOrder === 'asc'
        ? (aVal ?? Number.NEGATIVE_INFINITY) - (bVal ?? Number.NEGATIVE_INFINITY)
        : (bVal ?? Number.NEGATIVE_INFINITY) - (aVal ?? Number.NEGATIVE_INFINITY);
    });
  }, [items, sortBy, sortOrder]);

  const handleSort = (column: SortKey) => {
    if (sortBy === column) {
      const next = sortOrder === 'asc' ? 'desc' : 'asc';
      setSortOrder(next);
      return;
    }
    setSortBy(column);
    setSortOrder('desc');
  };

  return (
    <div className="min-h-screen bg-background-primary">
      <Header />

      <div className="max-w-7xl mx-auto px-6 py-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: EASE }}
          className="mb-8"
        >
          <span className="font-data text-[10px] font-bold uppercase tracking-[0.3em] text-accent-primary mb-3 block">
            MARKET_OVERVIEW
          </span>
          <h1 className="text-4xl font-bold mb-2 text-primary tracking-tight">Market Overview</h1>
          <p className="text-base text-secondary">
            Live market snapshots and recent movers
          </p>
        </motion.div>

        {/* Search + Filters */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.45, ease: EASE }}
          className="flex flex-col sm:flex-row gap-4 mb-10"
        >
          <div className="relative flex-1 max-w-[500px]">
            <div className="relative flex items-center bg-surface border border-border rounded-sm focus-within:border-accent transition-colors duration-200">
              <svg
                className="w-4 h-4 ml-4 text-muted transition-colors shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                placeholder="SEARCH ITEMS..."
                value={searchQuery}
                onChange={(e) => { setSearchQuery(e.target.value); }}
                className="flex-1 px-4 py-3 bg-transparent text-sm text-primary placeholder:text-muted focus:outline-none uppercase tracking-widest font-bold"
              />
            </div>
          </div>
          <div className="flex gap-1.5 items-center">
            {TYPES.map((t) => (
              <button
                key={t}
                onClick={() => setAndSearch(t)}
                className={`px-4 py-3 text-xs font-bold uppercase tracking-widest rounded-sm border transition-all duration-200 ${
                  activeType === t
                    ? 'bg-accent text-background-primary border-accent'
                    : 'bg-surface text-secondary border-border hover:bg-surface-hover hover:border-accent-primary'
                }`}
              >
                {TYPE_LABELS[t]}
              </button>
            ))}
          </div>
        </motion.div>

        {/* Trending */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.45, ease: EASE }}
          className="mb-10"
        >
          <div className="flex items-baseline justify-between gap-4 mb-4">
            <h2 className="text-lg font-semibold text-primary">Trending now</h2>
            <span className="tag-tech">/items/trending</span>
          </div>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {trending.length > 0 ? trending.map((item, i) => (
              <Link key={item.item_id} href={`/items/${item.item_id}`}>
                <motion.div
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.25 + i * 0.04, duration: 0.4, ease: EASE }}
                  className="widget-block flex items-center justify-between px-4 py-3 cursor-pointer group"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    {item.icon_url ? (
                      <div className="w-8 h-8 rounded-sm overflow-hidden shrink-0 bg-background-tertiary">
                          <img src={item.icon_url} alt={item.name} className="w-8 h-8 rounded-sm object-cover shrink-0" loading="lazy" />
                      </div>
                    ) : (
                      <div className="w-8 h-8 rounded-sm bg-background-tertiary shrink-0" />
                    )}
                    <div className="min-w-0">
                      <div className="font-medium text-primary text-sm truncate group-hover:text-accent-primary transition-colors">{item.name}</div>
                      <div className="text-[10px] uppercase tracking-wide text-secondary">{item.type}</div>
                    </div>
                  </div>
                  <div className="text-right font-data text-sm text-primary shrink-0 ml-4">
                    {formatCurrency(item.latest_price)}
                  </div>
                </motion.div>
              </Link>
            )) : !isLoading && (
              <div className="widget-block px-4 py-3 text-sm text-secondary col-span-full">
                No trending items available.
              </div>
            )}
          </div>
        </motion.div>

        {/* Error */}
        {error && (
          <div className="mb-6 rounded-sm border border-data-down/35 bg-data-down-subtle/20 px-4 py-3 text-sm text-primary flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={() => {
                setError(null);
                setIsLoading(true);
              }}
              className="text-xs font-bold uppercase tracking-widest text-accent-primary hover:text-brand-hover"
            >
              Retry
            </button>
          </div>
        )}

        {/* Table */}
        {isLoading && items.length > 0 && <div className="h-0.5 w-full bg-accent/40 mb-1 rounded-full overflow-hidden"><div className="h-full bg-accent animate-pulse" /></div>}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.45, ease: EASE }}
          className="overflow-x-auto rounded-sm border border-border bg-surface shadow-sm"
        >
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-background-tertiary border-b border-border">
                <th className="px-6 py-5 text-left text-xs font-semibold uppercase tracking-wide text-secondary w-[40%]">
                  <button onClick={() => handleSort('name')} className="hover:text-primary transition-colors flex items-center gap-2">
                    Item {sortBy === 'name' && <SortArrow direction={sortOrder} />}
                  </button>
                </th>
                <th className="px-6 py-5 text-left text-xs font-semibold uppercase tracking-wide text-secondary w-[8%]">
                  <span>Type</span>
                </th>
                <th className="px-6 py-5 text-right text-xs font-semibold uppercase tracking-wide text-secondary w-[15%]">
                  <button onClick={() => handleSort('priceAvg')} className="w-full flex justify-end hover:text-primary transition-colors items-center gap-2">
                    Avg Price {sortBy === 'priceAvg' && <SortArrow direction={sortOrder} />}
                  </button>
                </th>
                <th className="px-6 py-5 text-right text-xs font-semibold uppercase tracking-wide text-secondary w-[12%]">
                  <span className="text-tertiary">Range</span>
                </th>
                <th className="px-6 py-5 text-right text-xs font-semibold uppercase tracking-wide text-secondary w-[10%]">
                  <button onClick={() => handleSort('priceChange24h')} className="w-full flex justify-end hover:text-primary transition-colors items-center gap-2">
                    24h {sortBy === 'priceChange24h' && <SortArrow direction={sortOrder} />}
                  </button>
                </th>
                <th className="px-6 py-5 text-right text-xs font-semibold uppercase tracking-wide text-secondary w-[8%]">
                  <button onClick={() => handleSort('volume24h')} className="w-full flex justify-end hover:text-primary transition-colors items-center gap-2">
                    Vol {sortBy === 'volume24h' && <SortArrow direction={sortOrder} />}
                  </button>
                </th>
                <th className="px-6 py-5 text-center text-xs font-semibold uppercase tracking-wide text-secondary w-[7%]">
                  <span>Quals</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading && !items.length ? (
                Array.from({ length: 10 }).map((_, i) => <SkeletonRow key={i} />)
              ) : sortedItems.length ? (
                sortedItems.map((item, idx) => {
                  const firstVariant = item.qualities[0];
                  const linkId = firstVariant?.item_id ?? item.base_name;
                  return (
                    <motion.tr
                      key={item.base_name}
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.01 }}
                      className="stripe-row cursor-pointer group"
                      style={{ backgroundColor: hoveredRow === item.base_name ? 'var(--background-tertiary)' : 'transparent' }}
                      onMouseEnter={() => setHoveredRow(item.base_name)}
                      onMouseLeave={() => setHoveredRow(null)}
                    >
                      <td className="px-6 py-4">
                        <Link
                          href={`/items/${encodeURIComponent(linkId)}`}
                          className="flex items-center gap-3 font-medium transition-colors text-primary group-hover:text-accent-primary"
                        >
                          {item.icon_url ? (
                          <img src={item.icon_url} alt={item.base_name} className="w-8 h-8 rounded-sm object-cover shrink-0" loading="lazy" />
                          ) : (
                            <div className="w-8 h-8 rounded-sm bg-background-tertiary shrink-0" />
                          )}
                          <span className="truncate">{item.base_name}</span>
                        </Link>
                      </td>
                      <td className="px-6 py-4 text-left uppercase tracking-wide text-xs text-secondary">
                        {item.type}
                      </td>
                      <td className="px-6 py-4 text-right font-data font-medium text-primary">
                        {formatCurrency(item.price_avg)}
                      </td>
                      <td className="px-6 py-4 text-right font-data text-xs text-tertiary">
                        {item.price_min != null && item.price_max != null
                          ? `${formatCurrency(item.price_min)} – ${formatCurrency(item.price_max)}`
                          : '\u2014'}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <span
                          className="inline-block px-3 py-1.5 rounded-sm font-data font-semibold text-xs"
                          style={{
                            backgroundColor: (item.price_change_24h ?? 0) >= 0 ? 'var(--data-up-subtle)' : 'var(--data-down-subtle)',
                            color: (item.price_change_24h ?? 0) >= 0 ? 'var(--data-up)' : 'var(--data-down)'
                          }}
                        >
                          {formatPercent(item.price_change_24h)}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right font-data text-secondary">
                        {formatVolume(item.volume_24h)}
                      </td>
                      <td className="px-6 py-4 text-center">
                        <span className="inline-block px-2 py-0.5 rounded-sm bg-background-tertiary text-xs font-data text-secondary">
                          {item.quality_count}
                        </span>
                      </td>
                    </motion.tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={7} className="px-6 py-16 text-center">
                    <div className="flex flex-col items-center gap-3">
                      <span className="text-3xl text-tertiary">{'\u2205'}</span>
                      {isLoading ? (
                        <p className="text-secondary font-medium">Searching...</p>
                      ) : (
                        <>
                          <p className="text-secondary font-medium">No items match your search</p>
                          <p className="text-xs text-tertiary max-w-md">
                            Try broadening your search terms, or clear the filter to browse all items.
                          </p>
                          <button
                            onClick={() => { setSearchQuery(''); setDebouncedQuery(''); setActiveType('all'); setPageOffset(0); }}
                            className="text-xs font-bold uppercase tracking-widest text-accent-primary hover:text-brand-hover transition-colors mt-2"
                          >
                            Clear all filters
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>

          <div className="flex items-center justify-between px-6 py-4 border-t border-border bg-surface">
            <button
              onClick={() => setPageOffset(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="text-xs font-bold uppercase tracking-widest text-secondary hover:text-primary transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              {'\u2190'} Previous
            </button>
            <span className="text-xs font-data text-tertiary">Page {page + 1}</span>
            <button
              onClick={() => setPageOffset(p => p + 1)}
              disabled={!hasMore}
              className="text-xs font-bold uppercase tracking-widest text-secondary hover:text-primary transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Next {'\u2192'}
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

export default function MarketPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-background-primary flex items-center justify-center">
        <div className="h-0.5 w-48 bg-accent/40 rounded-full overflow-hidden"><div className="h-full bg-accent animate-pulse" /></div>
      </div>
    }>
      <MarketPageInner />
    </Suspense>
  );
}
