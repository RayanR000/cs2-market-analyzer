'use client';

import CountUpNumber from './CountUpNumber';

interface StatCardProps {
  label: string;
  value: number;
  highlight?: 'primary' | 'secondary' | 'accent';
  isPositive?: boolean;
  change?: number;
  subvalue?: string;
  unit?: string;
  annotation?: string;
}

export default function StatCard({
  label,
  value,
  highlight = 'primary',
  isPositive,
  change,
  subvalue,
  unit = '',
  annotation
}: StatCardProps) {
  return (
    <div className="widget-block p-5 flex flex-col justify-between relative overflow-hidden group">
      {/* Top Scan Line (Subtle Hover) */}
      <div className="absolute top-0 left-0 w-full h-[1px] bg-accent-primary scale-x-0 group-hover:scale-x-100 transition-transform duration-500 origin-left opacity-30" />

      <div>
        <div className="flex items-start justify-between mb-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-muted">
            {label}
          </p>
          {annotation && (
            <span className="tag-tech opacity-0 group-hover:opacity-100 transition-opacity">
              {annotation}
            </span>
          )}
        </div>

        <div className="flex items-baseline gap-2">
          <p className="text-3xl font-data font-medium tracking-tighter text-primary">
            <CountUpNumber 
              from={0} 
              to={value} 
              decimals={value % 1 === 0 ? 0 : 2}
              formatFn={(v) => `${unit}${v.toLocaleString()}`}
            />
          </p>
          
          {change !== undefined && (
            <span
              className="text-xs font-data font-bold"
              style={{
                color: change >= 0 ? 'var(--data-up)' : 'var(--data-down)'
              }}
            >
              {change >= 0 ? '+' : ''}{change.toFixed(1)}%
            </span>
          )}
        </div>
      </div>

      {subvalue && (
        <p className="text-[10px] font-data font-bold text-muted mt-4 uppercase tracking-[0.1em]">
          {subvalue}
        </p>
      )}
    </div>
  );
}
