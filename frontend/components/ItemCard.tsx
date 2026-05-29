'use client';

import Link from 'next/link';

interface ItemCardProps {
  itemId: string;
  name: string;
  type: string;
  imageUrl?: string;
  currentPrice?: number;
  priceChange7d?: number;
  rarity?: 'Consumer' | 'Industrial' | 'Mil-Spec' | 'Restricted' | 'Classified' | 'Covert' | 'Contraband';
}

export default function ItemCard({
  itemId,
  name,
  type,
  imageUrl,
  currentPrice,
  priceChange7d,
  rarity = 'Mil-Spec'
}: ItemCardProps) {
  const rarityColors = {
    'Consumer': 'oklch(70% 0.02 260)',
    'Industrial': 'oklch(60% 0.04 240)',
    'Mil-Spec': 'oklch(55% 0.06 250)',
    'Restricted': 'oklch(50% 0.08 280)',
    'Classified': 'oklch(55% 0.08 320)',
    'Covert': 'oklch(60% 0.1 20)',
    'Contraband': 'oklch(75% 0.1 60)'
  };

  const accentColor = rarityColors[rarity] || rarityColors['Mil-Spec'];

  return (
    <Link href={`/items/${itemId}`} className="card-boutique group block relative overflow-hidden">
      {/* Background Rarity Glow (Extremely Subtle) */}
      <div 
        className="absolute -top-24 -right-24 w-48 h-48 blur-[100px] opacity-5 group-hover:opacity-10 transition-opacity"
        style={{ backgroundColor: accentColor }}
      />

      <div className="relative z-10">
        <div className="flex justify-between items-start mb-4">
          <div className="flex flex-col">
            <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-muted mb-1">
              {type}
            </span>
            <h3 className="font-semibold text-sm text-primary group-hover:text-white transition-colors line-clamp-1 tracking-tight">
              {name}
            </h3>
          </div>
          <div 
            className="w-1.5 h-1.5 rounded-full" 
            style={{ backgroundColor: accentColor, boxShadow: `0 0 10px ${accentColor}` }}
          />
        </div>

        {/* Asset Display */}
        <div className="aspect-square w-full mb-6 flex items-center justify-center p-6 bg-background-tertiary/50 rounded-sm border border-border group-hover:border-accent-primary transition-all duration-500">
          {imageUrl ? (
            <img 
              src={imageUrl} 
              alt={name} 
              className="max-w-full max-h-full object-contain drop-shadow-[0_12px_24px_rgba(0,0,0,0.7)] group-hover:scale-105 transition-transform duration-700 ease-out"
            />
          ) : (
            <div className="text-muted text-[10px] font-data uppercase tracking-[0.3em]">No Asset</div>
          )}
        </div>

        <div className="flex items-end justify-between">
          <div className="flex flex-col">
            <span className="text-[9px] font-bold text-muted uppercase tracking-[0.2em] mb-1">
              VALUATION
            </span>
            <p className="text-xl font-data font-medium text-primary tracking-tighter">
              {currentPrice !== undefined ? `$${currentPrice.toFixed(2)}` : 'N/A'}
            </p>
          </div>

          {priceChange7d !== undefined && (
            <div className="flex flex-col items-end">
              <span className="text-[9px] font-bold text-muted uppercase tracking-[0.2em] mb-1">
                7D DELTA
              </span>
              <p 
                className="text-xs font-data font-bold"
                style={{ color: priceChange7d >= 0 ? 'var(--data-up)' : 'var(--data-down)' }}
              >
                {priceChange7d >= 0 ? '+' : ''}{priceChange7d.toFixed(1)}%
              </p>
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}
