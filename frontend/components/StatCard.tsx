'use client';

interface StatCardProps {
  label: string;
  value: string | number;
  highlight?: 'primary' | 'secondary' | 'accent';
  isPositive?: boolean;
  change?: number;
  subvalue?: string;
  icon?: React.ReactNode;
}

export default function StatCard({
  label,
  value,
  highlight = 'primary',
  isPositive,
  change,
  subvalue,
  icon
}: StatCardProps) {
  let accentColor = 'var(--text-primary)';
  
  if (isPositive === true) {
    accentColor = 'var(--data-up)';
  } else if (isPositive === false) {
    accentColor = 'var(--data-down)';
  } else if (highlight === 'secondary') {
    accentColor = 'var(--accent-secondary)';
  } else if (highlight === 'accent') {
    accentColor = 'var(--accent-primary)';
  }

  return (
    <div className="card-boutique group">
      <div className="flex items-start justify-between mb-3">
        <p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-tertiary">
          {label}
        </p>
        {icon && (
          <div style={{ color: accentColor }} className="text-lg opacity-40 group-hover:opacity-100 transition-opacity">
            {icon}
          </div>
        )}
      </div>

      <div className="flex items-baseline gap-3">
        <p className="text-3xl font-data font-medium tracking-tight text-primary">
          {value}
        </p>
        
        {change !== undefined && (
          <span
            className="text-xs font-data font-semibold"
            style={{
              color: change >= 0 ? 'var(--data-up)' : 'var(--data-down)'
            }}
          >
            {change >= 0 ? '+' : ''}{change.toFixed(1)}%
          </span>
        )}
      </div>

      {subvalue && (
        <p className="text-[11px] font-data text-muted mt-2 uppercase tracking-wide">
          {subvalue}
        </p>
      )}
    </div>
  );
}
