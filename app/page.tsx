'use client';

import { useState } from 'react';
import Link from 'next/link';
import LiquidCard from '../components/LiquidCard';
import SessionSetupModal from '../components/SessionSetupModal';
import PomodoroTimer from '../components/PomodoroTimer';
import { Activity, Clock, BarChart3, Eye, Timer, Lightbulb, TrendingUp, Users, Zap } from 'lucide-react';

/* ─── Marquee data ─── */
const marqueeItems = [
  { value: '15,000+', label: 'Focus Hours Logged' },
  { value: '98%', label: 'Session Accuracy' },
  { value: '3.2×', label: 'Productivity Lift' },
  { value: '42 min', label: 'Avg Deep Work Block' },
  { value: '12,800+', label: 'Distractions Caught' },
  { value: '4.9 / 5', label: 'User Satisfaction' },
];
// duplicate for seamless loop
const allItems = [...marqueeItems, ...marqueeItems];

/* ─── Stats callout data ─── */
const socialStats = [
  { icon: TrendingUp, value: '3.2×', label: 'Average productivity improvement reported by users after 30 days.' },
  { icon: Users, value: '12K+', label: 'Students and professionals tracking focus with Aurelius monthly.' },
  { icon: Zap, value: '94%', label: 'of sessions are completed without a major distraction event.' },
];

export default function LandingPage() {
  const [isSetupOpen, setIsSetupOpen] = useState(false);
  const [isSessionActive, setIsSessionActive] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);

  const handleEndSession = async () => {
    // 1. Stop trackers
    try {
      await fetch('http://localhost:8000/stop/study_tracker', { method: 'POST' });
      await fetch('http://localhost:8000/stop/noti_watcher', { method: 'POST' });
    } catch (err) {
      console.error('Failed to stop scripts', err);
    }
    setIsSessionActive(false);

    // 2. Sync data to/from Vultr
    setIsSyncing(true);
    setSyncResult(null);
    try {
      // Send CSVs
      await fetch('http://localhost:8000/sync/send', { method: 'POST' });
      // Poll until send completes (max ~30s)
      for (let i = 0; i < 30; i++) {
        await new Promise(r => setTimeout(r, 1000));
        const res = await fetch('http://localhost:8000/sync/send/status');
        const data = await res.json();
        if (data.status !== 'running') break;
      }
      // Receive data from server
      const recvRes = await fetch('http://localhost:8000/sync/receive', { method: 'POST' });
      const recvData = await recvRes.json();
      const ok = recvData.status === 'ok';
      setSyncResult(ok ? 'Data synced successfully!' : 'Sync completed with some issues.');
    } catch (err) {
      console.error('Sync failed', err);
      setSyncResult('Sync failed — server may be offline.');
    } finally {
      setIsSyncing(false);
      setTimeout(() => setSyncResult(null), 5000);
    }
  };

  return (
    <main className="min-h-screen">

      {/* ━━━ SECTION 1: HERO ━━━ */}
      <section
        className="relative flex flex-col items-center justify-center min-h-screen px-12 overflow-hidden"
        style={{
          background: '#F9F8F5',
          backgroundImage: [
            'radial-gradient(ellipse 80% 50% at 50% -10%, rgba(215,195,179,0.30) 0%, transparent 70%)',
            'radial-gradient(ellipse 40% 40% at 80% 60%, rgba(44,62,80,0.04) 0%, transparent 60%)',
          ].join(', '),
          paddingTop: 64,
        }}
      >
        {/* Dot-grid texture */}
        <div
          aria-hidden
          style={{
            position: 'absolute',
            inset: 0,
            backgroundImage: 'radial-gradient(circle, rgba(44,62,80,0.09) 1px, transparent 1px)',
            backgroundSize: '32px 32px',
            maskImage: 'radial-gradient(ellipse 70% 70% at 50% 50%, black 30%, transparent 100%)',
            WebkitMaskImage: 'radial-gradient(ellipse 70% 70% at 50% 50%, black 30%, transparent 100%)',
            pointerEvents: 'none',
          }}
        />

        {/* Decorative blurred orb top-right */}
        <div
          aria-hidden
          className="animate-pulse-glow"
          style={{
            position: 'absolute',
            width: 520,
            height: 520,
            right: '-80px',
            top: '-80px',
            background: 'radial-gradient(circle, rgba(215,195,179,0.55) 0%, transparent 70%)',
            borderRadius: '50%',
            pointerEvents: 'none',
          }}
        />

        {/* Decorative blurred orb bottom-left */}
        <div
          aria-hidden
          style={{
            position: 'absolute',
            width: 380,
            height: 380,
            left: '-60px',
            bottom: '5%',
            background: 'radial-gradient(circle, rgba(44,62,80,0.06) 0%, transparent 70%)',
            borderRadius: '50%',
            pointerEvents: 'none',
          }}
        />

        {/* Thin horizontal accent line */}
        <div
          aria-hidden
          style={{
            position: 'absolute',
            top: '62%',
            left: 0,
            right: 0,
            height: 1,
            background: 'linear-gradient(90deg, transparent 0%, rgba(215,195,179,0.45) 30%, rgba(44,62,80,0.10) 70%, transparent 100%)',
            pointerEvents: 'none',
          }}
        />

        {/* Hero content */}
        <div className="w-full max-w-[1440px] flex flex-col items-start justify-center animate-fade-up" style={{ position: 'relative', zIndex: 1 }}>
          <span className="micro-label" style={{ color: 'var(--color-accent-metal)', marginBottom: 24 }}>
            FOCUS INTELLIGENCE PLATFORM
          </span>

          <h1
            style={{
              fontFamily: 'var(--font-serif), serif',
              fontSize: 'clamp(64px, 8vw, 96px)',
              fontWeight: 400,
              letterSpacing: '-0.03em',
              lineHeight: 1.05,
              color: 'var(--color-text-primary)',
              marginBottom: 32,
              maxWidth: 900,
            }}
          >
            The discipline to study.<br />The data to improve.
          </h1>

          <p
            style={{
              fontFamily: 'var(--font-sans), sans-serif',
              fontSize: 17,
              lineHeight: 1.6,
              color: 'var(--color-text-secondary)',
              maxWidth: 560,
              marginBottom: 48,
            }}
          >
            Aurelius logs every interval of focus and every moment of distraction, offering you a high-resolution map of your attention. Master your environment. Command your time.
          </p>

          <div className="flex items-center gap-4">
            {!isSessionActive ? (
              <button onClick={() => setIsSetupOpen(true)} className="btn-primary btn-large">
                Start a Session
              </button>
            ) : (
              <button
                onClick={handleEndSession}
                disabled={isSyncing}
                className="btn-large"
                style={{ background: isSyncing ? '#888' : '#C0392B', color: '#fff', border: 'none', borderRadius: 99, padding: '0 32px', fontWeight: 600, opacity: isSyncing ? 0.7 : 1 }}
              >
                {isSyncing ? 'Syncing…' : 'End Session'}
              </button>
            )}
            <Link href="/stats" className="btn-ghost btn-large">
              View Demo Stats
            </Link>
          </div>

          {/* Sync status feedback */}
          {(isSyncing || syncResult) && (
            <div className="mt-4 flex items-center gap-2" style={{ fontFamily: 'var(--font-sans)', fontSize: 13 }}>
              {isSyncing && (
                <span style={{ color: '#B07A4A' }}>⏳ Uploading session data & syncing…</span>
              )}
              {syncResult && !isSyncing && (
                <span style={{ color: syncResult.includes('success') ? '#4A6741' : '#C0392B' }}>
                  {syncResult}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Floating Session Card Visual */}
        <div className="absolute right-[10%] top-[35%] animate-float hidden lg:block" style={{ width: 400, zIndex: 1 }}>
          <LiquidCard padding="p-8">
            <div className="flex justify-between items-center mb-6">
              <div className="flex items-center gap-2">
                <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: 'var(--color-positive)' }} />
                <span className="micro-label">LIVE SESSION</span>
              </div>
              <span className="micro-label">PHYSICS</span>
            </div>

            <div
              style={{
                fontFamily: 'var(--font-serif), serif',
                fontSize: 64,
                letterSpacing: '-0.03em',
                lineHeight: 1,
                color: 'var(--color-text-primary)',
                marginBottom: 8,
              }}
            >
              02:47:13
            </div>

            <p className="micro-label mb-8" style={{ color: 'var(--color-positive)' }}>
              CURRENT FOCUS SCORE: 92
            </p>

            <div className="h-[48px] w-full flex items-end gap-1 opacity-50">
              {[40, 60, 45, 80, 70, 90, 85, 95, 100].map((h, i) => (
                <div key={i} className="flex-1 rounded-t-sm" style={{ height: `${h}%`, backgroundColor: 'var(--color-accent-trust)' }} />
              ))}
            </div>
          </LiquidCard>
        </div>
      </section>

      {/* ━━━ MARQUEE STRIP ━━━ */}
      <div
        style={{
          borderTop: '1px solid rgba(0,0,0,0.06)',
          borderBottom: '1px solid rgba(0,0,0,0.06)',
          padding: '18px 0',
          background: 'rgba(255,255,255,0.5)',
          overflow: 'hidden',
          backdropFilter: 'blur(8px)',
        }}
      >
        <div className="animate-marquee" style={{ gap: 0 }}>
          {allItems.map((item, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '0 48px',
                borderRight: '1px solid rgba(0,0,0,0.07)',
                flexShrink: 0,
                whiteSpace: 'nowrap',
              }}
            >
              <span
                style={{
                  fontFamily: 'var(--font-serif), serif',
                  fontSize: 20,
                  letterSpacing: '-0.02em',
                  color: '#1A1A1A',
                  fontWeight: 400,
                }}
              >
                {item.value}
              </span>
              <span
                style={{
                  fontFamily: 'var(--font-sans), sans-serif',
                  fontSize: 11,
                  fontWeight: 600,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase' as const,
                  color: '#A8A9AD',
                }}
              >
                {item.label}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* ━━━ SECTION 2: FEATURES ━━━ */}
      <section
        id="features"
        className="py-[128px] px-12 relative overflow-hidden"
        style={{ background: '#F9F8F5' }}
      >
        {/* Section label + heading */}
        <div className="max-w-[1440px] mx-auto mb-16">
          <span className="micro-label" style={{ color: 'var(--color-accent-metal)', display: 'block', marginBottom: 12 }}>PLATFORM CAPABILITIES</span>
          <h2 style={{ fontFamily: 'var(--font-serif), serif', fontSize: 'clamp(32px,4vw,48px)', color: '#1A1A1A', letterSpacing: '-0.02em', lineHeight: 1.1, maxWidth: 560, margin: 0 }}>
            Everything you need to master your focus.
          </h2>
        </div>

        {/* Large decorative circle behind cards */}
        <div
          aria-hidden
          style={{
            position: 'absolute',
            width: 600,
            height: 600,
            right: '-150px',
            top: '50%',
            transform: 'translateY(-50%)',
            border: '1px solid rgba(215,195,179,0.25)',
            borderRadius: '50%',
            pointerEvents: 'none',
          }}
        />
        <div
          aria-hidden
          style={{
            position: 'absolute',
            width: 380,
            height: 380,
            right: '5px',
            top: '50%',
            transform: 'translateY(-50%)',
            border: '1px solid rgba(215,195,179,0.18)',
            borderRadius: '50%',
            pointerEvents: 'none',
          }}
        />

        <div className="max-w-[1440px] mx-auto grid grid-cols-1 md:grid-cols-3 gap-8 relative z-10">
          <LiquidCard padding="p-[40px] px-[32px]">
            <Clock size={24} strokeWidth={1.5} color="var(--color-accent-metal)" className="mb-6" />
            <h3 className="mb-4" style={{ fontFamily: 'var(--font-serif), serif', fontSize: 22, color: 'var(--color-text-primary)' }}>Session Tracking</h3>
            <p style={{ fontFamily: 'var(--font-sans), sans-serif', fontSize: 15, color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
              Log study sessions with start/end times, subject tags, and goals. Understand how long you actually focus vs. how long you sit down.
            </p>
          </LiquidCard>

          <LiquidCard padding="p-[40px] px-[32px]">
            <Activity size={24} strokeWidth={1.5} color="var(--color-accent-metal)" className="mb-6" />
            <h3 className="mb-4" style={{ fontFamily: 'var(--font-serif), serif', fontSize: 22, color: 'var(--color-text-primary)' }}>Distraction Intelligence</h3>
            <p style={{ fontFamily: 'var(--font-sans), sans-serif', fontSize: 15, color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
              Aurelius logs every interruption: notification source, app name, time elapsed, and how long it took you to re-engage. See exactly what's breaking your flow.
            </p>
          </LiquidCard>

          <LiquidCard padding="p-[40px] px-[32px]">
            <BarChart3 size={24} strokeWidth={1.5} color="var(--color-accent-metal)" className="mb-6" />
            <h3 className="mb-4" style={{ fontFamily: 'var(--font-serif), serif', fontSize: 22, color: 'var(--color-text-primary)' }}>Progress Analytics</h3>
            <p style={{ fontFamily: 'var(--font-sans), sans-serif', fontSize: 15, color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
              Weekly and monthly trend lines, streak tracking, and focus quality scores. Turn raw session data into actionable insight.
            </p>
          </LiquidCard>
        </div>

        {/* Second row */}
        <div className="max-w-[1440px] mx-auto grid grid-cols-1 md:grid-cols-3 gap-8 mt-8 relative z-10">
          <LiquidCard padding="p-[40px] px-[32px]">
            <Eye size={24} strokeWidth={1.5} color="var(--color-accent-metal)" className="mb-6" />
            <h3 className="mb-4" style={{ fontFamily: 'var(--font-serif), serif', fontSize: 22, color: 'var(--color-text-primary)' }}>Face Detection</h3>
            <p style={{ fontFamily: 'var(--font-sans), sans-serif', fontSize: 15, color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
              Aurelius uses your camera to detect when you look away from the screen, logging every distraction moment so you know exactly where your focus breaks.
            </p>
          </LiquidCard>

          <LiquidCard padding="p-[40px] px-[32px]">
            <Timer size={24} strokeWidth={1.5} color="var(--color-accent-metal)" className="mb-6" />
            <h3 className="mb-4" style={{ fontFamily: 'var(--font-serif), serif', fontSize: 22, color: 'var(--color-text-primary)' }}>Pomodoro Focus Mode</h3>
            <p style={{ fontFamily: 'var(--font-sans), sans-serif', fontSize: 15, color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
              Built-in Pomodoro timer with customizable intervals. Structure your sessions, take timed breaks, and build the rhythm that maximizes deep work.
            </p>
          </LiquidCard>

          <LiquidCard padding="p-[40px] px-[32px]">
            <Lightbulb size={24} strokeWidth={1.5} color="var(--color-accent-metal)" className="mb-6" />
            <h3 className="mb-4" style={{ fontFamily: 'var(--font-serif), serif', fontSize: 22, color: 'var(--color-text-primary)' }}>Actionable Insights</h3>
            <p style={{ fontFamily: 'var(--font-sans), sans-serif', fontSize: 15, color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
              Aurelius surfaces patterns in your data — your best focus hours, most distracting apps, and consistency streaks — so you can study smarter, not just longer.
            </p>
          </LiquidCard>
        </div>
      </section>

      {/* ━━━ SOCIAL PROOF / STATS CALLOUT ━━━ */}
      <section
        style={{
          background: 'linear-gradient(135deg, #2C3E50 0%, #1a252f 100%)',
          padding: '100px 48px',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Decorative rings */}
        <div aria-hidden style={{ position: 'absolute', width: 700, height: 700, right: '-200px', top: '-200px', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '50%', pointerEvents: 'none' }} />
        <div aria-hidden style={{ position: 'absolute', width: 440, height: 440, right: '-50px', top: '-50px', border: '1px solid rgba(255,255,255,0.04)', borderRadius: '50%', pointerEvents: 'none' }} />
        <div aria-hidden style={{ position: 'absolute', width: 500, height: 500, left: '-120px', bottom: '-120px', border: '1px solid rgba(215,195,179,0.06)', borderRadius: '50%', pointerEvents: 'none' }} />

        <div className="max-w-[1440px] mx-auto">
          <div style={{ textAlign: 'center', marginBottom: 64 }}>
            <span style={{ fontFamily: 'var(--font-sans)', fontSize: 11, fontWeight: 600, letterSpacing: '0.12em', color: 'rgba(215,195,179,0.7)', textTransform: 'uppercase' as const }}>
              PROOF OF IMPACT
            </span>
            <h2 style={{ fontFamily: 'var(--font-serif), serif', fontSize: 'clamp(32px,4vw,52px)', color: '#F9F8F5', letterSpacing: '-0.02em', lineHeight: 1.1, marginTop: 12, marginBottom: 0 }}>
              Focus is a skill.<br />We help you measure it.
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {socialStats.map(({ icon: Icon, value, label }, i) => (
              <div
                key={i}
                style={{
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: 20,
                  padding: '48px 40px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 16,
                }}
              >
                <div style={{ width: 44, height: 44, borderRadius: 12, background: 'rgba(215,195,179,0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Icon size={20} strokeWidth={1.5} color="#D7C3B3" />
                </div>
                <div style={{ fontFamily: 'var(--font-serif), serif', fontSize: 56, letterSpacing: '-0.03em', color: '#F9F8F5', lineHeight: 1 }}>
                  {value}
                </div>
                <p style={{ fontFamily: 'var(--font-sans)', fontSize: 14, color: 'rgba(249,248,245,0.55)', lineHeight: 1.6, margin: 0 }}>
                  {label}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ━━━ SECTION 3: ATTENTION + POMODORO ━━━ */}
      <section className="py-[128px] px-12 relative overflow-hidden" style={{ background: '#F9F8F5' }}>
        {/* Background accent */}
        <div aria-hidden style={{ position: 'absolute', inset: 0, backgroundImage: 'radial-gradient(circle, rgba(215,195,179,0.12) 1px, transparent 1px)', backgroundSize: '40px 40px', pointerEvents: 'none' }} />

        <div className="max-w-[1440px] mx-auto w-full flex flex-col md:flex-row items-center justify-between gap-16 relative z-10">
          <div className="md:w-1/2 flex flex-col items-start z-10">
            {/* Decorative vertical rule */}
            <div style={{ width: 2, height: 48, background: 'linear-gradient(180deg, #D7C3B3, transparent)', borderRadius: 99, marginBottom: 24 }} />
            <h2 className="mb-6" style={{ fontFamily: 'var(--font-serif), serif', fontSize: 'clamp(40px, 5vw, 56px)', color: 'var(--color-text-primary)', letterSpacing: '-0.02em', lineHeight: 1.1 }}>
              Your attention,<br />quantified.
            </h2>
            <p className="mb-8 max-w-[480px]" style={{ fontFamily: 'var(--font-sans), sans-serif', fontSize: 17, color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
              Stop guessing if you had a productive day. We break down your habits into digestible, actionable metrics, so you can train your focus like a muscle.
            </p>
            <Link href="/stats" className="btn-primary">
              View Insights Demo
            </Link>
          </div>

          <div className="md:w-1/2 flex justify-center items-center px-4">
            <PomodoroTimer />
          </div>
        </div>
      </section>

      {/* ━━━ FOOTER ━━━ */}
      <footer className="py-[64px] px-12" style={{ borderTop: '1px solid rgba(0,0,0,0.06)', background: '#F9F8F5' }}>
        <div className="max-w-[1440px] mx-auto">
          {/* Top row */}
          <div className="flex flex-col md:flex-row justify-between items-start gap-8 mb-12">
            {/* Brand */}
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div style={{ width: 3, height: 20, background: '#D7C3B3', borderRadius: 2 }} />
                <span style={{ fontFamily: 'var(--font-sans)', fontSize: 13, fontWeight: 600, letterSpacing: '0.15em', textTransform: 'uppercase' as const, color: '#1A1A1A' }}>AURELIUS</span>
              </div>
              <p style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: '#888', lineHeight: 1.6, maxWidth: 280 }}>
                AI-powered focus intelligence for students and professionals who take their time seriously.
              </p>
            </div>

            {/* Nav links */}
            <div className="flex gap-16">
              <div>
                <p style={{ fontFamily: 'var(--font-sans)', fontSize: 11, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase' as const, color: '#A8A9AD', marginBottom: 16 }}>PRODUCT</p>
                <div className="flex flex-col gap-3">
                  <Link href="/" style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: '#666', textDecoration: 'none' }}>Overview</Link>
                  <Link href="/stats" style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: '#666', textDecoration: 'none' }}>Statistics</Link>
                </div>
              </div>
              <div>
                <p style={{ fontFamily: 'var(--font-sans)', fontSize: 11, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase' as const, color: '#A8A9AD', marginBottom: 16 }}>PLATFORM</p>
                <div className="flex flex-col gap-3">
                  <span style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: '#ccc', cursor: 'default' }}>Auth0 Login <span style={{ fontSize: 10, color: '#D7C3B3' }}>— coming soon</span></span>
                </div>
              </div>
            </div>
          </div>

          {/* Divider */}
          <div style={{ height: 1, background: 'rgba(0,0,0,0.06)', marginBottom: 24 }} />

          {/* Bottom row */}
          <div className="flex flex-col md:flex-row items-center justify-between gap-2">
            <span style={{ fontFamily: 'var(--font-sans)', fontSize: 12, color: '#A8A9AD' }}>
              © {new Date().getFullYear()} Aurelius Focus Systems. All rights reserved.
            </span>
            <span style={{ fontFamily: 'var(--font-sans)', fontSize: 12, color: '#C8B89A', letterSpacing: '0.06em' }}>
              BUILT FOR DEEP WORK
            </span>
          </div>
        </div>
      </footer>

      <SessionSetupModal
        isOpen={isSetupOpen}
        onClose={() => {
          setIsSetupOpen(false);
          setIsSessionActive(true);
        }}
      />
    </main>
  );
}
