'use client';

import React from 'react';
import styles from './PriceSourceFilter.module.css';

interface PriceSourceFilterProps {
  selectedSources: string[];
  onSourceChange: (sources: string[]) => void;
  availableSources?: string[];
}

const SOURCE_META: Record<string, { label: string; color: string }> = {
  steam: { label: 'Steam', color: '#1b2838' },
  csfloat: { label: 'CSFloat', color: '#ff6b35' },
};

const DEFAULT_SOURCES = [
  'steam',
  'csfloat',
];

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
    <div className={styles.filterContainer}>
      <label className={styles.label}>Price Sources</label>
      <div className={styles.toggleGroup}>
        {availableSources.map(sourceId => {
          const source = SOURCE_META[sourceId] ?? { label: sourceId, color: '#6b7280' };

          return (
            <button
              key={sourceId}
              className={`${styles.toggle} ${
                selectedSources.includes(sourceId) ? styles.active : ''
              }`}
              onClick={() => handleToggle(sourceId)}
              style={{
                borderColor: selectedSources.includes(sourceId) ? source.color : undefined,
                backgroundColor: selectedSources.includes(sourceId)
                  ? `${source.color}15`
                  : undefined,
              }}
            >
              {source.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
