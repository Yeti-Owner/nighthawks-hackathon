'use client';

import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ReferenceLine,
    ResponsiveContainer,
} from 'recharts';
import type { FaceAwayEvent } from '../../lib/data';

const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || !payload.length) return null;

    return (
        <div className="bg-white p-3 border border-[#E5E5E5] rounded shadow-sm" style={{ backdropFilter: 'blur(10px)', background: 'rgba(255,255,255,0.95)' }}>
            <p className="micro-label text-[#8B7355] mb-2">{label}</p>
            <div className="flex flex-col gap-1">
                <p style={{ fontFamily: 'var(--font-sans), sans-serif', fontSize: 13, color: '#1A1A1A' }}>
                    <span style={{ color: '#B0B0B0', marginRight: 8 }}>Time off-screen:</span>
                    <strong>{payload[0].value}s</strong>
                </p>
            </div>
        </div>
    );
};

export default function FaceDetectionChart({ data }: { data: FaceAwayEvent[] }) {
    const chartData = data.map((e) => ({
        time: e.time,
        'Look-Away (s)': e.durationSeconds,
    }));

    const avg = data.length > 0
        ? Math.round(data.reduce((s, e) => s + e.durationSeconds, 0) / data.length)
        : 0;

    return (
        <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                    <linearGradient id="colorLookAway" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#C0392B" stopOpacity={0.15} />
                        <stop offset="95%" stopColor="#C0392B" stopOpacity={0} />
                    </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.05)" />
                <XAxis
                    dataKey="time"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#A8A9AD', fontSize: 10, fontFamily: 'var(--font-sans)' }}
                    dy={10}
                />
                <YAxis
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#A8A9AD', fontSize: 10, fontFamily: 'var(--font-sans)' }}
                />
                <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(192, 57, 43, 0.2)', strokeWidth: 1, strokeDasharray: '4 4' }} />
                <ReferenceLine
                    y={avg}
                    stroke="#D7C3B3"
                    strokeDasharray="3 3"
                    label={{ position: 'insideTopLeft', value: `AVG: ${avg}s`, fill: '#D7C3B3', fontSize: 10, fontFamily: 'var(--font-sans)', dy: -10 }}
                />
                <Area
                    type="monotone"
                    dataKey="Look-Away (s)"
                    stroke="#C0392B"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorLookAway)"
                    activeDot={{ r: 4, fill: '#C0392B', stroke: '#fff', strokeWidth: 2 }}
                    animationDuration={1200}
                />
            </AreaChart>
        </ResponsiveContainer>
    );
}
