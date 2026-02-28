'use client';

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { useStatsData } from '../../lib/DataContext';

function CustomTooltip({ active, payload, totalInterruptions }: any) {
    if (!active || !payload?.length) return null;
    const { name, value, color } = payload[0].payload;
    const pct = totalInterruptions > 0 ? Math.round((value / totalInterruptions) * 100) : 0;
    return (
        <div style={{
            background: 'rgba(255,255,255,0.95)',
            backdropFilter: 'blur(12px)',
            border: '1px solid rgba(0,0,0,0.08)',
            borderRadius: 12,
            padding: '12px 16px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.10)',
            minWidth: 160,
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <div style={{ width: 10, height: 10, borderRadius: '50%', background: color, flexShrink: 0 }} />
                <span style={{ fontFamily: 'var(--font-sans)', fontSize: 12, fontWeight: 700, color: '#1A1A1A' }}>
                    {name}
                </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 16 }}>
                <span style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: '#888' }}>Interruptions</span>
                <span style={{ fontFamily: 'var(--font-serif)', fontSize: 18, color: '#1A1A1A', letterSpacing: '-0.02em' }}>{value}</span>
            </div>
            <div style={{ marginTop: 8, height: 4, borderRadius: 99, background: 'rgba(0,0,0,0.06)', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${pct}%`, borderRadius: 99, background: color, transition: 'width 0.3s ease' }} />
            </div>
            <span style={{ fontFamily: 'var(--font-sans)', fontSize: 10, color: '#A8A9AD', marginTop: 4, display: 'block', textAlign: 'right' }}>
                {pct}% of total
            </span>
        </div>
    );
}

export default function DistractionDonut() {
    const { data } = useStatsData();
    if (!data) return null;

    const { distractionSources, totalInterruptions } = data;

    return (
        <div className="flex flex-col h-full w-full">
            <div style={{ position: 'relative', width: '100%', height: 320 }}>
                {/* Center KPI Layer */}
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <span style={{
                        fontFamily: 'var(--font-serif), serif',
                        fontSize: 56,
                        fontWeight: 400,
                        letterSpacing: '-0.03em',
                        lineHeight: 1,
                        color: '#1A1A1A',
                    }}>
                        {totalInterruptions}
                    </span>
                    <span className="micro-label" style={{ marginTop: 8 }}>
                        TOTAL INTERRUPTIONS
                    </span>
                </div>

                {/* Chart Layer */}
                <ResponsiveContainer width="100%" height="100%">
                    <PieChart margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                        <Tooltip
                            content={<CustomTooltip totalInterruptions={totalInterruptions} />}
                            cursor={false}
                        />
                        <Pie
                            data={distractionSources}
                            cx="50%"
                            cy="50%"
                            innerRadius={90}
                            outerRadius={130}
                            paddingAngle={2}
                            dataKey="value"
                            stroke="none"
                            animationEasing={"cubic-bezier(0.25, 1, 0.5, 1)" as any}
                            animationDuration={800}
                        >
                            {distractionSources.map((entry, index) => (
                                <Cell
                                    key={`cell-${index}`}
                                    fill={entry.color}
                                    style={{ cursor: 'pointer', outline: 'none' }}
                                />
                            ))}
                        </Pie>
                    </PieChart>
                </ResponsiveContainer>
            </div>

            {/* Custom Legend */}
            <div className="flex flex-wrap justify-center mt-8" style={{ gap: 24 }}>
                {distractionSources.map((source, index) => {
                    const percentage = totalInterruptions > 0 ? Math.round((source.value / totalInterruptions) * 100) : 0;
                    return (
                        <div key={index} className="flex items-center gap-2">
                            <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: source.color }} />
                            <span style={{ fontFamily: 'var(--font-sans), sans-serif', fontSize: 13, color: '#666666' }}>
                                {source.name}
                            </span>
                            <span style={{ fontFamily: 'var(--font-sans), sans-serif', fontSize: 13, fontWeight: 600, color: '#1A1A1A' }}>
                                {source.value} <span style={{ color: '#A8A9AD', fontWeight: 400 }}>({percentage}%)</span>
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
