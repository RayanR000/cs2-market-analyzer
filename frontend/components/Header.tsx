'use client';

import Link from 'next/link';
import { useUser } from '@/lib/UserContext';
import { getLoginUrl } from '@/lib/api';

export default function Header() {
  const { user, loading, logout } = useUser();

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background-primary/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex justify-between items-center">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-9 h-9 rounded-sm border border-border flex items-center justify-center bg-background-secondary group-hover:border-accent-primary transition-colors">
              <span className="font-data font-bold text-[10px] text-accent-primary tracking-tighter">CS2</span>
            </div>
            <div className="flex flex-col">
              <span className="font-semibold text-sm leading-none tracking-tight text-primary">
                MARKET
              </span>
              <span className="font-data text-[10px] text-tertiary tracking-widest uppercase mt-0.5">
                Analyzer
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
                  <span className="text-xs font-semibold text-primary">{user.username}</span>
                  <button 
                    onClick={() => logout()}
                    className="text-[10px] text-tertiary hover:text-accent-primary transition-colors uppercase tracking-widest"
                  >
                    Logout
                  </button>
                </div>
                {user.avatar_url && (
                  <img 
                    src={user.avatar_url} 
                    alt={user.username} 
                    className="w-8 h-8 rounded-sm border border-border shadow-sm grayscale hover:grayscale-0 transition-all"
                  />
                )}
              </div>
            ) : (
              <a 
                href={getLoginUrl()}
                className="flex items-center gap-2.5 px-5 py-2 rounded-sm text-[11px] font-bold uppercase tracking-widest transition-all bg-accent-primary text-background-primary hover:bg-white hover:text-background-primary"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M11.979 0C5.678 0 .511 4.86.022 11.037l6.432 2.654c.545-.371 1.203-.59 1.912-.59.063 0 .125.004.188.006l2.83-4.146V8.92c0-2.607 2.113-4.72 4.72-4.72 2.607 0 4.72 2.113 4.72 4.72 0 2.607-2.113 4.72-4.72 4.72-.173 0-.341-.013-.506-.035l-4.14 2.831c.002.063.006.125.006.188 0 2.114-1.714 3.828-3.828 3.828-1.55 0-2.891-.918-3.504-2.236L0 15.352c.866 4.887 5.152 8.648 10.285 8.648 5.756 0 10.422-4.666 10.422-10.422C20.707 7.822 16.784 3.322 11.979 0zm2.741 12.01c-1.706 0-3.091-1.385-3.091-3.09 0-1.706 1.385-3.091 3.091-3.091 1.706 0 3.091 1.385 3.091 3.091 0 1.705-1.385 3.09-3.091 3.09zm-3.091-3.09c0 .416.084.81.233 1.168l-2.73 3.999c-.198-.016-.399-.026-.603-.026-1.127 0-2.146.486-2.854 1.261l-5.32-2.193c.312-4.143 3.49-7.447 7.554-8.156.002.016.006.033.006.05v.001zM10.285 17.548c0 1.312-1.063 2.375-2.375 2.375-1.312 0-2.375-1.063-2.375-2.375s1.063-2.375 2.375-2.375c.063 0 .125.004.188.006l2.193-3.193v.001c.416.486 1.035.789 1.724.789h.001c-.149-.358-.233-.752-.233-1.168s.084-.81.233-1.168h-.001c-.689 0-1.308.303-1.724.789l-2.193-3.193c-.063.002-.125.006-.188.006z"/>
                </svg>
                Authenticate
              </a>
            )}
          </div>
        </div>
      </div>
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
