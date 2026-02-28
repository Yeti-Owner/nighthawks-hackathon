'use client';

import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Area,
    ComposedChart
} from 'recharts';
import { useStatsData } from '../../lib/DataContext';

interface CustomTooltipProps {
    active?: boolean;
    payload?: any[];
    label?: string;
}

const CustomTooltip = ({ active, payload, label }: CustomTooltipProps) => {
    if (active && payload && payload.length) {
        return (
            <div
                style={{
                    background: 'rgba(255, 255, 255, 0.90)',
                    backdropFilter: 'blur(12px)',
                    WebkitBackdropFilter: 'blur(12px)',
                    border: '1px solid rgba(44, 62, 80, 0.10)',
                    boxShadow: '0 8px 24px -8px rgba(44, 62, 80, 0.15)',
                    borderRadius: 8,
                    padding: '12px 16px',
                }}
            >
                <p className="micro-label" style={{ marginBottom: 4 }}>{label}</p>
                <p
                    style={{
                        fontFamily: 'var(--font-sans), sans-serif',
                        fontSize: 14,
                        fontWeight: 600,
                        color: '#1A1A1A',
                        margin: 0,
                    }}
                >
                    {`${payload[0].value} hours`}
                </p>
            </div>
        );
    }
    return null;
};

export default function DailyHoursChart() {
    const { data } = useStatsData();
    if (!data) return null;

    return (
        <div style={{ width: '100%', height: 320 }}>
            {/* We use ComposedChart to get both the filled Area and the crisp Line on top easily */}
            <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                    data={data.dailyHours}
                    margin={{ top: 16, right: 16, left: -16, bottom: 0 }}
                >
                    <CartesianGrid
                        strokeDasharray="0"
                        vertical={false}
                        stroke="rgba(0,0,0,0.04)"
                    />
                    <XAxis
                        dataKey="date"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fontFamily: 'var(--font-sans)', fontSize: 11, fill: '#A8A9AD' }}
                        dy={8}
                        minTickGap={24}
                    />
                    <YAxis
                        axisLine={false}
                        tickLine={false}
                        tick={{ fontFamily: 'var(--font-sans)', fontSize: 11, fill: '#A8A9AD' }}
                        dx={-8}
                    />
                    <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(44, 62, 80, 0.03)', strokeWidth: 0 }} />
                    <Area
                        type="monotone"
                        dataKey="hours"
                        stroke="none"
                        fill="rgba(44, 62, 80, 0.05)"
                        activeDot={false}
                    />
                    <Line
                        type="monotone"
                        dataKey="hours"
                        stroke="#2C3E50"
                        strokeWidth={2.5}
                        dot={false}
                        activeDot={{ r: 4, fill: '#2C3E50', stroke: '#F9F8F5', strokeWidth: 2 }}
                    />
                </ComposedChart>
            </ResponsiveContainer>
        </div>
    );
}
