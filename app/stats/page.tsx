'use client';

import { useRef, useState } from 'react';
import LiquidCard from '../../components/LiquidCard';
import KpiCard from '../../components/KpiCard';
import DailyHoursChart from '../../components/charts/DailyHoursChart';
import SubjectBarChart from '../../components/charts/SubjectBarChart';
import DistractionDonut from '../../components/charts/DistractionDonut';
import TopAppsList from '../../components/TopAppsList';
import SessionTable from '../../components/SessionTable';
import PhonePickupsChart from '../../components/charts/PhonePickupsChart';
import FaceDetectionChart from '../../components/charts/FaceDetectionChart';
import {
    totalStudyMinutes,
    totalSessions,
    avgFocusScore,
    totalInterruptions,
    totalPhonePickups,
    avgUnattendedMinutes,
    longestUnattended,
    totalLookAways,
    avgLookAwaySeconds,
    longestLookAway,
    totalSecondsDistracted,
} from '../../lib/data';

const periods = ['Today', 'All Time'];
const filters = ['All Filters', 'Phone Pickups', 'Face Detection'];

export default function StatsDashboard() {
    const [activePeriod, setActivePeriod] = useState('Today');
    const [activeFilter, setActiveFilter] = useState('All Filters');

    const phonePickupsRef = useRef<HTMLDivElement>(null);
    const faceDetectionRef = useRef<HTMLDivElement>(null);

    function handleFilterClick(filter: string) {
        setActiveFilter(filter);
        if (filter === 'Phone Pickups') {
            setTimeout(() => {
                phonePickupsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 50);
        } else if (filter === 'Face Detection') {
            setTimeout(() => {
                faceDetectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 50);
        }
    }

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
                    <h4 className="micro-label mb-6">FILTERS</h4>
                    <div className="flex flex-col gap-4">
                        {filters.map(filter => (
                            <button
                                key={filter}
                                onClick={() => handleFilterClick(filter)}
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
                        trendType="positive"
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

                {/* ─── Phone Pickups Section ─── */}
                <div
                    ref={phonePickupsRef}
                    className="mb-[64px] animate-fade-up"
                    style={{ animationDelay: '460ms', scrollMarginTop: '96px' }}
                >
                    {/* Section header */}
                    <div className="flex items-center gap-4 mb-8">
                        <div
                            style={{
                                width: 3,
                                height: 28,
                                background: 'linear-gradient(180deg, #B07A4A, #8B5E3C)',
                                borderRadius: 99,
                            }}
                        />
                        <div>
                            <span className="micro-label" style={{ color: '#B07A4A' }}>DISTRACTION ANALYSIS</span>
                            <h2
                                style={{
                                    fontFamily: 'var(--font-serif), serif',
                                    fontSize: 26,
                                    color: '#1A1A1A',
                                    letterSpacing: '-0.015em',
                                    margin: '2px 0 0',
                                }}
                            >
                                Phone Pickups
                            </h2>
                        </div>
                    </div>

                    {/* KPI mini-cards */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                        {/* Total pickups */}
                        <LiquidCard padding="p-6">
                            <p className="micro-label mb-2" style={{ color: '#B07A4A' }}>TOTAL PICKUPS</p>
                            <p style={{ fontFamily: 'var(--font-serif)', fontSize: 36, color: '#1A1A1A', margin: 0 }}>
                                {totalPhonePickups}
                            </p>
                            <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>times today</p>
                        </LiquidCard>

                        {/* Avg unattended */}
                        <LiquidCard padding="p-6">
                            <p className="micro-label mb-2" style={{ color: '#4A6741' }}>AVG. FOCUS WINDOW</p>
                            <p style={{ fontFamily: 'var(--font-serif)', fontSize: 36, color: '#1A1A1A', margin: 0 }}>
                                {avgUnattendedMinutes}<span style={{ fontSize: 18, color: '#888' }}> min</span>
                            </p>
                            <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>avg. between pickups</p>
                        </LiquidCard>

                        {/* Longest without phone */}
                        <LiquidCard padding="p-6">
                            <p className="micro-label mb-2" style={{ color: '#2C3E50' }}>BEST STREAK</p>
                            <p style={{ fontFamily: 'var(--font-serif)', fontSize: 36, color: '#1A1A1A', margin: 0 }}>
                                {longestUnattended}<span style={{ fontSize: 18, color: '#888' }}> min</span>
                            </p>
                            <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>longest phone-free window</p>
                        </LiquidCard>
                    </div>

                    {/* Chart */}
                    <LiquidCard padding="p-8">
                        <div className="flex items-start justify-between mb-6">
                            <div>
                                <h3 className="micro-label mb-1">Pickup Timeline</h3>
                                <p style={{ fontSize: 12, color: '#999', margin: 0 }}>
                                    Bars = how long you used<br />the phone · Line = focus window before each pickup
                                </p>
                            </div>
                            <div style={{
                                background: 'rgba(176,122,74,0.08)',
                                border: '1px solid rgba(176,122,74,0.2)',
                                borderRadius: 8,
                                padding: '6px 14px',
                                fontSize: 11,
                                color: '#B07A4A',
                                fontFamily: 'var(--font-sans)',
                                fontWeight: 600,
                                letterSpacing: '0.05em'
                            }}>
                                TODAY
                            </div>
                        </div>
                        <PhonePickupsChart />

                        {/* Event timeline list */}
                        <div style={{ marginTop: 28, borderTop: '1px solid rgba(0,0,0,0.05)', paddingTop: 20 }}>
                            <p className="micro-label mb-4">ALL PICKUP EVENTS</p>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                {[...require('../../lib/data').phonePickupEvents].map((e: any, i: number) => (
                                    <div
                                        key={i}
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: 16,
                                            padding: '8px 12px',
                                            borderRadius: 8,
                                            background: i % 2 === 0 ? 'rgba(0,0,0,0.02)' : 'transparent',
                                        }}
                                    >
                                        <span style={{ fontSize: 12, fontWeight: 600, color: '#1A1A1A', width: 44, flexShrink: 0 }}>{e.time}</span>
                                        <span style={{ fontSize: 12, color: '#B07A4A', flexShrink: 0 }}>
                                            📱 picked up for {e.durationSeconds}s
                                        </span>
                                        {e.minutesUnattended > 0 && (
                                            <span style={{ fontSize: 11, color: '#888' }}>
                                                · {e.minutesUnattended} min phone-free before this
                                            </span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    </LiquidCard>
                </div>

                {/* ─── Face Detection Section ─── */}
                <div
                    ref={faceDetectionRef}
                    className="mb-[64px] animate-fade-up"
                    style={{ animationDelay: '500ms', scrollMarginTop: '96px' }}
                >
                    <div className="flex items-center gap-4 mb-8">
                        <div style={{ width: 3, height: 28, background: 'linear-gradient(180deg, #2C3E50, #1a252f)', borderRadius: 99 }} />
                        <div>
                            <span className="micro-label" style={{ color: '#2C3E50' }}>DISTRACTION ANALYSIS</span>
                            <h2 style={{ fontFamily: 'var(--font-serif), serif', fontSize: 26, color: '#1A1A1A', letterSpacing: '-0.015em', margin: '2px 0 0' }}>
                                Face Detection
                            </h2>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8">
                        <LiquidCard padding="p-6">
                            <p className="micro-label mb-2" style={{ color: '#2C3E50' }}>TOTAL LOOK-AWAYS</p>
                            <p style={{ fontFamily: 'var(--font-serif)', fontSize: 36, color: '#1A1A1A', margin: 0 }}>{totalLookAways}</p>
                            <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>times today</p>
                        </LiquidCard>
                        <LiquidCard padding="p-6">
                            <p className="micro-label mb-2" style={{ color: '#B07A4A' }}>AVG. DURATION</p>
                            <p style={{ fontFamily: 'var(--font-serif)', fontSize: 36, color: '#1A1A1A', margin: 0 }}>{avgLookAwaySeconds}<span style={{ fontSize: 18, color: '#888' }}>s</span></p>
                            <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>per look-away</p>
                        </LiquidCard>
                        <LiquidCard padding="p-6">
                            <p className="micro-label mb-2" style={{ color: '#C0392B' }}>LONGEST AWAY</p>
                            <p style={{ fontFamily: 'var(--font-serif)', fontSize: 36, color: '#1A1A1A', margin: 0 }}>{longestLookAway}<span style={{ fontSize: 18, color: '#888' }}>s</span></p>
                            <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>single distraction</p>
                        </LiquidCard>
                        <LiquidCard padding="p-6">
                            <p className="micro-label mb-2" style={{ color: '#4A6741' }}>TOTAL DISTRACTED</p>
                            <p style={{ fontFamily: 'var(--font-serif)', fontSize: 36, color: '#1A1A1A', margin: 0 }}>{Math.floor(totalSecondsDistracted / 60)}<span style={{ fontSize: 18, color: '#888' }}>m {totalSecondsDistracted % 60}s</span></p>
                            <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>total time off-screen</p>
                        </LiquidCard>
                    </div>

                    <LiquidCard padding="p-8">
                        <div className="flex items-start justify-between mb-6">
                            <div>
                                <h3 className="micro-label mb-1">Look-Away Timeline</h3>
                                <p style={{ fontSize: 12, color: '#999', margin: 0 }}>Each spike = one distraction · Dashed line = your daily average</p>
                            </div>
                            <div style={{ background: 'rgba(44,62,80,0.08)', border: '1px solid rgba(44,62,80,0.2)', borderRadius: 8, padding: '6px 14px', fontSize: 11, color: '#2C3E50', fontFamily: 'var(--font-sans)', fontWeight: 600, letterSpacing: '0.05em' }}>
                                TODAY
                            </div>
                        </div>
                        <FaceDetectionChart />

                        <div style={{ display: 'flex', gap: 20, marginTop: 16, paddingTop: 16, borderTop: '1px solid rgba(0,0,0,0.05)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#4A6741' }} />
                                <span style={{ fontSize: 11, color: '#888' }}>Low (&lt;20s)</span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#B07A4A' }} />
                                <span style={{ fontSize: 11, color: '#888' }}>Medium (20–60s)</span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#C0392B' }} />
                                <span style={{ fontSize: 11, color: '#888' }}>High (&gt;60s)</span>
                            </div>
                        </div>

                        <div style={{ marginTop: 20, borderTop: '1px solid rgba(0,0,0,0.05)', paddingTop: 20 }}>
                            <p className="micro-label mb-4">ALL LOOK-AWAY EVENTS</p>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                {[...require('../../lib/data').faceAwayEvents].map((e: any, i: number) => {
                                    const severity = e.durationSeconds > 60 ? 'High' : e.durationSeconds > 20 ? 'Medium' : 'Low';
                                    const sColor = e.durationSeconds > 60 ? '#C0392B' : e.durationSeconds > 20 ? '#B07A4A' : '#4A6741';
                                    return (
                                        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '8px 12px', borderRadius: 8, background: i % 2 === 0 ? 'rgba(0,0,0,0.02)' : 'transparent' }}>
                                            <span style={{ fontSize: 12, fontWeight: 600, color: '#1A1A1A', width: 44, flexShrink: 0 }}>{e.time}</span>
                                            <span style={{ fontSize: 12, color: '#2C3E50', flexShrink: 0 }}>👁 looked away for {e.durationSeconds}s</span>
                                            <span style={{ fontSize: 11, color: sColor, fontWeight: 600 }}>{severity}</span>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </LiquidCard>
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
