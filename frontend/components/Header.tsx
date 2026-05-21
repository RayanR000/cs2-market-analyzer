'use client';

import Link from 'next/link';
import { useUser } from '@/lib/UserContext';
import { getLoginUrl } from '@/lib/api';

export default function Header() {
  const { user, loading, logout } = useUser();

  return (
    <header className="sticky top-0 z-50 border-b" style={{
      borderColor: 'var(--border)',
      backgroundColor: 'var(--background-secondary)',
      boxShadow: '0 1px 3px rgba(0,0,0,0.3)'
    }}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex justify-between items-center">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="w-8 h-8 rounded border-2 flex items-center justify-center" style={{
              borderColor: 'var(--accent-primary)',
              backgroundColor: 'var(--bg-accent-subtle)'
            }}>
              <span className="font-bold text-xs" style={{ color: 'var(--accent-primary)' }}>CS2</span>
            </div>
            <span className="font-semibold" style={{ color: 'var(--text-primary)', fontSize: '16px' }}>
              CS2
            </span>
            <span className="hidden sm:inline" style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
              Market Analyzer
            </span>
          </Link>

          <nav className="hidden md:flex gap-12">
            <NavLink href="/" label="Home" />
            <NavLink href="/market" label="Market" />
            <NavLink href="/portfolio" label="Portfolio" />
          </nav>

          <div className="flex items-center gap-4">
            {loading ? (
              <div className="w-8 h-8 rounded-full animate-pulse bg-gray-700" />
            ) : user ? (
              <div className="flex items-center gap-3">
                <div className="flex flex-col items-end hidden sm:flex">
                  <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{user.username}</span>
                  <button 
                    onClick={() => logout()}
                    className="text-xs hover:underline" 
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    Logout
                  </button>
                </div>
                {user.avatar_url && (
                  <img 
                    src={user.avatar_url} 
                    alt={user.username} 
                    className="w-8 h-8 rounded-full border border-gray-600 shadow-sm"
                  />
                )}
              </div>
            ) : (
              <a 
                href={getLoginUrl()}
                className="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all hover:opacity-90 active:scale-95"
                style={{ 
                  backgroundColor: '#171a21', 
                  color: '#ffffff',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
                }}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M11.979 0C5.678 0 .511 4.86.022 11.037l6.432 2.654c.545-.371 1.203-.59 1.912-.59.063 0 .125.004.188.006l2.83-4.146V8.92c0-2.607 2.113-4.72 4.72-4.72 2.607 0 4.72 2.113 4.72 4.72 0 2.607-2.113 4.72-4.72 4.72-.173 0-.341-.013-.506-.035l-4.14 2.831c.002.063.006.125.006.188 0 2.114-1.714 3.828-3.828 3.828-1.55 0-2.891-.918-3.504-2.236L0 15.352c.866 4.887 5.152 8.648 10.285 8.648 5.756 0 10.422-4.666 10.422-10.422C20.707 7.822 16.784 3.322 11.979 0zm2.741 12.01c-1.706 0-3.091-1.385-3.091-3.09 0-1.706 1.385-3.091 3.091-3.091 1.706 0 3.091 1.385 3.091 3.091 0 1.705-1.385 3.09-3.091 3.09zm-3.091-3.09c0 .416.084.81.233 1.168l-2.73 3.999c-.198-.016-.399-.026-.603-.026-1.127 0-2.146.486-2.854 1.261l-5.32-2.193c.312-4.143 3.49-7.447 7.554-8.156.002.016.006.033.006.05v.001zM10.285 17.548c0 1.312-1.063 2.375-2.375 2.375-1.312 0-2.375-1.063-2.375-2.375s1.063-2.375 2.375-2.375c.063 0 .125.004.188.006l2.193-3.193v.001c.416.486 1.035.789 1.724.789h.001c-.149-.358-.233-.752-.233-1.168s.084-.81.233-1.168h-.001c-.689 0-1.308.303-1.724.789l-2.193-3.193c-.063.002-.125.006-.188.006z"/>
                </svg>
                Sign in with Steam
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
      className="relative text-sm font-medium transition-all duration-200 group"
      style={{ color: 'var(--text-secondary)' }}
    >
      {label}
      <span
        className="absolute bottom-0 left-0 w-0 h-0.5 transition-all duration-200 group-hover:w-full"
        style={{ backgroundColor: 'var(--accent-primary)' }}
      />
    </Link>
  );
}
