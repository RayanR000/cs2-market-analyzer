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
  let indicatorColor = 'var(--text-primary)';
  
  if (isPositive === true) {
    indicatorColor = 'var(--data-up)';
  } else if (isPositive === false) {
    indicatorColor = 'var(--data-down)';
  } else if (highlight === 'secondary') {
    indicatorColor = 'var(--accent-secondary)';
  } else if (highlight === 'accent') {
    indicatorColor = 'var(--accent-primary)';
  }

  return (
    <div className="card-boutique group">
      <div className="flex items-start justify-between mb-4">
        <p className="text-[9px] font-bold uppercase tracking-[0.2em] text-muted">
          {label}
        </p>
        {icon && (
          <div style={{ color: indicatorColor }} className="text-base opacity-30 group-hover:opacity-100 transition-opacity">
            {icon}
          </div>
        )}
      </div>

      <div className="flex items-baseline gap-3">
        <p className="text-3xl font-data font-medium tracking-tighter text-primary">
          {value}
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

      {subvalue && (
        <p className="text-[9px] font-data font-bold text-muted mt-3 uppercase tracking-[0.1em]">
          {subvalue}
        </p>
      )}
    </div>
  );
}
