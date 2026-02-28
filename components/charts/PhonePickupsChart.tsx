'use client';

import {
    ComposedChart,
    Bar,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
} from 'recharts';
import type { PhonePickupEvent } from '../../lib/data';

const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || !payload.length) return null;
    const duration = payload.find((p: any) => p.dataKey === 'Pickup Duration (s)')?.value;
    const gap = payload.find((p: any) => p.dataKey === 'Gap Since Last (min)')?.value;
    return (
        <div
            style={{
                background: 'rgba(255,255,255,0.96)',
                border: '1px solid rgba(0,0,0,0.08)',
                borderRadius: 12,
                padding: '12px 16px',
                boxShadow: '0 8px 32px rgba(0,0,0,0.10)',
                fontFamily: 'var(--font-sans), sans-serif',
            }}
        >
            <p style={{ fontWeight: 600, fontSize: 13, color: '#1A1A1A', marginBottom: 6 }}>
                📱 {label}
            </p>
            {duration !== undefined && (
                <p style={{ fontSize: 12, color: '#B07A4A', margin: '2px 0' }}>
                    Pickup lasted: <strong>{duration}s</strong>
                </p>
            )}
            {gap !== undefined && gap > 0 && (
                <p style={{ fontSize: 12, color: '#4A6741', margin: '2px 0' }}>
                    Phone left alone: <strong>{gap} min</strong> before this
                </p>
            )}
        </div>
    );
};

export default function PhonePickupsChart({ data }: { data: PhonePickupEvent[] }) {
    const chartData = data.map((e) => ({
        time: e.time,
        'Pickup Duration (s)': e.durationSeconds,
        'Gap Since Last (min)': e.minutesUnattended,
    }));

    return (
        <ResponsiveContainer width="100%" height={260}>
            <ComposedChart data={chartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.05)" />
                <XAxis
                    dataKey="time"
                    tick={{ fontSize: 11, fontFamily: 'var(--font-sans)', fill: '#999' }}
                    axisLine={false}
                    tickLine={false}
                    interval={2}
                />
                <YAxis
                    yAxisId="left"
                    tick={{ fontSize: 11, fontFamily: 'var(--font-sans)', fill: '#999' }}
                    axisLine={false}
                    tickLine={false}
                    label={{ value: 'Pickup (s)', angle: -90, position: 'insideLeft', fontSize: 10, fill: '#bbb', dy: 40 }}
                />
                <YAxis
                    yAxisId="right"
                    orientation="right"
                    tick={{ fontSize: 11, fontFamily: 'var(--font-sans)', fill: '#999' }}
                    axisLine={false}
                    tickLine={false}
                    label={{ value: 'Gap (min)', angle: 90, position: 'insideRight', fontSize: 10, fill: '#bbb', dy: -30 }}
                />
                <Tooltip content={<CustomTooltip />} />
                <Legend
                    wrapperStyle={{ fontSize: 11, fontFamily: 'var(--font-sans)', color: '#888', paddingTop: 12 }}
                />
                <Bar
                    yAxisId="left"
                    dataKey="Pickup Duration (s)"
                    fill="#B07A4A"
                    radius={[4, 4, 0, 0]}
                    opacity={0.85}
                    maxBarSize={28}
                />
                <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="Gap Since Last (min)"
                    stroke="#4A6741"
                    strokeWidth={2}
                    dot={{ r: 3, fill: '#4A6741', strokeWidth: 0 }}
                    activeDot={{ r: 5 }}
                />
            </ComposedChart>
        </ResponsiveContainer>
    );
}
