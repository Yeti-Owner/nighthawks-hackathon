'use client';

import LiquidCard from './LiquidCard';

interface KpiCardProps {
    value: string;
    label: string;
    trend: string;
    trendType: 'positive' | 'negative' | 'neutral';
    delay?: number;
}

export default function KpiCard({ value, label, trend, trendType, delay = 0 }: KpiCardProps) {
    const pillClass =
        trendType === 'positive' ? 'pill-positive' :
            trendType === 'negative' ? 'pill-negative' :
                'pill-neutral';

    return (
        <div
            className="animate-fade-up"
            style={{ animationDelay: `${delay}ms` }}
        >
            <LiquidCard
                className="hover:translate-y-[-2px]"
                padding="p-8"
            >
                <div className="flex flex-col" style={{ gap: 8 }}>
                    {/* KPI Number */}
                    <span
                        style={{
                            fontFamily: 'var(--font-serif), serif',
                            fontSize: 56,
                            fontWeight: 400,
                            letterSpacing: '-0.03em',
                            lineHeight: 1,
                            color: '#1A1A1A',
                        }}
                    >
                        {value}
                    </span>

                    {/* Label */}
                    <span className="micro-label">
                        {label}
                    </span>

                    {/* Trend Pill */}
                    <span className={`pill ${pillClass}`} style={{ alignSelf: 'flex-start', marginTop: 8 }}>
                        {trend}
                    </span>
                </div>
            </LiquidCard>
        </div>
    );
}
