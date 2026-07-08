'use client';

import React from 'react';

interface PriceSourceFilterProps {
  selectedSources: string[];
  onSourceChange: (sources: string[]) => void;
  availableSources?: string[];
}

const SOURCE_META: Record<string, { label: string; color: string }> = {
  aggregator_sync: { label: 'Live', color: 'var(--brand)' },
  market_csgo: { label: 'Market.CSGO', color: 'oklch(65% 0.14 250)' },
  steam_historical: { label: 'Steam (weekly)', color: 'oklch(70% 0 0)' },
  steam_batch: { label: 'Steam', color: 'oklch(70% 0 0)' },
  steam: { label: 'Steam', color: 'oklch(70% 0 0)' },
  csfloat: { label: 'CSFloat', color: 'var(--brand)' },
};

const DEFAULT_SOURCES = ['aggregator_sync'];

export default function PriceSourceFilter({
  selectedSources,
  onSourceChange,
  availableSources = DEFAULT_SOURCES,
}: PriceSourceFilterProps) {
  const handleToggle = (sourceId: string) => {
    if (selectedSources.includes(sourceId)) {
      onSourceChange(selectedSources.filter(s => s !== sourceId));
    } else {
      onSourceChange([...selectedSources, sourceId]);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <span className="text-[10px] font-semibold uppercase tracking-[0.15em] text-muted">Price Sources</span>
      <div className="flex gap-1.5 flex-wrap">
        {availableSources.map(sourceId => {
          const source = SOURCE_META[sourceId] ?? { label: sourceId, color: 'oklch(50% 0 0)' };
          const isActive = selectedSources.includes(sourceId);

          return (
            <button
              key={sourceId}
              onClick={() => handleToggle(sourceId)}
              className={`px-3 py-1.5 text-xs font-bold uppercase tracking-widest rounded-sm border transition-all duration-200 ${
                isActive
                  ? 'text-primary border-current'
                  : 'text-secondary border-border hover:bg-surface-hover hover:border-accent-primary'
              }`}
              style={isActive ? { borderColor: source.color, color: source.color, backgroundColor: `color-mix(in oklch, ${source.color} 8%, transparent)` } : undefined}
            >
              {source.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
