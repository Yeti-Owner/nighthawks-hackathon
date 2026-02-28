'use client';

import Link from 'next/link';
import LiquidCard from '../components/LiquidCard';
import PomodoroTimer from '../components/PomodoroTimer';
import { Activity, Clock, BarChart3 } from 'lucide-react';

export default function LandingPage() {
  return (
    <main className="min-h-screen">
      {/* SECTION 1: HERO */}
      <section
        className="relative flex flex-col items-center justify-center min-h-screen px-12 overflow-hidden"
        style={{
          background: '#F9F8F5',
          backgroundImage: 'radial-gradient(ellipse 80% 50% at 50% -10%, rgba(215, 195, 179, 0.25) 0%, transparent 70%)',
          paddingTop: 64, // offset for navbar
        }}
      >
        <div className="w-full max-w-[1440px] flex flex-col items-start justify-center animate-fade-up">
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
            <Link href="/stats" className="btn-primary btn-large">
              Start a Session
            </Link>
            <Link href="/stats" className="btn-ghost btn-large">
              View Demo Stats
            </Link>
          </div>
        </div>

        {/* Floating Session Card Visual */}
        <div className="absolute right-[10%] top-[35%] animate-float hidden lg:block" style={{ width: 400 }}>
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
              {/* Decorative sparkline bars */}
              {[40, 60, 45, 80, 70, 90, 85, 95, 100].map((h, i) => (
                <div key={i} className="flex-1 rounded-t-sm" style={{ height: `${h}%`, backgroundColor: 'var(--color-accent-trust)' }} />
              ))}
            </div>
          </LiquidCard>
        </div>
      </section>

      {/* SECTION 2: FEATURES */}
      <section id="features" className="py-[128px] px-12 bg-[#F9F8F5]">
        <div className="max-w-[1440px] mx-auto grid grid-cols-1 md:grid-cols-3 gap-8">

          {/* Feature 1 */}
          <LiquidCard padding="p-[40px] px-[32px]">
            <Clock size={24} strokeWidth={1.5} color="var(--color-accent-metal)" className="mb-6" />
            <h3 className="mb-4" style={{ fontFamily: 'var(--font-serif), serif', fontSize: 22, color: 'var(--color-text-primary)' }}>
              Session Tracking
            </h3>
            <p style={{ fontFamily: 'var(--font-sans), sans-serif', fontSize: 15, color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
              Log study sessions with start/end times, subject tags, and goals. Understand how long you actually focus vs. how long you sit down.
            </p>
          </LiquidCard>

          {/* Feature 2 */}
          <LiquidCard padding="p-[40px] px-[32px]">
            <Activity size={24} strokeWidth={1.5} color="var(--color-accent-metal)" className="mb-6" />
            <h3 className="mb-4" style={{ fontFamily: 'var(--font-serif), serif', fontSize: 22, color: 'var(--color-text-primary)' }}>
              Distraction Intelligence
            </h3>
            <p style={{ fontFamily: 'var(--font-sans), sans-serif', fontSize: 15, color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
              Aurelius logs every interruption: notification source, app name, time elapsed, and how long it took you to re-engage. See exactly what's breaking your flow.
            </p>
          </LiquidCard>

          {/* Feature 3 */}
          <LiquidCard padding="p-[40px] px-[32px]">
            <BarChart3 size={24} strokeWidth={1.5} color="var(--color-accent-metal)" className="mb-6" />
            <h3 className="mb-4" style={{ fontFamily: 'var(--font-serif), serif', fontSize: 22, color: 'var(--color-text-primary)' }}>
              Progress Analytics
            </h3>
            <p style={{ fontFamily: 'var(--font-sans), sans-serif', fontSize: 15, color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
              Weekly and monthly trend lines, streak tracking, and focus quality scores. Turn raw session data into actionable insight.
            </p>
          </LiquidCard>

        </div>
      </section>

      {/* SECTION 3: STATS PREVIEW TEASER */}
      <section className="py-[128px] px-12 relative overflow-hidden flex items-center bg-[#F9F8F5]">
        <div className="max-w-[1440px] mx-auto w-full flex flex-col md:flex-row items-center justify-between gap-16">
          <div className="md:w-1/2 flex flex-col items-start z-10">
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

      {/* SECTION 4: FOOTER */}
      <footer className="py-[48px] px-12 bg-[#F9F8F5]" style={{ borderTop: '1px solid rgba(0,0,0,0.06)' }}>
        <div className="max-w-[1440px] mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          <div style={{ fontFamily: 'var(--font-sans), sans-serif', fontSize: 12, color: 'var(--color-text-secondary)' }}>
            &copy; {new Date().getFullYear()} Aurelius Focus Systems. All rights reserved.
          </div>
          <div className="flex gap-8">
            <Link href="/" style={{ fontFamily: 'var(--font-sans), sans-serif', fontSize: 12, color: 'var(--color-text-secondary)', textDecoration: 'none' }}>Overview</Link>
            <Link href="/#features" style={{ fontFamily: 'var(--font-sans), sans-serif', fontSize: 12, color: 'var(--color-text-secondary)', textDecoration: 'none' }}>Features</Link>
            <Link href="/stats" style={{ fontFamily: 'var(--font-sans), sans-serif', fontSize: 12, color: 'var(--color-text-secondary)', textDecoration: 'none' }}>Statistics</Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
