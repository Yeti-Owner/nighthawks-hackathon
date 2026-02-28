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
import { faceAwayEvents } from '../../lib/data';

const data = faceAwayEvents.map((e) => ({
    time: e.time,
    'Look-Away (s)': e.durationSeconds,
}));

// avg line value
const avg = Math.round(
    faceAwayEvents.reduce((s, e) => s + e.durationSeconds, 0) / faceAwayEvents.length
);

const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || !payload.length) return null;
    const dur = payload[0]?.value;
    const severity = dur > 60 ? 'High' : dur > 20 ? 'Medium' : 'Low';
    const severityColor = dur > 60 ? '#C0392B' : dur > 20 ? '#B07A4A' : '#4A6741';
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
                👁 {label}
            </p>
            <p style={{ fontSize: 12, color: '#2C3E50', margin: '2px 0' }}>
                Looked away for: <strong>{dur}s</strong>
            </p>
            <p style={{ fontSize: 11, color: severityColor, marginTop: 4, fontWeight: 600 }}>
                {severity} distraction
            </p>
        </div>
    );
};

export default function FaceDetectionChart() {
    return (
        <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
                <defs>
                    <linearGradient id="faceGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#2C3E50" stopOpacity={0.18} />
                        <stop offset="95%" stopColor="#2C3E50" stopOpacity={0.01} />
                    </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.05)" />
                <XAxis
                    dataKey="time"
                    tick={{ fontSize: 11, fontFamily: 'var(--font-sans)', fill: '#999' }}
                    axisLine={false}
                    tickLine={false}
                    interval={3}
                />
                <YAxis
                    tick={{ fontSize: 11, fontFamily: 'var(--font-sans)', fill: '#999' }}
                    axisLine={false}
                    tickLine={false}
                    label={{ value: 'Seconds away', angle: -90, position: 'insideLeft', fontSize: 10, fill: '#bbb', dy: 50 }}
                />
                <Tooltip content={<CustomTooltip />} />
                <ReferenceLine
                    y={avg}
                    stroke="#B07A4A"
                    strokeDasharray="5 4"
                    strokeWidth={1.5}
                    label={{ value: `avg ${avg}s`, position: 'right', fontSize: 10, fill: '#B07A4A' }}
                />
                <Area
                    type="monotone"
                    dataKey="Look-Away (s)"
                    stroke="#2C3E50"
                    strokeWidth={2}
                    fill="url(#faceGrad)"
                    dot={{ r: 3, fill: '#2C3E50', strokeWidth: 0 }}
                    activeDot={{ r: 5, fill: '#2C3E50' }}
                />
            </AreaChart>
        </ResponsiveContainer>
    );
}
