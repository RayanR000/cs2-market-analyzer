'use client';

interface StatCardProps {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon?: string;
}

export default function StatCard({
  title,
  value,
  change,
  changeLabel = '7d',
  icon
}: StatCardProps) {
  const changeColor = (change ?? 0) >= 0 ? 'text-green-600' : 'text-red-600';

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-start">
        <div>
          <p className="text-gray-500 text-sm font-medium">{title}</p>
          <p className="text-2xl md:text-3xl font-bold text-gray-900 mt-2">{value}</p>
          {change !== undefined && (
            <p className={`text-sm font-medium mt-2 ${changeColor}`}>
              {change >= 0 ? '↑' : '↓'} {Math.abs(change).toFixed(2)}% {changeLabel}
            </p>
          )}
        </div>
        {icon && (
          <div className="text-3xl opacity-20">{icon}</div>
        )}
      </div>
    </div>
  );
}
