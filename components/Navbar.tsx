'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth0 } from '@auth0/auth0-react';

const navLinks = [
    { href: '/', label: 'Overview' },
    { href: '/stats', label: 'Statistics' },
];

export default function Navbar() {
    const pathname = usePathname();
    const { isAuthenticated, loginWithRedirect, logout, user, isLoading } = useAuth0();

    return (
        <nav
            className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between"
            style={{
                height: 64,
                padding: '0 48px',
                background: 'rgba(249, 248, 245, 0.85)',
                backdropFilter: 'blur(16px)',
                WebkitBackdropFilter: 'blur(16px)',
                borderBottom: '1px solid rgba(0, 0, 0, 0.06)',
            }}
        >
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2" style={{ textDecoration: 'none' }}>
                <div
                    style={{
                        width: 3,
                        height: 24,
                        background: '#D7C3B3',
                        borderRadius: 2,
                    }}
                />
                <span
                    style={{
                        fontFamily: 'var(--font-sans), sans-serif',
                        fontSize: 13,
                        fontWeight: 600,
                        letterSpacing: '0.15em',
                        textTransform: 'uppercase' as const,
                        color: '#1A1A1A',
                    }}
                >
                    AURELIUS
                </span>
            </Link>

            {/* Center Nav Links */}
            <div className="hidden md:flex items-center" style={{ gap: 32 }}>
                {navLinks.map((link) => (
                    <Link
                        key={link.href}
                        href={link.href}
                        style={{
                            fontFamily: 'var(--font-sans), sans-serif',
                            fontSize: 13,
                            fontWeight: 500,
                            color: pathname === link.href ? '#1A1A1A' : '#666666',
                            textDecoration: 'none',
                            transition: 'color 200ms cubic-bezier(0.25, 1, 0.5, 1)',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.color = '#1A1A1A')}
                        onMouseLeave={(e) => {
                            if (pathname !== link.href) {
                                e.currentTarget.style.color = '#666666';
                            }
                        }}
                    >
                        {link.label}
                    </Link>
                ))}
            </div>

            {/* Auth Actions */}
            <div className="flex items-center gap-4">
                {!isLoading && (
                    isAuthenticated ? (
                        <>
                            <span
                                style={{
                                    fontSize: 12,
                                    color: '#666666',
                                    fontFamily: 'var(--font-sans), sans-serif',
                                    fontWeight: 500
                                }}
                            >
                                {user?.email}
                            </span>
                            <button
                                className="btn-primary"
                                style={{ height: 40, padding: '0 24px', fontSize: 11, cursor: 'pointer' }}
                                onClick={() => logout({ logoutParams: { returnTo: typeof window !== 'undefined' ? window.location.origin : '' } })}
                            >
                                Logout
                            </button>
                        </>
                    ) : (
                        <>
                            <button
                                style={{
                                    height: 40,
                                    padding: '0 24px',
                                    fontSize: 11,
                                    cursor: 'pointer',
                                    background: 'transparent',
                                    border: '1px solid #A8A9AD',
                                    color: '#1A1A1A',
                                    fontWeight: 600,
                                    borderRadius: 4
                                }}
                                onClick={() => loginWithRedirect({ authorizationParams: { screen_hint: 'signup' } })}
                            >
                                Register
                            </button>
                            <button
                                className="btn-primary"
                                style={{ height: 40, padding: '0 24px', fontSize: 11, cursor: 'pointer' }}
                                onClick={() => loginWithRedirect()}
                            >
                                Login
                            </button>
                        </>
                    )
                )}
            </div>
        </nav>
    );
}
