'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { Header } from '@/components';
import StatCard from '@/components/StatCard';
import ItemCard from '@/components/ItemCard';
import Search from '@/components/Search';

const EASE: [number, number, number, number] = [0.16, 1, 0.3, 1];

export default function Home() {
  return (
    <div className="min-h-screen bg-background-primary">
      <Header />

      <main className="max-w-7xl mx-auto px-6 py-20 lg:py-32">
        {/* --- HERO --- */}
        <section className="mb-32">
          <div className="flex flex-col md:flex-row gap-16 lg:gap-32">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, ease: EASE }}
              className="flex-1"
            >
              <div className="flex items-center gap-3 mb-8">
                <span className="tag-tech">V1.0.4</span>
                <span className="w-1 h-1 rounded-full bg-text-muted" />
                <span className="font-data text-[10px] font-bold uppercase tracking-[0.2em] text-muted">
                  Institutional Terminal
                </span>
              </div>

              <h1 className="text-6xl lg:text-8xl font-semibold tracking-tighter leading-[0.85] text-primary mb-12 text-wrap-balance">
                Digital{' '}
                <span className="text-brand">Market Research.</span>
              </h1>

              <p className="text-xl text-secondary max-w-xl mb-12 leading-relaxed font-medium">
                A sophisticated analytical document for professional CS2 item speculators.
                Structured data blocks, precision trends, and asset-grounded research metrics.
              </p>

              <div className="flex flex-wrap gap-8 items-center">
                <Link
                  href="/market"
                  className="px-8 py-4 bg-brand text-white font-bold text-xs uppercase tracking-[0.2em] rounded-sm hover:bg-brand-hover transition-all active:scale-95"
                >
                  Launch Terminal
                </Link>
                <div className="flex flex-col">
                  <span className="font-data text-[10px] font-bold text-muted uppercase tracking-widest mb-1">
                    System State
                  </span>
                  <div className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-data-up" />
                    <span className="text-[11px] font-bold uppercase tracking-wider text-primary">Live Connection</span>
                  </div>
                </div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 1, delay: 0.2, ease: EASE }}
              className="w-full md:w-[400px]"
            >
              <div className="widget-block p-8 h-full flex flex-col justify-between">
                <div>
                  <h3 className="text-sm font-bold uppercase tracking-[0.2em] text-muted mb-6">
                    Quick Search
                  </h3>
                  <Search onSearch={() => {}} placeholder="SEARCH INDEX..." />
                </div>
                <div className="mt-12 pt-12 border-t border-border/60">
                  <p className="text-xs text-secondary leading-relaxed mb-4 italic">
                    &ldquo;Data-driven insights for the modern skin investor. Every metric grounded in high-resolution asset history.&rdquo;
                  </p>
                  <span className="tag-tech">Research Bot v0.2</span>
                </div>
              </div>
            </motion.div>
          </div>
        </section>

        {/* --- MARKET PULSE --- */}
        <motion.section
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.6, ease: EASE }}
          className="mb-32"
        >
          <div className="flex items-end justify-between mb-12">
            <div>
              <span className="font-data text-[10px] font-bold uppercase tracking-[0.3em] text-brand mb-3 block">
                [01] MARKET_PULSE
              </span>
              <h2 className="text-3xl font-semibold tracking-tighter text-primary">
                Real-time Indices.
              </h2>
            </div>
            <div className="hidden md:block">
              <span className="tag-tech">UPDT: 32ms ago</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <motion.div initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: 0.05, ease: EASE }}>
              <StatCard
                label="ACTIVE_TRACKERS"
                value={14282}
                annotation="LIVE"
                subvalue="Asset Indices"
              />
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: 0.1, ease: EASE }}>
              <StatCard
                label="24H_AGGREGATE"
                value={2481290}
                unit="$"
                isPositive={true}
                change={4.2}
                annotation="USD"
              />
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: 0.15, ease: EASE }}>
              <StatCard
                label="VOLATILITY_IDX"
                value={12.4}
                annotation="VIX"
                subvalue="Market Sentiment"
              />
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: 0.2, ease: EASE }}>
              <StatCard
                label="DATA_LOGS"
                value={1200000000}
                annotation="RAW"
                subvalue="Total Points"
              />
            </motion.div>
          </div>
        </motion.section>

        {/* --- ASSET SHOWCASE --- */}
        <motion.section
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.6, ease: EASE }}
          className="mb-32"
        >
          <div className="flex items-end justify-between mb-12">
            <div>
              <span className="font-data text-[10px] font-bold uppercase tracking-[0.3em] text-brand mb-3 block">
                [02] ASSET_SHOWCASE
              </span>
              <h2 className="text-3xl font-semibold tracking-tighter text-primary">
                High-Alpha Leads.
              </h2>
            </div>
            <Link
              href="/market"
              className="text-[10px] font-bold uppercase tracking-[0.2em] text-brand hover:text-brand-hover transition-colors underline underline-offset-8"
            >
              EXPLORE FULL DIRECTORY
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <ItemCard
              itemId="ak47-vulcan-fn"
              name="AK-47 | Vulcan"
              type="WEAPON SKIN"
              rarity="Covert"
              currentPrice={942.50}
              priceChange7d={2.4}
              annotation="BULLISH"
              imageUrl="https://community.cloudflare.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpot7HxfDhjxszJemkV092lnYmGmOHLPr7Vn35cppR32-qS99SmiwS3_hU6Y236ctfDclM6YF_U_lXrk-7shZC8u8zBmnVguyZ25S3cmBfihB9SaeM60_veWAtXOnvE/512fx512f"
            />
            <ItemCard
              itemId="awp-asiimov-ft"
              name="AWP | Asiimov"
              type="WEAPON SKIN"
              rarity="Covert"
              currentPrice={164.20}
              priceChange7d={-1.2}
              annotation="NEUTRAL"
              imageUrl="https://community.cloudflare.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpot621FBRw7P7NYjV96t2ykZOfqODmNr_ulWhE18l4mLP--InlgUGw_0VvMNj2IdSRclA-M1_SrFW4krq9hZ_v75_MzCRkvXF34X7cnxa0hUwbafZshvveWAvp4K3Dsw/512fx512f"
            />
            <ItemCard
              itemId="m4a1s-printstream-mw"
              name="M4A1-S | Printstream"
              type="WEAPON SKIN"
              rarity="Covert"
              currentPrice={428.15}
              priceChange7d={5.8}
              annotation="ALPHA"
              imageUrl="https://community.cloudflare.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpou-6kejhjxszFJTwW09Kzm7-FmP7mDLfYkW5u5Mx2gv2P89-m2w3gr0s4ajzycITAdlA7N1vS_gTvyevp1sS0uMzAnXU2vXQm4ivezBa-1RkYarNxxavJGZ6S_vY/512fx512f"
            />
            <ItemCard
              itemId="butterfly-knife-fade-fn"
              name="Butterfly Knife | Fade"
              type="KNIFE"
              rarity="Covert"
              currentPrice={3240.00}
              priceChange7d={0.8}
              annotation="PREMIUM"
              imageUrl="https://community.cloudflare.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpovbSsLQJf1f_BYi59_9S_mYmDkvPLPr7Vn35cppN0i-zEpdX0iwHhqkZuNmilddScclM6aVDWqFa9wr2-1JW1u8zAm3VvunYm43rD30vgoS7N6Q/512fx512f"
            />
          </div>
        </motion.section>

        {/* --- ANALYTICAL ENGINE --- */}
        <motion.section
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.6, ease: EASE }}
          className="mb-32"
        >
          <div className="flex items-end justify-between mb-12">
            <div>
              <span className="font-data text-[10px] font-bold uppercase tracking-[0.3em] text-brand mb-3 block">
                [03] ANALYTICAL_ENGINE
              </span>
              <h2 className="text-3xl font-semibold tracking-tighter text-primary">
                Engineered Insights.
              </h2>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <FeatureWidget
              id="E1"
              title="Time-Series Analysis"
              description="Institutional-grade candle analysis and volume delta tracking across multi-year windows."
              index={0}
            />
            <FeatureWidget
              id="E2"
              title="Wear Spread Logic"
              description="Sophisticated algorithms tracking price spreads across float values and condition tiers."
              index={1}
            />
            <FeatureWidget
              id="E3"
              title="Liquidity Mapping"
              description="Deep-dive into supply dynamics across major skin aggregators to find real buy/sell walls."
              index={2}
            />
            <FeatureWidget
              id="E4"
              title="Portfolio Valuation"
              description="Professional inventory tracking with cost-basis analysis and risk distribution metrics."
              index={3}
            />
          </div>
        </motion.section>
      </main>

      <footer className="py-20 border-t border-border/40">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row justify-between items-start gap-12">
            <div className="max-w-xs">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-8 h-8 rounded-sm border border-border flex items-center justify-center bg-background-secondary">
                  <span className="font-data font-bold text-[8px] text-primary tracking-tighter">CS</span>
                </div>
                <span className="font-semibold text-xs tracking-[0.2em] uppercase text-primary">Data Terminal</span>
              </div>
              <p className="text-xs text-muted leading-relaxed font-medium">
                A high-precision analytical environment for Counter-Strike 2 item speculators.
                Scientific reporting for the modern skin investor.
              </p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-16">
              <FooterGroup title="Platform" links={['Market', 'Portfolio', 'Analytics', 'Trends']} />
              <FooterGroup title="Engine" links={['Documentation', 'API Guide', 'Market Report', 'Status']} />
              <FooterGroup title="Legal" links={['Terms', 'Privacy', 'Cookies']} />
            </div>
          </div>

          <div className="mt-20 pt-12 border-t border-border/20 flex flex-col md:flex-row justify-between gap-6">
            <p className="text-[10px] font-data text-muted uppercase tracking-[0.2em] font-bold">
              &copy; 2026 DATA TERMINAL &mdash; ALL RIGHTS RESERVED.
            </p>
            <div className="flex items-center gap-6">
              <span className="tag-tech">MOD: ANALYTICAL</span>
              <span className="tag-tech">SRC: LIVE_FEED</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

function FeatureWidget({ id, title, description, index }: { id: string; title: string; description: string; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: index * 0.1, ease: EASE }}
      className="widget-block p-8 flex gap-8 group"
    >
      <div className="font-data text-[12px] font-bold text-muted border border-border w-12 h-12 rounded-sm flex items-center justify-center bg-background-tertiary group-hover:text-brand group-hover:border-brand transition-all">
        {id}
      </div>
      <div>
        <h3 className="text-lg font-semibold text-primary mb-3 tracking-tight group-hover:text-brand transition-colors">
          {title}
        </h3>
        <p className="text-sm text-secondary leading-relaxed font-medium">
          {description}
        </p>
      </div>
    </motion.div>
  );
}

function FooterGroup({ title, links }: { title: string; links: string[] }) {
  return (
    <div className="flex flex-col gap-6">
      <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-muted">{title}</span>
      <ul className="flex flex-col gap-3">
        {links.map(link => (
          <li key={link}>
            <Link href="#" className="text-[11px] font-bold text-muted hover:text-brand transition-colors uppercase tracking-widest">
              {link}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
