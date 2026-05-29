'use client';

import Link from 'next/link';
import { useUser } from '@/lib/UserContext';
import { getLoginUrl } from '@/lib/api';

export default function Header() {
  const { user, loading, logout } = useUser();

  return (
    <header className="sticky top-0 z-50 bg-background-primary/95 backdrop-blur-sm">
      <div className="progress-line" />
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex justify-between items-center">
          <Link href="/" className="flex items-center gap-4 group">
            <div className="w-8 h-8 rounded-sm border border-border flex items-center justify-center bg-background-secondary transition-all">
              <span className="font-data font-bold text-[10px] text-primary tracking-tighter">CS</span>
            </div>
            <div className="flex flex-col">
              <span className="font-semibold text-sm leading-none tracking-tight text-primary">
                DATA TERMINAL
              </span>
              <span className="font-data text-[9px] text-muted tracking-[0.2em] uppercase mt-1">
                Analytical Report
              </span>
            </div>
          </Link>

          <nav className="hidden md:flex gap-10">
            <NavLink href="/market" label="MARKET" />
            <NavLink href="/portfolio" label="PORTFOLIO" />
          </nav>

          <div className="flex items-center gap-6">
            {loading ? (
              <div className="w-8 h-8 rounded-full animate-pulse bg-surface" />
            ) : user ? (
              <div className="flex items-center gap-4">
                <div className="flex flex-col items-end hidden sm:flex">
                  <span className="text-[11px] font-bold text-primary tracking-tight">{user.username}</span>
                  <button 
                    onClick={() => logout()}
                    className="text-[9px] text-muted hover:text-primary transition-colors uppercase tracking-[0.2em]"
                  >
                    Logout
                  </button>
                </div>
                {user.avatar_url && (
                  <img 
                    src={user.avatar_url} 
                    alt={user.username} 
                    className="w-8 h-8 rounded-sm border border-border grayscale hover:grayscale-0 transition-all"
                  />
                )}
              </div>
            ) : (
              <a 
                href={getLoginUrl()}
                className="flex items-center gap-3 px-5 py-2 rounded-sm text-[11px] font-bold uppercase tracking-widest transition-all bg-primary text-background-primary hover:bg-white"
              >
                <img 
                  src="/steam-logo.png" 
                  alt="Steam" 
                  className="w-4 h-4 invert group-hover/steam:invert-0 transition-all"
                />
                AUTHENTICATE
              </a>
            )}
          </div>
        </div>
      </div>
      <div className="border-b border-border/60" />
    </header>
  );
}

function NavLink({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="relative text-[11px] font-bold uppercase tracking-[0.2em] transition-all duration-300 group text-secondary hover:text-primary"
    >
      {label}
      <span className="absolute -bottom-1 left-0 w-0 h-[1px] transition-all duration-300 group-hover:w-full bg-accent-primary" />
    </Link>
  );
}
