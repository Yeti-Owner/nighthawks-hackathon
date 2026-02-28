'use client';

import { useRef, useState } from 'react';
import { withAuthenticationRequired } from '@auth0/auth0-react';
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

function StatsDashboard() {
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
        <div className="flex min-h-screen pt-[64px]" style={{ background: '#F9F8F5', position: 'relative' }}>

            {/* ── Global dot-grid background ── */}
            <div aria-hidden style={{
                position: 'fixed',
                inset: 0,
                backgroundImage: 'radial-gradient(circle, rgba(44,62,80,0.055) 1px, transparent 1px)',
                backgroundSize: '28px 28px',
                maskImage: 'radial-gradient(ellipse 85% 85% at 60% 40%, black 20%, transparent 100%)',
                WebkitMaskImage: 'radial-gradient(ellipse 85% 85% at 60% 40%, black 20%, transparent 100%)',
                pointerEvents: 'none',
                zIndex: 0,
            }} />

            {/* ── Warm glow top-right ── */}
            <div aria-hidden className="animate-pulse-glow" style={{
                position: 'fixed',
                width: 480,
                height: 480,
                right: -80,
                top: -80,
                background: 'radial-gradient(circle, rgba(215,195,179,0.35) 0%, transparent 70%)',
                borderRadius: '50%',
                pointerEvents: 'none',
                zIndex: 0,
            }} />

            {/* Fixed Sidebar */}
            <aside
                className="fixed left-0 top-[64px] bottom-0 w-[240px] px-8 py-12 liquid-glass"
                style={{
                    borderLeft: 'none',
                    borderTop: 'none',
                    borderBottom: 'none',
                    borderRadius: 0,
                    borderRight: '1px solid rgba(0,0,0,0.06)',
                    zIndex: 40,
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                }}
            >
                <div>
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
                </div>

                {/* ── Sidebar Middle Fill ── */}
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 20, padding: '24px 0' }}>

                    {/* Today at a Glance mini panel */}
                    <div style={{
                        background: 'rgba(255,255,255,0.55)',
                        border: '1px solid rgba(0,0,0,0.07)',
                        borderRadius: 14,
                        padding: '16px 14px',
                        backdropFilter: 'blur(12px)',
                    }}>
                        <p style={{ fontFamily: 'var(--font-sans)', fontSize: 9, fontWeight: 700, letterSpacing: '0.12em', color: '#C8B89A', marginBottom: 14 }}>TODAY AT A GLANCE</p>
                        {[
                            { label: 'Study time', value: '2h 47m', color: '#2C3E50' },
                            { label: 'Phone pickups', value: `${totalPhonePickups}×`, color: '#B07A4A' },
                            { label: 'Look-aways', value: `${totalLookAways}×`, color: '#C0392B' },
                            { label: 'Focus score', value: `${avgFocusScore}`, color: '#4A6741' },
                        ].map(({ label, value, color }) => (
                            <div key={label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                                <span style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: '#888' }}>{label}</span>
                                <span style={{ fontFamily: 'var(--font-serif)', fontSize: 15, color, letterSpacing: '-0.02em' }}>{value}</span>
                            </div>
                        ))}
                        {/* Focus quality gradient bar */}
                        <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid rgba(0,0,0,0.05)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                                <span style={{ fontFamily: 'var(--font-sans)', fontSize: 9, color: '#B0B0B0', fontWeight: 600, letterSpacing: '0.08em' }}>FOCUS QUALITY</span>
                                <span style={{ fontFamily: 'var(--font-sans)', fontSize: 9, color: '#888' }}>{avgFocusScore}%</span>
                            </div>
                            <div style={{ height: 5, borderRadius: 99, background: 'rgba(0,0,0,0.06)', overflow: 'hidden' }}>
                                <div style={{
                                    height: '100%',
                                    width: `${avgFocusScore}%`,
                                    borderRadius: 99,
                                    background: 'linear-gradient(90deg, #B07A4A, #4A6741)',
                                    transition: 'width 1s ease',
                                }} />
                            </div>
                        </div>
                    </div>

                    {/* Animated breathing focus orb */}
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, padding: '12px 0' }}>
                        <div style={{ position: 'relative', width: 88, height: 88 }}>
                            {/* Outer pulse rings */}
                            <div style={{
                                position: 'absolute', inset: -8,
                                borderRadius: '50%',
                                border: '1px solid rgba(215,195,179,0.3)',
                                animation: 'pulseRing 3s ease-in-out infinite',
                            }} />
                            <div style={{
                                position: 'absolute', inset: -16,
                                borderRadius: '50%',
                                border: '1px solid rgba(215,195,179,0.12)',
                                animation: 'pulseRing 3s ease-in-out infinite 0.5s',
                            }} />
                            {/* SVG ring */}
                            <svg width={88} height={88} style={{ position: 'absolute', inset: 0, transform: 'rotate(-90deg)' }}>
                                <circle cx={44} cy={44} r={36} fill="none" stroke="rgba(0,0,0,0.06)" strokeWidth="5" />
                                <circle cx={44} cy={44} r={36} fill="none" stroke="url(#sidebarGrad)" strokeWidth="5"
                                    strokeLinecap="round"
                                    strokeDasharray={2 * Math.PI * 36}
                                    strokeDashoffset={2 * Math.PI * 36 * (1 - avgFocusScore / 100)}
                                    style={{ transition: 'stroke-dashoffset 1.5s ease' }}
                                />
                                <defs>
                                    <linearGradient id="sidebarGrad" x1="0" y1="0" x2="1" y2="0">
                                        <stop offset="0%" stopColor="#D7C3B3" />
                                        <stop offset="100%" stopColor="#2C3E50" />
                                    </linearGradient>
                                </defs>
                            </svg>
                            {/* Centre score */}
                            <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                                <span style={{ fontFamily: 'var(--font-serif)', fontSize: 20, color: '#1A1A1A', letterSpacing: '-0.03em', lineHeight: 1 }}>{avgFocusScore}</span>
                                <span style={{ fontFamily: 'var(--font-sans)', fontSize: 8, color: '#B0B0B0', fontWeight: 600, letterSpacing: '0.08em', marginTop: 2 }}>SCORE</span>
                            </div>
                        </div>
                        <p style={{ fontFamily: 'var(--font-sans)', fontSize: 10, color: '#A8A9AD', textAlign: 'center', lineHeight: 1.5, margin: 0 }}>
                            Live focus<br />quality index
                        </p>
                    </div>

                    {/* Focus tip / quote */}
                    <div style={{
                        borderLeft: '2px solid #D7C3B3',
                        paddingLeft: 12,
                        margin: '0 0 4px',
                    }}>
                        <p style={{ fontFamily: 'var(--font-serif)', fontSize: 13, color: '#555', lineHeight: 1.6, fontStyle: 'italic', margin: 0 }}>
                            "The secret of getting ahead is getting started."
                        </p>
                        <p style={{ fontFamily: 'var(--font-sans)', fontSize: 10, color: '#C8B89A', fontWeight: 600, letterSpacing: '0.06em', marginTop: 8 }}>
                            — MARK TWAIN
                        </p>
                    </div>

                    {/* ── 24h Focus Heatmap ── */}
                    <div style={{ background: 'rgba(255,255,255,0.45)', border: '1px solid rgba(0,0,0,0.06)', borderRadius: 14, padding: '14px 12px' }}>
                        <p style={{ fontFamily: 'var(--font-sans)', fontSize: 9, fontWeight: 700, letterSpacing: '0.12em', color: '#C8B89A', marginBottom: 10 }}>24H FOCUS MAP</p>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: 3, marginBottom: 4 }}>
                            {[0, 0, 0, 0, 0, 0, 30, 60, 85, 90, 75, 80, 92, 88, 40, 15, 70, 85, 90, 80, 60, 30, 10, 0].map((intensity, i) => (
                                <div key={i} title={`${i}:00`} style={{
                                    height: 14, borderRadius: 3,
                                    background: intensity === 0
                                        ? 'rgba(0,0,0,0.05)'
                                        : intensity < 40 ? 'rgba(215,195,179,0.45)'
                                            : intensity < 70 ? 'rgba(176,122,74,0.55)'
                                                : 'rgba(44,62,80,0.72)',
                                }} />
                            ))}
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <span style={{ fontFamily: 'var(--font-sans)', fontSize: 8, color: '#C0C0C0' }}>12AM</span>
                            <span style={{ fontFamily: 'var(--font-sans)', fontSize: 8, color: '#C0C0C0' }}>12PM</span>
                            <span style={{ fontFamily: 'var(--font-sans)', fontSize: 8, color: '#C0C0C0' }}>11PM</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 6 }}>
                            {['rgba(0,0,0,0.05)', 'rgba(215,195,179,0.45)', 'rgba(176,122,74,0.55)', 'rgba(44,62,80,0.72)'].map((bg, i) => (
                                <div key={i} style={{ width: 9, height: 9, borderRadius: 2, background: bg }} />
                            ))}
                            <span style={{ fontFamily: 'var(--font-sans)', fontSize: 8, color: '#C0C0C0', marginLeft: 3 }}>Low → High</span>
                        </div>
                    </div>

                    {/* ── 7-Day Streak ── */}
                    <div style={{ background: 'rgba(255,255,255,0.45)', border: '1px solid rgba(0,0,0,0.06)', borderRadius: 14, padding: '14px 12px', overflow: 'hidden' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                            <p style={{ fontFamily: 'var(--font-sans)', fontSize: 9, fontWeight: 700, letterSpacing: '0.12em', color: '#C8B89A', margin: 0 }}>STREAK</p>
                            <div style={{ display: 'flex', alignItems: 'baseline', gap: 3 }}>
                                <span style={{ fontFamily: 'var(--font-serif)', fontSize: 22, color: '#1A1A1A', letterSpacing: '-0.02em', lineHeight: 1 }}>5</span>
                                <span style={{ fontFamily: 'var(--font-sans)', fontSize: 9, color: '#B0B0B0' }}>days</span>
                            </div>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            {['M', 'T', 'W', 'T', 'F', 'S', 'S'].map((day, i) => {
                                const done = i < 5;
                                const isToday = i === 4;
                                return (
                                    <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                                        <div style={{
                                            width: 18, height: 18, borderRadius: '50%',
                                            background: isToday ? 'linear-gradient(135deg, #D7C3B3, #2C3E50)' : done ? 'rgba(44,62,80,0.12)' : 'rgba(0,0,0,0.04)',
                                            border: isToday ? 'none' : done ? '1.5px solid rgba(44,62,80,0.2)' : '1.5px solid rgba(0,0,0,0.08)',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            boxShadow: isToday ? '0 2px 8px rgba(44,62,80,0.25)' : 'none',
                                            flexShrink: 0,
                                        }}>
                                            {done && <div style={{ width: 5, height: 5, borderRadius: '50%', background: isToday ? '#fff' : 'rgba(44,62,80,0.45)' }} />}
                                        </div>
                                        <span style={{ fontFamily: 'var(--font-sans)', fontSize: 8, fontWeight: 600, color: done ? '#888' : '#CCC' }}>{day}</span>
                                    </div>
                                );
                            })}
                        </div>
                        <p style={{ fontFamily: 'var(--font-sans)', fontSize: 10, color: '#C8B89A', marginTop: 10, marginBottom: 0, fontWeight: 600 }}>🔥 Best streak yet — keep going!</p>
                    </div>

                    {/* ── Peak Hours ── */}
                    <div style={{ background: 'rgba(255,255,255,0.45)', border: '1px solid rgba(0,0,0,0.06)', borderRadius: 14, padding: '14px 12px' }}>
                        <p style={{ fontFamily: 'var(--font-sans)', fontSize: 9, fontWeight: 700, letterSpacing: '0.12em', color: '#C8B89A', marginBottom: 12 }}>PEAK HOURS</p>
                        {[
                            { time: '9–11 AM', score: 95, label: 'Deep work zone' },
                            { time: '1–3 PM', score: 88, label: 'Post-lunch surge' },
                            { time: '7–9 PM', score: 76, label: 'Evening review' },
                        ].map(({ time, score, label }) => (
                            <div key={time} style={{ marginBottom: 10 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                                    <span style={{ fontFamily: 'var(--font-sans)', fontSize: 10, fontWeight: 600, color: '#444' }}>{time}</span>
                                    <span style={{ fontFamily: 'var(--font-serif)', fontSize: 12, color: '#2C3E50' }}>{score}</span>
                                </div>
                                <div style={{ height: 4, borderRadius: 99, background: 'rgba(0,0,0,0.06)', overflow: 'hidden' }}>
                                    <div style={{ height: '100%', width: `${score}%`, borderRadius: 99, background: 'linear-gradient(90deg, #D7C3B3, #2C3E50)' }} />
                                </div>
                                <span style={{ fontFamily: 'var(--font-sans)', fontSize: 9, color: '#B0B0B0' }}>{label}</span>
                            </div>
                        ))}
                    </div>

                </div>


                <div style={{ paddingBottom: 8 }}>
                    <div style={{ height: 1, background: 'rgba(0,0,0,0.06)', marginBottom: 20 }} />
                    <p style={{ fontFamily: 'var(--font-sans)', fontSize: 10, fontWeight: 600, letterSpacing: '0.12em', color: '#C8B89A', marginBottom: 8 }}>AURELIUS</p>
                    <p style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: '#B0B0B0', lineHeight: 1.5 }}>Focus Intelligence<br />Platform</p>
                    {/* Decorative mini sparkline */}
                    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 3, marginTop: 14, height: 24 }}>
                        {[40, 65, 50, 80, 70, 90, 75, 95, 85, 100].map((h, i) => (
                            <div key={i} style={{ flex: 1, height: `${h}%`, background: i === 9 ? '#D7C3B3' : 'rgba(215,195,179,0.35)', borderRadius: '2px 2px 0 0' }} />
                        ))}
                    </div>
                </div>
            </aside>

            {/* Main Content Area */}
            <main className="flex-1 ml-[216px] pl-0 pr-[48px] py-[48px] md:py-[64px] max-w-[1440px]" style={{ position: 'relative', zIndex: 1 }}>

                {/* ── Hero Banner ── */}
                <div style={{
                    position: 'relative',
                    borderRadius: 20,
                    overflow: 'hidden',
                    background: 'linear-gradient(135deg, rgba(255,255,255,0.72) 0%, rgba(249,248,245,0.85) 100%)',
                    border: '1px solid rgba(215,195,179,0.25)',
                    backdropFilter: 'blur(20px)',
                    padding: '40px 48px 36px',
                    marginBottom: 48,
                    boxShadow: '0 4px 40px rgba(44,62,80,0.06)',
                }}>
                    {/* Background radial glow */}
                    <div aria-hidden style={{
                        position: 'absolute', top: -60, right: -60,
                        width: 340, height: 340,
                        background: 'radial-gradient(circle, rgba(215,195,179,0.28) 0%, transparent 70%)',
                        pointerEvents: 'none', borderRadius: '50%',
                    }} />
                    {/* Decorative concentric arc */}
                    <svg aria-hidden style={{ position: 'absolute', right: 48, top: '50%', transform: 'translateY(-50%)', opacity: 0.22 }} width={180} height={180}>
                        <circle cx={90} cy={90} r={70} fill="none" stroke="#D7C3B3" strokeWidth="1.5" />
                        <circle cx={90} cy={90} r={50} fill="none" stroke="#D7C3B3" strokeWidth="1.5" />
                        <circle cx={90} cy={90} r={30} fill="none" stroke="#2C3E50" strokeWidth="2" />
                    </svg>

                    {/* Top row: date pill + export button */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            {/* Live status dot */}
                            <div style={{ position: 'relative', width: 8, height: 8 }}>
                                <div style={{ position: 'absolute', inset: -3, borderRadius: '50%', background: 'rgba(74,103,65,0.2)', animation: 'pulseRing 2s ease-in-out infinite' }} />
                                <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#4A6741' }} />
                            </div>
                            <span style={{ fontFamily: 'var(--font-sans)', fontSize: 11, fontWeight: 600, letterSpacing: '0.1em', color: '#4A6741' }}>LIVE</span>
                            <span style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: '#B0B0B0', marginLeft: 4 }}>
                                {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
                            </span>
                        </div>
                    </div>

                    {/* Overline label */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
                        <div style={{ width: 32, height: 2, background: 'linear-gradient(90deg, #D7C3B3, transparent)', borderRadius: 99 }} />
                        <span style={{ fontFamily: 'var(--font-sans)', fontSize: 10, fontWeight: 700, letterSpacing: '0.14em', color: '#C8B89A' }}>
                            {activePeriod.toUpperCase()} INTELLIGENCE REPORT
                        </span>
                    </div>

                    {/* Main headline */}
                    <h1 style={{
                        fontFamily: 'var(--font-serif), serif',
                        fontSize: 64,
                        color: '#1A1A1A',
                        letterSpacing: '-0.03em',
                        lineHeight: 1.0,
                        margin: '0 0 12px',
                    }}>
                        Your Focus<br />
                        <span style={{ color: '#B07A4A' }}>Report.</span>
                    </h1>
                    <p style={{ fontFamily: 'var(--font-sans)', fontSize: 14, color: '#888', margin: '0 0 32px', lineHeight: 1.5, maxWidth: 420 }}>
                        A deep look into your attention patterns, distractions, and productivity rhythms — all in one place.
                    </p>

                    {/* Divider */}
                    <div style={{ height: 1, background: 'linear-gradient(90deg, rgba(215,195,179,0.5), rgba(44,62,80,0.08), transparent)', marginBottom: 28 }} />

                    {/* Quick-stat chips */}
                    <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
                        {[
                            { label: 'Study Time', value: `${Math.floor(totalStudyMinutes / 60)}h ${totalStudyMinutes % 60}m`, accent: '#2C3E50' },
                            { label: 'Sessions', value: String(totalSessions), accent: '#B07A4A' },
                            { label: 'Focus Score', value: `${avgFocusScore} / 100`, accent: '#4A6741' },
                            { label: 'Interruptions', value: String(totalInterruptions), accent: '#C0392B' },
                        ].map(({ label, value, accent }) => (
                            <div key={label} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                <span style={{ fontFamily: 'var(--font-sans)', fontSize: 9, fontWeight: 700, letterSpacing: '0.1em', color: '#B0B0B0' }}>{label}</span>
                                <span style={{ fontFamily: 'var(--font-serif)', fontSize: 22, color: accent, letterSpacing: '-0.02em', lineHeight: 1 }}>{value}</span>
                            </div>
                        ))}
                    </div>
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

                {/* ── Decorative section divider ── */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 32 }}>
                    <div style={{ height: 1, flex: 1, background: 'linear-gradient(90deg, rgba(215,195,179,0.5), transparent)' }} />
                    <span style={{ fontFamily: 'var(--font-sans)', fontSize: 10, fontWeight: 600, letterSpacing: '0.12em', color: '#C8B89A' }}>STUDY TRENDS</span>
                    <div style={{ height: 1, flex: 1, background: 'linear-gradient(270deg, rgba(215,195,179,0.5), transparent)' }} />
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

                {/* ── Decorative section divider ── */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 32 }}>
                    <div style={{ height: 1, flex: 1, background: 'linear-gradient(90deg, rgba(44,62,80,0.15), transparent)' }} />
                    <span style={{ fontFamily: 'var(--font-sans)', fontSize: 10, fontWeight: 600, letterSpacing: '0.12em', color: '#A8A9AD' }}>INTERRUPTIONS</span>
                    <div style={{ height: 1, flex: 1, background: 'linear-gradient(270deg, rgba(44,62,80,0.15), transparent)' }} />
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

                {/* ── Phone Pickups Section ── */}
                <div
                    ref={phonePickupsRef}
                    className="mb-[64px] animate-fade-up"
                    style={{ animationDelay: '460ms', scrollMarginTop: '96px', position: 'relative' }}
                >
                    {/* Background glow behind this section */}
                    <div aria-hidden style={{
                        position: 'absolute',
                        width: 400,
                        height: 300,
                        right: 0,
                        top: -40,
                        background: 'radial-gradient(ellipse, rgba(176,122,74,0.07) 0%, transparent 70%)',
                        pointerEvents: 'none',
                        borderRadius: '50%',
                    }} />

                    {/* Decorative divider */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 32 }}>
                        <div style={{ height: 1, flex: 1, background: 'linear-gradient(90deg, rgba(176,122,74,0.4), transparent)' }} />
                        <span style={{ fontFamily: 'var(--font-sans)', fontSize: 10, fontWeight: 600, letterSpacing: '0.12em', color: '#B07A4A' }}>PHONE ACTIVITY</span>
                        <div style={{ height: 1, flex: 1, background: 'linear-gradient(270deg, rgba(176,122,74,0.4), transparent)' }} />
                    </div>

                    {/* Section header */}
                    <div className="flex items-center gap-4 mb-8">
                        <div style={{ width: 3, height: 28, background: 'linear-gradient(180deg, #B07A4A, #8B5E3C)', borderRadius: 99 }} />
                        <div>
                            <span className="micro-label" style={{ color: '#B07A4A' }}>DISTRACTION ANALYSIS</span>
                            <h2 style={{ fontFamily: 'var(--font-serif), serif', fontSize: 26, color: '#1A1A1A', letterSpacing: '-0.015em', margin: '2px 0 0' }}>
                                Phone Pickups
                            </h2>
                        </div>
                    </div>

                    {/* KPI mini-cards */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                        <LiquidCard padding="p-6">
                            <p className="micro-label mb-2" style={{ color: '#B07A4A' }}>TOTAL PICKUPS</p>
                            <p style={{ fontFamily: 'var(--font-serif)', fontSize: 36, color: '#1A1A1A', margin: 0 }}>{totalPhonePickups}</p>
                            <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>times today</p>
                        </LiquidCard>
                        <LiquidCard padding="p-6">
                            <p className="micro-label mb-2" style={{ color: '#4A6741' }}>AVG. FOCUS WINDOW</p>
                            <p style={{ fontFamily: 'var(--font-serif)', fontSize: 36, color: '#1A1A1A', margin: 0 }}>{avgUnattendedMinutes}<span style={{ fontSize: 18, color: '#888' }}> min</span></p>
                            <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>avg. between pickups</p>
                        </LiquidCard>
                        <LiquidCard padding="p-6">
                            <p className="micro-label mb-2" style={{ color: '#2C3E50' }}>BEST STREAK</p>
                            <p style={{ fontFamily: 'var(--font-serif)', fontSize: 36, color: '#1A1A1A', margin: 0 }}>{longestUnattended}<span style={{ fontSize: 18, color: '#888' }}> min</span></p>
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
                            <div style={{ background: 'rgba(176,122,74,0.08)', border: '1px solid rgba(176,122,74,0.2)', borderRadius: 8, padding: '6px 14px', fontSize: 11, color: '#B07A4A', fontFamily: 'var(--font-sans)', fontWeight: 600, letterSpacing: '0.05em' }}>
                                TODAY
                            </div>
                        </div>
                        <PhonePickupsChart />

                        {/* Event timeline list */}
                        <div style={{ marginTop: 28, borderTop: '1px solid rgba(0,0,0,0.05)', paddingTop: 20 }}>
                            <p className="micro-label mb-4">ALL PICKUP EVENTS</p>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 220, overflowY: 'auto', paddingRight: 4 }}>
                                {[...require('../../lib/data').phonePickupEvents].map((e: any, i: number) => (
                                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '8px 12px', borderRadius: 8, background: i % 2 === 0 ? 'rgba(0,0,0,0.02)' : 'transparent' }}>
                                        <span style={{ fontSize: 12, fontWeight: 600, color: '#1A1A1A', width: 44, flexShrink: 0 }}>{e.time}</span>
                                        <span style={{ fontSize: 12, color: '#B07A4A', flexShrink: 0 }}>📱 picked up for {e.durationSeconds}s</span>
                                        {e.minutesUnattended > 0 && (
                                            <span style={{ fontSize: 11, color: '#888' }}>· {e.minutesUnattended} min phone-free before this</span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    </LiquidCard>
                </div>

                {/* ── Face Detection Section ── */}
                <div
                    ref={faceDetectionRef}
                    className="mb-[64px] animate-fade-up"
                    style={{ animationDelay: '500ms', scrollMarginTop: '96px', position: 'relative' }}
                >
                    {/* Background glow */}
                    <div aria-hidden style={{
                        position: 'absolute',
                        width: 400,
                        height: 300,
                        left: 0,
                        top: -40,
                        background: 'radial-gradient(ellipse, rgba(44,62,80,0.06) 0%, transparent 70%)',
                        pointerEvents: 'none',
                        borderRadius: '50%',
                    }} />

                    {/* Decorative divider */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 32 }}>
                        <div style={{ height: 1, flex: 1, background: 'linear-gradient(90deg, rgba(44,62,80,0.25), transparent)' }} />
                        <span style={{ fontFamily: 'var(--font-sans)', fontSize: 10, fontWeight: 600, letterSpacing: '0.12em', color: '#2C3E50' }}>GAZE ACTIVITY</span>
                        <div style={{ height: 1, flex: 1, background: 'linear-gradient(270deg, rgba(44,62,80,0.25), transparent)' }} />
                    </div>

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
                            {[
                                { color: '#4A6741', label: 'Low (<20s)' },
                                { color: '#B07A4A', label: 'Medium (20–60s)' },
                                { color: '#C0392B', label: 'High (>60s)' },
                            ].map(({ color, label }) => (
                                <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: color }} />
                                    <span style={{ fontSize: 11, color: '#888' }}>{label}</span>
                                </div>
                            ))}
                        </div>

                        <div style={{ marginTop: 20, borderTop: '1px solid rgba(0,0,0,0.05)', paddingTop: 20 }}>
                            <p className="micro-label mb-4">ALL LOOK-AWAY EVENTS</p>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 220, overflowY: 'auto', paddingRight: 4 }}>
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

                {/* ── Decorative divider before session log ── */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 32 }}>
                    <div style={{ height: 1, flex: 1, background: 'linear-gradient(90deg, rgba(44,62,80,0.12), transparent)' }} />
                    <span style={{ fontFamily: 'var(--font-sans)', fontSize: 10, fontWeight: 600, letterSpacing: '0.12em', color: '#A8A9AD' }}>SESSION LOG</span>
                    <div style={{ height: 1, flex: 1, background: 'linear-gradient(270deg, rgba(44,62,80,0.12), transparent)' }} />
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

export default withAuthenticationRequired(StatsDashboard, {
    onRedirecting: () => (
        <div className="flex min-h-screen items-center justify-center pt-[64px]" style={{ background: '#F9F8F5' }}>
            <span style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: '#888' }}>Checking authentication...</span>
        </div>
    ),
    loginOptions: {
        authorizationParams: {
            screen_hint: 'signup'
        }
    }
});
