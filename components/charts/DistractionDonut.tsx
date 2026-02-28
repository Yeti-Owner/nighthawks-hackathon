'use client';

import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';
import { distractionSources, totalInterruptions } from '../../lib/data';

export default function DistractionDonut() {
    return (
        <div className="flex flex-col h-full w-full">
            <div style={{ position: 'relative', width: '100%', height: 320 }}>
                {/* Center KPI Layer */}
                <div
                    className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none"
                >
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
                        {totalInterruptions}
                    </span>
                    <span className="micro-label" style={{ marginTop: 8 }}>
                        TOTAL INTERRUPTIONS
                    </span>
                </div>

                {/* Chart Layer */}
                <ResponsiveContainer width="100%" height="100%">
                    <PieChart margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
                        <Pie
                            data={distractionSources}
                            cx="50%"
                            cy="50%"
                            innerRadius={90}
                            outerRadius={130}
                            paddingAngle={2}
                            dataKey="value"
                            stroke="none"
                            // Adding easing to chart animation per spec
                            animationEasing={"cubic-bezier(0.25, 1, 0.5, 1)" as any}
                            animationDuration={800}
                        >
                            {distractionSources.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                        </Pie>
                    </PieChart>
                </ResponsiveContainer>
            </div>

            {/* Custom Legend */}
            <div className="flex flex-wrap justify-center mt-8" style={{ gap: 24 }}>
                {distractionSources.map((source, index) => {
                    const percentage = Math.round((source.value / totalInterruptions) * 100);
                    return (
                        <div key={index} className="flex items-center gap-2">
                            <div
                                style={{
                                    width: 8,
                                    height: 8,
                                    borderRadius: '50%',
                                    backgroundColor: source.color
                                }}
                            />
                            <span
                                style={{
                                    fontFamily: 'var(--font-sans), sans-serif',
                                    fontSize: 13,
                                    color: '#666666',
                                }}
                            >
                                {source.name}
                            </span>
                            <span
                                style={{
                                    fontFamily: 'var(--font-sans), sans-serif',
                                    fontSize: 13,
                                    fontWeight: 600,
                                    color: '#1A1A1A',
                                }}
                            >
                                {source.value} <span style={{ color: '#A8A9AD', fontWeight: 400 }}>({percentage}%)</span>
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
