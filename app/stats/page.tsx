'use client';

import { useState } from 'react';
import LiquidCard from '../../components/LiquidCard';
import KpiCard from '../../components/KpiCard';
import DailyHoursChart from '../../components/charts/DailyHoursChart';
import SubjectBarChart from '../../components/charts/SubjectBarChart';
import DistractionDonut from '../../components/charts/DistractionDonut';
import TopAppsList from '../../components/TopAppsList';
import SessionTable from '../../components/SessionTable';
import { totalStudyMinutes, totalSessions, avgFocusScore, totalInterruptions } from '../../lib/data';

const periods = ['Today', 'This Week', 'This Month', 'All Time'];
const filters = ['All Subjects', 'Physics', 'Mathematics', 'Literature', 'Chemistry', 'History'];

export default function StatsDashboard() {
    const [activePeriod, setActivePeriod] = useState('This Month');
    const [activeFilter, setActiveFilter] = useState('All Subjects');

    return (
        <div className="flex min-h-screen bg-[#F9F8F5] pt-[64px]">

            {/* Fixed Sidebar */}
            <aside
                className="fixed left-0 top-[64px] bottom-0 w-[240px] px-8 py-12 liquid-glass"
                style={{
                    borderLeft: 'none',
                    borderTop: 'none',
                    borderBottom: 'none',
                    borderRadius: 0,
                    borderRight: '1px solid rgba(0,0,0,0.06)',
                    zIndex: 40
                }}
            >
                <div className="mb-12">
                    <h4 className="micro-label mb-6">PERIOD</h4>
                    <div className="flex flex-col gap-4">
                        {periods.map(period => (
                            <button
                                key={period}
                                onClick={() => setActivePeriod(period)}
                                className="text-left bg-transparent border-none cursor-pointer"
                                style={{
                                    fontFamily: 'var(--font-sans), sans-serif',
                                    fontSize: 14,
                                    fontWeight: activePeriod === period ? 600 : 400,
                                    color: activePeriod === period ? '#1A1A1A' : '#666666',
                                    transition: 'color 200ms cubic-bezier(0.25, 1, 0.5, 1)',
                                }}
                            >
                                {period}
                            </button>
                        ))}
                    </div>
                </div>

                <div>
                    <h4 className="micro-label mb-6">SUBJECT filters</h4>
                    <div className="flex flex-col gap-4">
                        {filters.map(filter => (
                            <button
                                key={filter}
                                onClick={() => setActiveFilter(filter)}
                                className="text-left bg-transparent border-none cursor-pointer"
                                style={{
                                    fontFamily: 'var(--font-sans), sans-serif',
                                    fontSize: 14,
                                    fontWeight: activeFilter === filter ? 600 : 400,
                                    color: activeFilter === filter ? '#1A1A1A' : '#666666',
                                    transition: 'color 200ms cubic-bezier(0.25, 1, 0.5, 1)',
                                }}
                            >
                                {filter}
                            </button>
                        ))}
                    </div>
                </div>
            </aside>

            {/* Main Content Area */}
            <main className="flex-1 ml-[240px] p-[48px] md:p-[64px] max-w-[1440px]">
                {/* Top Header Row */}
                <div className="flex items-end justify-between mb-16 animate-fade-up">
                    <div>
                        <span className="micro-label text-[var(--color-accent-metal)] block mb-4">
                            {activePeriod.toUpperCase()} SUMMARY • {new Date().getFullYear()}
                        </span>
                        <h1
                            style={{
                                fontFamily: 'var(--font-serif), serif',
                                fontSize: 40,
                                color: '#1A1A1A',
                                letterSpacing: '-0.02em',
                                lineHeight: 1.1,
                                margin: 0
                            }}
                        >
                            Your Focus Report
                        </h1>
                    </div>
                    <button className="btn-ghost" style={{ height: 40, padding: '0 24px', fontSize: 11 }}>
                        Export PDF
                    </button>
                </div>

                {/* Row 1: KPI Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-8 mb-[64px]">
                    <KpiCard
                        value={`${Math.floor(totalStudyMinutes / 60)}h ${totalStudyMinutes % 60}m`}
                        label="TOTAL STUDY TIME"
                        trend="+12% vs last month"
                        trendType="positive"
                        delay={0}
                    />
                    <KpiCard
                        value={totalSessions.toString()}
                        label="SESSIONS COMPLETED"
                        trend="+8 this month"
                        trendType="neutral"
                        delay={80}
                    />
                    <KpiCard
                        value={avgFocusScore.toString()}
                        label="AVG. FOCUS SCORE"
                        trend="+3 pts"
                        trendType="positive"
                        delay={160}
                    />
                    <KpiCard
                        value={totalInterruptions.toString()}
                        label="TOTAL INTERRUPTIONS"
                        trend="-18% vs last month"
                        trendType="positive" // Decreased interruptions is positive
                        delay={240}
                    />
                </div>

                {/* Row 2: Charts (Line 60% / Bar 40%) */}
                <div className="flex flex-col lg:flex-row gap-8 mb-[64px] animate-fade-up" style={{ animationDelay: '320ms' }}>
                    <LiquidCard padding="p-8" className="flex-grow w-full lg:w-[60%]">
                        <h3 className="micro-label mb-8">Daily Study Duration</h3>
                        <DailyHoursChart />
                    </LiquidCard>

                    <LiquidCard padding="p-8" className="flex-grow w-full lg:w-[40%]">
                        <h3 className="micro-label mb-8">Study Time By Subject</h3>
                        <SubjectBarChart />
                    </LiquidCard>
                </div>

                {/* Row 3: Distraction Panel (Donut 50% / List 50%) */}
                <div className="flex flex-col lg:flex-row gap-8 mb-[64px] animate-fade-up" style={{ animationDelay: '400ms' }}>
                    <LiquidCard padding="p-8" className="flex-grow w-full lg:w-[50%]">
                        <h3 className="micro-label mb-8">Interruption Source Breakdown</h3>
                        <DistractionDonut />
                    </LiquidCard>

                    <div className="flex-grow w-full lg:w-[50%]">
                        <TopAppsList />
                    </div>
                </div>

                {/* Row 4: Session Log Table */}
                <div className="animate-fade-up" style={{ animationDelay: '480ms' }}>
                    <h3 className="micro-label mb-8">Recent Sessions</h3>
                    <LiquidCard padding="p-0 pt-8" className="overflow-hidden">
                        <SessionTable />
                    </LiquidCard>
                </div>

            </main>
        </div>
    );
}
