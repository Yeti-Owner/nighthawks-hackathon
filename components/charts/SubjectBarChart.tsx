'use client';

import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell
} from 'recharts';
import { useStatsData } from '../../lib/DataContext';

interface CustomTooltipProps {
    active?: boolean;
    payload?: any[];
}

const CustomTooltip = ({ active, payload }: CustomTooltipProps) => {
    if (active && payload && payload.length) {
        return (
            <div
                style={{
                    background: 'rgba(255, 255, 255, 0.90)',
                    backdropFilter: 'blur(12px)',
                    border: '1px solid rgba(44, 62, 80, 0.10)',
                    boxShadow: '0 8px 24px -8px rgba(44, 62, 80, 0.15)',
                    borderRadius: 8,
                    padding: '12px 16px',
                }}
            >
                <p className="micro-label" style={{ marginBottom: 4 }}>{payload[0].payload.subject}</p>
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

const QUIET_LUXURY_COLORS = [
    '#2C3E50', // Midnight Blue
    '#D7C3B3', // Rose Gold
    '#A8A9AD', // Brushed Platinum
    '#4A6741', // Muted Green / Olive
    '#8B7355', // Warm Wood
];

export default function SubjectBarChart() {
    const { data } = useStatsData();
    if (!data) return null;

    return (
        <div style={{ width: '100%', height: 320 }}>
            {/* 
        Horizontal BarChart:
        layout="vertical"
        XAxis type="number"
        YAxis type="category"
      */}
            <ResponsiveContainer width="100%" height="100%">
                <BarChart
                    data={data.subjectHours}
                    layout="vertical"
                    margin={{ top: 0, right: 16, left: 0, bottom: 0 }}
                >
                    <CartesianGrid
                        strokeDasharray="0"
                        horizontal={false}
                        stroke="rgba(0,0,0,0.04)"
                    />
                    <XAxis
                        type="number"
                        domain={[0, 'auto']} // Zero baseline strictly enforced
                        axisLine={false}
                        tickLine={false}
                        tick={{ fontFamily: 'var(--font-sans)', fontSize: 11, fill: '#A8A9AD' }}
                        dy={8}
                    />
                    <YAxis
                        type="category"
                        dataKey="subject"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fontFamily: 'var(--font-sans)', fontSize: 12, fill: '#666666' }}
                        width={90}
                        dx={-8}
                    />
                    <Tooltip
                        cursor={{ fill: 'rgba(44, 62, 80, 0.03)' }}
                        content={<CustomTooltip />}
                    />
                    <Bar
                        dataKey="hours"
                        radius={[0, 4, 4, 0]} // Right-side radius only 
                        barSize={24}
                    >
                        {data.subjectHours.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={QUIET_LUXURY_COLORS[index % QUIET_LUXURY_COLORS.length]} />
                        ))}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}
