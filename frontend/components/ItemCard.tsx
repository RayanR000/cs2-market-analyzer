'use client';

interface ItemCardProps {
  itemId: string;
  name: string;
  type: 'skin' | 'case' | 'sticker';
  currentPrice?: number;
  priceChange7d?: number;
  trendDirection?: 'bullish' | 'neutral' | 'bearish';
}

export default function ItemCard({
  itemId,
  name,
  type,
  currentPrice,
  priceChange7d,
  trendDirection = 'neutral'
}: ItemCardProps) {
  const typeColors = {
    skin: 'bg-purple-100 text-purple-800',
    case: 'bg-blue-100 text-blue-800',
    sticker: 'bg-green-100 text-green-800'
  };

  const trendColors = {
    bullish: 'text-green-600',
    neutral: 'text-gray-600',
    bearish: 'text-red-600'
  };

  const changeColor = (priceChange7d ?? 0) >= 0 ? 'text-green-600' : 'text-red-600';

  return (
    <div className="bg-white rounded-lg shadow hover:shadow-md transition-shadow p-4 cursor-pointer">
      <div className="flex justify-between items-start mb-3">
        <h3 className="font-semibold text-lg text-gray-900 line-clamp-2">{name}</h3>
        <span className={`px-2 py-1 rounded text-xs font-medium ${typeColors[type]}`}>
          {type.toUpperCase()}
        </span>
      </div>

      {currentPrice !== undefined && (
        <div className="mb-3">
          <p className="text-2xl font-bold text-gray-900">
            ${currentPrice.toFixed(2)}
          </p>
          {priceChange7d !== undefined && (
            <p className={`text-sm font-medium ${changeColor}`}>
              {priceChange7d >= 0 ? '+' : ''}{priceChange7d.toFixed(2)}% (7d)
            </p>
          )}
        </div>
      )}

      {trendDirection && (
        <div className={`text-sm font-medium ${trendColors[trendDirection]}`}>
          {trendDirection.charAt(0).toUpperCase() + trendDirection.slice(1)}
        </div>
      )}

      <div className="mt-3 pt-3 border-t">
        <p className="text-xs text-gray-500">ID: {itemId}</p>
      </div>
    </div>
  );
}
