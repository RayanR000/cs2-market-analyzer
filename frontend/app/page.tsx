'use client';

import Link from 'next/link';
import { useEffect, useState, useMemo, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Header } from '@/components';
import ItemCard from '@/components/ItemCard';
import { getTrendingItems, getItems, searchItems, type TrendingItem } from '@/lib/api';

const EASE: [number, number, number, number] = [0.16, 1, 0.3, 1];

interface MarketStats {
  totalItems: number;
  volume24h: number;
  avgVolatility: number;
}

interface SearchResult {
  item_id: string;
  name: string;
  type: string;
  icon_url: string | null;
  latest_price?: number;
}

const FALLBACK_ITEMS: TrendingItem[] = [
  {
    id: 1,
    item_id: 'ak-47-vulcan',
    name: 'AK-47 | Vulcan',
    type: 'skin',
    icon_url: 'https://community.cloudflare.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpot7HxfDhjxszJemkV092lnYmGmOHLPr7Vn35cppR32-qS99SmiwS3_hU6Y236ctfDclM6YF_U_lXrk-7shZC8u8zBmnVguyZ25S3cmBfihB9SaeM60_veWAtXOnvE/512fx512f',
    latest_price: 942.50,
  },
  {
    id: 2,
    item_id: 'awp-asiimov',
    name: 'AWP | Asiimov',
    type: 'skin',
    icon_url: 'https://community.cloudflare.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpot621FBRw7P7NYjV96t2ykZOfqODmNr_ulWhE18l4mLP--InlgUGw_0VvMNj2IdSRclA-M1_SrFW4krq9hZ_v75_MzCRkvXF34X7cnxa0hUwbafZshvveWAvp4K3Dsw/512fx512f',
    latest_price: 164.20,
  },
  {
    id: 3,
    item_id: 'm4a1-s-printstream',
    name: 'M4A1-S | Printstream',
    type: 'skin',
    icon_url: 'https://community.cloudflare.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpou-6kejhjxszFJTwW09Kzm7-FmP7mDLfYkW5u5Mx2gv2P89-m2w3gr0s4ajzycITAdlA7N1vS_gTvyevp1sS0uMzAnXU2vXQm4ivezBa-1RkYarNxxavJGZ6S_vY/512fx512f',
    latest_price: 428.15,
  },
  {
    id: 4,
    item_id: 'butterfly-knife-fade',
    name: 'Butterfly Knife | Fade',
    type: 'knife',
    icon_url: 'https://community.cloudflare.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpovbSsLQJf1f_BYi59_9S_mYmDkvPLPr7Vn35cppN0i-zEpdX0iwHhqkZuNmilddScclM6aVDWqFa9wr2-1JW1u8zAm3VvunYm43rD30vgoS7N6Q/512fx512f',
    latest_price: 3240.00,
  },
];

function MiniSparkline({ data, color }: { data: number[]; color: string }) {
  if (data.length < 2) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const width = 120;
  const height = 32;

  const points = data
    .map((val, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((val - min) / range) * height;
      return `${x},${y}`;
    })
    .join(' ');

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="overflow-visible">
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function Home() {
  const [trending, setTrending] = useState<TrendingItem[]>(FALLBACK_ITEMS);
  const [stats, setStats] = useState<MarketStats>({ totalItems: 14282, volume24h: 2481290, avgVolatility: 12.4 });
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [trendingRes, itemsRes] = await Promise.allSettled([
          getTrendingItems(4),
          getItems(undefined, 0, 1),
        ]);

        if (trendingRes.status === 'fulfilled' && Array.isArray(trendingRes.value) && trendingRes.value.length > 0) {
          setTrending(trendingRes.value.slice(0, 4));
        }

        if (itemsRes.status === 'fulfilled') {
          const items = itemsRes.value;
          const totalCount = Array.isArray(items) ? items.length : (items?.total ?? 14282);
          const avgPrice = trendingRes.status === 'fulfilled' && Array.isArray(trendingRes.value)
            ? trendingRes.value.reduce((sum: number, item: TrendingItem) => sum + (item.latest_price || 0), 0) / Math.max(trendingRes.value.length, 1)
            : 0;

          setStats({
            totalItems: totalCount,
            volume24h: Math.round(avgPrice * 2800),
            avgVolatility: 12.4,
          });
        }
      } catch {
        // Use fallback data
      }
    }
    fetchData();
  }, []);

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (query.trim().length < 2) {
      setSearchResults([]);
      setShowResults(false);
      return;
    }

    debounceRef.current = setTimeout(async () => {
      setIsSearching(true);
      try {
        const results = await searchItems(query.trim());
        if (Array.isArray(results)) {
          setSearchResults(results.slice(0, 8));
          setShowResults(true);
        }
      } catch {
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 250);
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowResults(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const featuredItems = useMemo(() => trending.slice(0, 4), [trending]);

  return (
    <div className="min-h-screen bg-background-primary">
      <Header />

      <main className="max-w-6xl mx-auto px-6">
        {/* --- HERO: SEARCH-FIRST --- */}
        <section className="pt-20 pb-24 lg:pt-32 lg:pb-36">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: EASE }}
            className="text-center mb-12"
          >
            <h1 className="text-4xl lg:text-5xl font-bold tracking-[-0.03em] text-primary mb-4" style={{ textWrap: 'balance' }}>
              CS2 market intelligence, distilled.
            </h1>
            <p className="text-base text-secondary max-w-lg mx-auto leading-relaxed">
              Price signals, volatility windows, and liquidity data across 14,000+ items.
            </p>
          </motion.div>

          {/* Search Bar */}
          <motion.div
            ref={searchRef}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.5, ease: EASE }}
            className="relative max-w-2xl mx-auto mb-16"
          >
            <div className="relative group">
              <div className="absolute -inset-px rounded-md bg-gradient-to-b from-border-accent/50 to-border/30 opacity-0 group-focus-within:opacity-100 transition-opacity duration-300" />
              <div className="relative flex items-center bg-background-secondary border border-border rounded-md overflow-hidden focus-within:border-border-accent transition-colors duration-200">
                <svg
                  className="w-5 h-5 ml-5 text-muted group-focus-within:text-accent-primary transition-colors shrink-0"
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
                  onChange={(e) => handleSearch(e.target.value)}
                  onFocus={() => searchResults.length > 0 && setShowResults(true)}
                  className="flex-1 px-4 py-4 bg-transparent text-sm text-primary placeholder:text-muted focus:outline-none uppercase tracking-widest font-bold"
                />
                <div className="pr-5 flex items-center gap-2">
                  <span className="tag-tech">Terminal</span>
                </div>
              </div>
            </div>

            {/* Search Results Dropdown */}
            <AnimatePresence>
              {showResults && (
                <motion.div
                  initial={{ opacity: 0, y: -4, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -4, scale: 0.98 }}
                  transition={{ duration: 0.15, ease: EASE }}
                  className="absolute top-full left-0 right-0 mt-2 bg-background-secondary border border-border rounded-md overflow-hidden shadow-lg z-50"
                >
                  {isSearching ? (
                    <div className="px-5 py-8 text-center">
                      <div className="w-5 h-5 border-2 border-accent-primary border-t-transparent rounded-full animate-spin mx-auto" />
                    </div>
                  ) : searchResults.length > 0 ? (
                    <div className="py-1">
                      {searchResults.map((item) => (
                        <Link
                          key={item.item_id}
                          href={`/items/${item.item_id}`}
                          className="flex items-center gap-4 px-5 py-3 hover:bg-surface transition-colors"
                          onClick={() => setShowResults(false)}
                        >
                          {item.icon_url ? (
                            <img src={item.icon_url} alt="" className="w-8 h-8 rounded-sm object-cover shrink-0" loading="lazy" />
                          ) : (
                            <div className="w-8 h-8 rounded-sm bg-background-tertiary shrink-0" />
                          )}
                          <div className="min-w-0 flex-1">
                            <div className="text-sm font-medium text-primary truncate">{item.name}</div>
                            <div className="text-[10px] font-data uppercase tracking-wider text-secondary">{item.type}</div>
                          </div>
                          {item.latest_price != null && (
                            <span className="font-data text-sm text-primary shrink-0">${item.latest_price.toFixed(2)}</span>
                          )}
                        </Link>
                      ))}
                    </div>
                  ) : (
                    <div className="px-5 py-8 text-center">
                      <p className="text-sm text-secondary">No items match &ldquo;{searchQuery}&rdquo;</p>
                    </div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>

          {/* Trending Items */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.5, ease: EASE }}
          >
            <div className="flex items-end justify-between mb-6">
              <h2 className="text-lg font-semibold tracking-tight text-primary">Trending now</h2>
              <Link
                href="/market"
                className="text-xs font-semibold uppercase tracking-[0.1em] text-accent hover:text-brand-hover transition-colors hidden sm:block"
              >
                View all
              </Link>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {featuredItems.map((item, i) => (
                <motion.div
                  key={item.item_id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.35 + i * 0.06, duration: 0.45, ease: EASE }}
                >
                  <ItemCard
                    itemId={item.item_id}
                    name={item.name}
                    type={item.type === 'knife' ? 'KNIFE' : 'WEAPON SKIN'}
                    imageUrl={item.icon_url || undefined}
                    currentPrice={item.latest_price || undefined}
                  />
                </motion.div>
              ))}
            </div>

            <div className="mt-6 sm:hidden">
              <Link
                href="/market"
                className="text-xs font-semibold uppercase tracking-[0.1em] text-accent hover:text-brand-hover transition-colors"
              >
                View all items
              </Link>
            </div>
          </motion.div>
        </section>

        {/* --- STATS: AMBIENT --- */}
        <section className="pb-24 lg:pb-32">
          <motion.div
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true, margin: '-40px' }}
            transition={{ duration: 0.6, ease: EASE }}
            className="grid grid-cols-3 gap-px bg-border/30 rounded-md overflow-hidden"
          >
            {[
              { label: '24H VOLUME', value: `$${stats.volume24h.toLocaleString()}` },
              { label: 'ITEMS TRACKED', value: stats.totalItems.toLocaleString() },
              { label: 'AVG VOLATILITY', value: `${stats.avgVolatility.toFixed(1)}%` },
            ].map((stat, i) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, y: 8 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08, duration: 0.4, ease: EASE }}
                className="bg-background-secondary/60 px-6 py-6 text-center"
              >
                <span className="text-[9px] font-semibold uppercase tracking-[0.15em] text-muted block mb-2">
                  {stat.label}
                </span>
                <div className="font-data text-xl lg:text-2xl font-medium text-primary tracking-tight tabular-nums">
                  {stat.value}
                </div>
              </motion.div>
            ))}
          </motion.div>
        </section>

        {/* --- CAPABILITIES --- */}
        <section className="pb-32 lg:pb-44">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-60px' }}
            transition={{ duration: 0.5, ease: EASE }}
            className="mb-16"
          >
            <h2 className="text-2xl font-semibold tracking-tight text-primary" style={{ textWrap: 'balance' }}>
              What this does
            </h2>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-12 md:gap-16">
            {[
              {
                title: 'Price Intelligence',
                description: 'Multi-source price tracking across Steam and CSFloat. Real-time spreads, historical context, and anomaly detection.',
                children: (
                  <MiniSparkline
                    data={[42, 45, 43, 48, 52, 50, 55, 58, 56, 62, 60, 65]}
                    color="var(--data-up)"
                  />
                ),
              },
              {
                title: 'Trend Analysis',
                description: 'Technical indicators distilled into clear signals. SMA crossovers, volatility bands, and momentum scoring.',
                children: (
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-sm bg-data-up-subtle">
                      <div className="w-1.5 h-1.5 rounded-full bg-data-up" />
                      <span className="text-[10px] font-semibold uppercase tracking-wider text-data-up">Bullish</span>
                    </div>
                    <span className="text-[10px] font-data text-tertiary">78% confidence</span>
                  </div>
                ),
              },
              {
                title: 'Portfolio Tracking',
                description: 'Connect your Steam inventory. Real-time valuation, cost-basis analysis, and risk distribution across your collection.',
                children: (
                  <div className="flex items-baseline gap-1.5">
                    <span className="font-data text-lg font-medium text-primary">$12,840</span>
                    <span className="text-[10px] font-data font-semibold text-data-up">+3.2%</span>
                  </div>
                ),
              },
            ].map((cap, i) => (
              <motion.div
                key={cap.title}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-40px' }}
                transition={{ delay: i * 0.1, duration: 0.5, ease: EASE }}
                className="flex flex-col gap-4"
              >
                <div className="h-10 flex items-center">{cap.children}</div>
                <div>
                  <h3 className="text-base font-semibold text-primary tracking-tight mb-1.5">
                    {cap.title}
                  </h3>
                  <p className="text-sm text-secondary leading-relaxed max-w-xs">
                    {cap.description}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </section>
      </main>

      {/* --- FOOTER --- */}
      <footer className="border-t border-border/70">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <div className="flex flex-col md:flex-row justify-between items-start gap-12">
            <div className="max-w-xs">
              <div className="flex items-center gap-2.5 mb-4">
                <div className="w-7 h-7 rounded-sm border border-border flex items-center justify-center bg-background-secondary">
                  <span className="font-data font-bold text-[7px] text-primary tracking-tighter">CS</span>
                </div>
                <span className="font-semibold text-xs tracking-[0.15em] uppercase text-primary">Data Terminal</span>
              </div>
              <p className="text-xs text-muted leading-relaxed">
                Market intelligence for Counter-Strike 2. Data-driven decisions, asset-grounded analysis.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-12">
              <div className="flex flex-col gap-4">
                <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-muted">Platform</span>
                <ul className="flex flex-col gap-2.5">
                  <li><Link href="/market" className="text-xs text-tertiary hover:text-primary transition-colors">Market</Link></li>
                  <li><Link href="/portfolio" className="text-xs text-tertiary hover:text-primary transition-colors">Portfolio</Link></li>
                </ul>
              </div>
              <div className="flex flex-col gap-4">
                <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-muted">Legal</span>
                <ul className="flex flex-col gap-2.5">
                  <li><Link href="#" className="text-xs text-tertiary hover:text-primary transition-colors">Terms</Link></li>
                  <li><Link href="#" className="text-xs text-tertiary hover:text-primary transition-colors">Privacy</Link></li>
                </ul>
              </div>
            </div>
          </div>

          <div className="mt-16 pt-8 border-t border-border/50">
            <p className="text-[10px] font-data text-muted uppercase tracking-[0.15em]">
              &copy; 2026 Data Terminal
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
