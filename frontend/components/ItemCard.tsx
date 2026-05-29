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
  annotation?: string;
}

export default function ItemCard({
  itemId,
  name,
  type,
  imageUrl,
  currentPrice,
  priceChange7d,
  rarity = 'Mil-Spec',
  annotation
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

  const rarityColor = rarityColors[rarity] || rarityColors['Mil-Spec'];

  return (
    <Link href={`/items/${itemId}`} className="widget-block p-5 block group relative overflow-hidden transition-all duration-300">
      {/* Background Accent Glow (Subtle) */}
      <div 
        className="absolute -top-24 -right-24 w-48 h-48 blur-[80px] bg-white opacity-0 group-hover:opacity-[0.03] transition-opacity duration-500"
      />

      <div className="relative z-10 h-full flex flex-col justify-between">
        <div>
          <div className="flex justify-between items-start mb-4">
            <div className="flex flex-col">
              <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-muted mb-1">
                {type}
              </span>
              <h3 className="font-semibold text-sm text-primary group-hover:text-white transition-colors line-clamp-1 tracking-tight">
                {name}
              </h3>
            </div>
            <div className="flex items-center gap-2">
              {annotation && (
                <span className="tag-tech opacity-0 group-hover:opacity-100 transition-opacity">
                  {annotation}
                </span>
              )}
              <div 
                className="w-1.5 h-1.5 rounded-full" 
                style={{ backgroundColor: rarityColor, boxShadow: `0 0 10px ${rarityColor}` }}
              />
            </div>
          </div>

          {/* Asset Display */}
          <div className="aspect-square w-full mb-6 flex items-center justify-center p-6 bg-background-tertiary/50 rounded-sm border border-border group-hover:border-border-accent transition-all duration-500">
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
        </div>

        <div className="flex items-end justify-between mt-auto">
          <div className="flex flex-col">
            <span className="text-[9px] font-bold text-muted uppercase tracking-[0.2em] mb-1">
              EST. VALUE
            </span>
            <p className="text-xl font-data font-medium text-primary tracking-tighter group-hover:text-white">
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
