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
    'Consumer': 'oklch(70% 0.05 260)',
    'Industrial': 'oklch(60% 0.1 240)',
    'Mil-Spec': 'oklch(55% 0.15 250)',
    'Restricted': 'oklch(50% 0.2 280)',
    'Classified': 'oklch(55% 0.2 320)',
    'Covert': 'oklch(60% 0.2 20)',
    'Contraband': 'oklch(75% 0.15 60)'
  };

  const accentColor = rarityColors[rarity] || rarityColors['Mil-Spec'];

  return (
    <Link href={`/items/${itemId}`} className="card-boutique group block relative overflow-hidden">
      {/* Background Rarity Glow (Subtle) */}
      <div 
        className="absolute -top-24 -right-24 w-48 h-48 blur-[80px] opacity-10 group-hover:opacity-20 transition-opacity"
        style={{ backgroundColor: accentColor }}
      />

      <div className="relative z-10">
        <div className="flex justify-between items-start mb-4">
          <div className="flex flex-col">
            <span className="text-[10px] font-bold uppercase tracking-widest text-tertiary mb-1">
              {type}
            </span>
            <h3 className="font-semibold text-sm text-primary group-hover:text-accent-primary transition-colors line-clamp-1">
              {name}
            </h3>
          </div>
          <div 
            className="w-2 h-2 rounded-full" 
            style={{ backgroundColor: accentColor, boxShadow: `0 0 8px ${accentColor}` }}
          />
        </div>

        {/* Asset Display */}
        <div className="aspect-square w-full mb-6 flex items-center justify-center p-4 bg-background-primary/30 rounded-sm border border-border/50 group-hover:border-border transition-colors">
          {imageUrl ? (
            <img 
              src={imageUrl} 
              alt={name} 
              className="max-w-full max-h-full object-contain drop-shadow-[0_8px_16px_rgba(0,0,0,0.5)] group-hover:scale-110 transition-transform duration-500"
            />
          ) : (
            <div className="text-muted text-xs font-data uppercase tracking-widest">No Image</div>
          )}
        </div>

        <div className="flex items-end justify-between">
          <div className="flex flex-col">
            <span className="text-[10px] font-semibold text-tertiary uppercase tracking-wider mb-1">
              Current Price
            </span>
            <p className="text-xl font-data font-medium text-primary">
              {currentPrice !== undefined ? `$${currentPrice.toFixed(2)}` : 'N/A'}
            </p>
          </div>

          {priceChange7d !== undefined && (
            <div className="flex flex-col items-end">
              <span className="text-[10px] font-semibold text-tertiary uppercase tracking-wider mb-1">
                7D Change
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
