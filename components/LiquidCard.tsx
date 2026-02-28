import React from 'react';

interface LiquidCardProps {
    children: React.ReactNode;
    className?: string;
    padding?: string;
}

export default function LiquidCard({ children, className = '', padding = 'p-8' }: LiquidCardProps) {
    return (
        <div
            className={`liquid-glass ${padding} ${className}`}
            style={{ transition: 'all 200ms cubic-bezier(0.25, 1, 0.5, 1)' }}
        >
            <div className="liquid-glass-highlight" />
            {children}
        </div>
    );
}
