'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { Header } from '@/components';
import StatCard from '@/components/StatCard';
import ItemCard from '@/components/ItemCard';

export default function Home() {
  return (
    <div className="min-h-screen bg-background-primary selection:bg-accent-primary/30 selection:text-white">
      <Header />

      {/* Hero Section - Machined Terminal */}
      <section className="relative overflow-hidden pt-32 pb-24 border-b border-border shadow-[0_4px_24px_rgba(0,0,0,0.5)]">
        <div className="max-w-7xl mx-auto px-6 relative z-10">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 1, ease: [0.16, 1, 0.3, 1] }}
            className="max-w-4xl"
          >
            <div className="mb-10 flex items-center gap-4">
              <span className="w-12 h-[1px] bg-primary" />
              <span className="font-data text-[10px] font-bold uppercase tracking-[0.4em] text-primary">
                Institutional Data Terminal
              </span>
            </div>

            <h1 className="text-7xl md:text-8xl font-semibold mb-10 tracking-tighter leading-[0.85] text-primary">
              Tactile <br />
              <span className="text-muted">Market Precision.</span>
            </h1>

            <p className="text-xl text-secondary max-w-xl mb-14 leading-relaxed font-medium">
              A custom-machined interface for long-term CS2 speculation. 
              Minimalist by design, industrial by nature.
            </p>

            <div className="flex flex-wrap gap-8">
              <Link
                href="/market"
                className="px-10 py-5 bg-primary text-background-primary font-bold text-xs uppercase tracking-[0.3em] rounded-sm hover:bg-muted transition-all active:scale-95 shadow-md"
              >
                Open Terminal
              </Link>
              <Link
                href="/portfolio"
                className="px-10 py-5 border border-border border-t-border-highlight border-l-border-highlight text-primary font-bold text-xs uppercase tracking-[0.3em] rounded-sm hover:bg-background-secondary transition-all active:scale-95"
              >
                Portfolio
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Market Pulse - Real-time Stats */}
      <section className="py-24 border-b border-border/40 bg-background-secondary/30">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row md:items-end justify-between mb-16 gap-8">
            <div>
              <span className="font-data text-[10px] font-bold uppercase tracking-[0.2em] text-tertiary mb-3 block">
                01 — Market Pulse
              </span>
              <h2 className="text-3xl font-semibold tracking-tight text-primary">
                Current Equilibrium.
              </h2>
            </div>
            <p className="text-sm text-muted max-w-xs font-medium">
              Real-time snapshot of the global CS2 economy across primary trading volumes.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
            <StatCard 
              label="Active Indices" 
              value="14,282" 
              subvalue="Live Trackers" 
              highlight="primary"
            />
            <StatCard 
              label="24H Volume" 
              value="$2.4M" 
              subvalue="Estimated Net" 
              isPositive={true}
              change={4.2}
            />
            <StatCard 
              label="Market Sentiment" 
              value="Neutral" 
              subvalue="Volatility Index" 
              highlight="secondary"
            />
            <StatCard 
              label="Data Points" 
              value="1.2B" 
              subvalue="Historical Logs" 
              highlight="accent"
            />
          </div>
        </div>
      </section>

      {/* Featured Assets - The "What" */}
      <section className="py-24">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row md:items-end justify-between mb-16 gap-8">
            <div>
              <span className="font-data text-[10px] font-bold uppercase tracking-[0.2em] text-tertiary mb-3 block">
                02 — Featured Assets
              </span>
              <h2 className="text-3xl font-semibold tracking-tight text-primary">
                High-Volatility Opportunities.
              </h2>
            </div>
            <Link 
              href="/market" 
              className="text-[10px] font-bold uppercase tracking-[0.2em] text-accent-primary hover:text-white transition-colors"
            >
              View Full Market →
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <ItemCard 
              itemId="ak47-vulcan-fn"
              name="AK-47 | Vulcan"
              type="Weapon Skin"
              rarity="Covert"
              currentPrice={942.50}
              priceChange7d={2.4}
              imageUrl="https://community.cloudflare.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpot7HxfDhjxszJemkV092lnYmGmOHLPr7Vn35cppR32-qS99SmiwS3_hU6Y236ctfDclM6YF_U_lXrk-7shZC8u8zBmnVguyZ25S3cmBfihB9SaeM60_veWAtXOnvE/512fx512f"
            />
            <ItemCard 
              itemId="awp-asiimov-ft"
              name="AWP | Asiimov"
              type="Weapon Skin"
              rarity="Covert"
              currentPrice={164.20}
              priceChange7d={-1.2}
              imageUrl="https://community.cloudflare.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpot621FBRw7P7NYjV96t2ykZOfqODmNr_ulWhE18l4mLP--InlgUGw_0VvMNj2IdSRclA-M1_SrFW4krq9hZ_v75_MzCRkvXF34X7cnxa0hUwbafZshvveWAvp4K3Dsw/512fx512f"
            />
            <ItemCard 
              itemId="m4a1s-printstream-mw"
              name="M4A1-S | Printstream"
              type="Weapon Skin"
              rarity="Covert"
              currentPrice={428.15}
              priceChange7d={5.8}
              imageUrl="https://community.cloudflare.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpou-6kejhjxszFJTwW09Kzm7-FmP7mDLfYkW5u5Mx2gv2P89-m2w3gr0s4ajzycITAdlA7N1vS_gTvyevp1sS0uMzAnXU2vXQm4ivezBa-1RkYarNxxavJGZ6S_vY/512fx512f"
            />
            <ItemCard 
              itemId="butterfly-knife-fade-fn"
              name="Butterfly Knife | Fade"
              type="Knife"
              rarity="Covert"
              currentPrice={3240.00}
              priceChange7d={0.8}
              imageUrl="https://community.cloudflare.steamstatic.com/economy/image/-9a81dlWLwJ2UUGcVs_nsVtzdOEdtWwKGZZLQHTxDZ7I56KU0Zwwo4NUX4oFJZEHLbXH5ApeO4YmlhxYQknCRvCo04DEVlxkKgpovbSsLQJf1f_BYi59_9S_mYmDkvPLPr7Vn35cppN0i-zEpdX0iwHhqkZuNmilddScclM6aVDWqFa9wr2-1JW1u8zAm3VvunYm43rD30vgoS7N6Q/512fx512f"
            />
          </div>
        </div>
      </section>

      {/* Terminal Features */}
      <section className="py-24 bg-background-secondary/20">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row md:items-end justify-between mb-16 gap-8">
            <div>
              <span className="font-data text-[10px] font-bold uppercase tracking-[0.2em] text-tertiary mb-3 block">
                03 — Analytical Depth
              </span>
              <h2 className="text-3xl font-semibold tracking-tight text-primary">
                Engineered for Alpha.
              </h2>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <FeatureBlock 
              title="Time-Series Precision"
              description="Institutional-grade charts with candle analysis, volume delta, and moving averages across 5-year historical windows."
              icon="T01"
            />
            <FeatureBlock 
              title="Wear Convergence"
              description="Sophisticated algorithms tracking price spreads across float values from Factory New to Battle-Scarred."
              icon="T02"
            />
            <FeatureBlock 
              title="Liquidity Analytics"
              description="Deep-dive into supply dynamics across all major skin aggregators to identify real buy/sell walls."
              icon="T03"
            />
            <FeatureBlock 
              title="Portfolio Valuation"
              description="Professional inventory tracking with cost-basis analysis, unrealized P&L, and risk distribution metrics."
              icon="T04"
            />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-24 border-t border-border/40">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row justify-between items-start gap-12">
            <div className="max-w-xs">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-8 h-8 rounded-sm border border-border flex items-center justify-center bg-background-secondary">
                  <span className="font-data font-bold text-[8px] text-accent-primary tracking-tighter">CS2</span>
                </div>
                <span className="font-semibold text-xs tracking-widest uppercase text-primary">Market Analyzer</span>
              </div>
              <p className="text-xs text-muted leading-relaxed">
                A professional-grade analytical tool for Counter-Strike 2 item speculators. 
                Data-driven insights for the modern skin investor.
              </p>
            </div>
            
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-12">
              <FooterGroup title="Platform" links={['Market', 'Portfolio', 'Analytics', 'Trends']} />
              <FooterGroup title="Resources" links={['Documentation', 'API Guide', 'Market Report', 'Status']} />
              <FooterGroup title="Legal" links={['Terms', 'Privacy', 'Cookies']} />
            </div>
          </div>
          
          <div className="mt-24 pt-12 border-t border-border/20 flex flex-col md:flex-row justify-between gap-6">
            <p className="text-[10px] font-data text-muted uppercase tracking-widest">
              © 2026 CS2 MARKET ANALYZER — ALL RIGHTS RESERVED.
            </p>
            <p className="text-[10px] font-data text-muted uppercase tracking-widest">
              DESIGNED FOR THE MODERN SPECULATOR.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

function FeatureBlock({ title, description, icon }: { title: string; description: string; icon: string }) {
  return (
    <div className="card-boutique group">
      <div className="flex items-start gap-6">
        <div className="font-data text-[10px] font-bold text-accent-primary border border-accent-primary/20 w-10 h-10 rounded-sm flex items-center justify-center bg-accent-primary/5 group-hover:bg-accent-primary group-hover:text-background-primary transition-all">
          {icon}
        </div>
        <div>
          <h3 className="text-base font-semibold text-primary mb-2 group-hover:text-accent-primary transition-colors">
            {title}
          </h3>
          <p className="text-sm text-secondary leading-relaxed">
            {description}
          </p>
        </div>
      </div>
    </div>
  );
}

function FooterGroup({ title, links }: { title: string; links: string[] }) {
  return (
    <div className="flex flex-col gap-4">
      <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-tertiary">{title}</span>
      <ul className="flex flex-col gap-2">
        {links.map(link => (
          <li key={link}>
            <Link href="#" className="text-xs text-muted hover:text-accent-primary transition-colors">
              {link}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
