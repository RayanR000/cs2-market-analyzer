'use client';

import { useState } from 'react';

interface SearchProps {
  onSearch: (query: string) => void;
  placeholder?: string;
}

export default function Search({ onSearch, placeholder = 'SEARCH ASSETS...' }: SearchProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(query);
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="relative group">
        <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
          <svg className="w-4 h-4 text-tertiary group-focus-within:text-white transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            onSearch(e.target.value);
          }}
          placeholder={placeholder}
          className="w-full pl-12 pr-24 py-4 bg-background-tertiary border border-border border-b-border-highlight border-r-border-highlight rounded-sm text-sm text-primary placeholder:text-muted focus:bg-background-secondary transition-all outline-none uppercase tracking-widest font-bold shadow-[inset_0_2px_4px_rgba(0,0,0,0.5)]"
        />
        <div className="absolute inset-y-0 right-4 flex items-center">
          <span className="text-[10px] font-data font-bold text-muted tracking-widest uppercase border border-border px-2 py-1 rounded-sm">
            Terminal
          </span>
        </div>
      </div>
    </form>
  );
}
