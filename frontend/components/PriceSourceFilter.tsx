'use client';

import React from 'react';
import styles from './PriceSourceFilter.module.css';

interface PriceSourceFilterProps {
  selectedSources: string[];
  onSourceChange: (sources: string[]) => void;
}

const AVAILABLE_SOURCES = [
  { id: 'steam', label: 'Steam', color: '#1b2838' },
  { id: 'skinport', label: 'Skinport', color: '#9d2b3f' },
  { id: 'dmarket', label: 'DMarket', color: '#00d4ff' }
];

export default function PriceSourceFilter({
  selectedSources,
  onSourceChange
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
        {AVAILABLE_SOURCES.map(source => (
          <button
            key={source.id}
            className={`${styles.toggle} ${
              selectedSources.includes(source.id) ? styles.active : ''
            }`}
            onClick={() => handleToggle(source.id)}
            style={{
              borderColor: selectedSources.includes(source.id) ? source.color : undefined,
              backgroundColor: selectedSources.includes(source.id)
                ? `${source.color}15`
                : undefined
            }}
          >
            {source.label}
          </button>
        ))}
      </div>
    </div>
  );
}
