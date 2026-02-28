'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

const PRESETS = [
    { label: '25 min', minutes: 25 },
    { label: '45 min', minutes: 45 },
    { label: '60 min', minutes: 60 },
    { label: '90 min', minutes: 90 },
];

const RING_RADIUS = 120;
const SVG_SIZE = 280;

export default function PomodoroTimer() {
    const [selectedMinutes, setSelectedMinutes] = useState(25);
    const [customInput, setCustomInput] = useState('');
    const [showCustom, setShowCustom] = useState(false);
    const [secondsLeft, setSecondsLeft] = useState(25 * 60);
    const [isRunning, setIsRunning] = useState(false);
    const [isFinished, setIsFinished] = useState(false);
    const intervalRef = useRef<NodeJS.Timeout | null>(null);
    const totalSeconds = selectedMinutes * 60;
    const radius = RING_RADIUS;
    const circumference = 2 * Math.PI * radius;

    const reset = useCallback((minutes: number) => {
        if (intervalRef.current) clearInterval(intervalRef.current);
        setIsRunning(false);
        setIsFinished(false);
        setSecondsLeft(minutes * 60);
    }, []);

    useEffect(() => {
        if (isRunning) {
            intervalRef.current = setInterval(() => {
                setSecondsLeft(prev => {
                    if (prev <= 1) {
                        clearInterval(intervalRef.current!);
                        setIsRunning(false);
                        setIsFinished(true);
                        return 0;
                    }
                    return prev - 1;
                });
            }, 1000);
        } else {
            if (intervalRef.current) clearInterval(intervalRef.current);
        }
        return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
    }, [isRunning]);

    const selectPreset = (minutes: number) => {
        setSelectedMinutes(minutes);
        setShowCustom(false);
        setCustomInput('');
        reset(minutes);
    };

    const applyCustom = () => {
        const val = parseInt(customInput, 10);
        if (!isNaN(val) && val > 0 && val <= 300) {
            setSelectedMinutes(val);
            reset(val);
            setShowCustom(false);
        }
    };

    const mins = Math.floor(secondsLeft / 60);
    const secs = secondsLeft % 60;
    const progress = 1 - secondsLeft / totalSeconds;
    const dashOffset = circumference * (1 - progress);

    return (
        <div
            style={{
                background: 'rgba(255,255,255,0.6)',
                backdropFilter: 'blur(20px)',
                WebkitBackdropFilter: 'blur(20px)',
                border: '1px solid rgba(0,0,0,0.07)',
                borderRadius: 28,
                padding: '52px 48px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 32,
                boxShadow: '0 8px 48px rgba(0,0,0,0.07)',
                width: '100%',
                maxWidth: '100%',
            }}
        >
            {/* Header */}
            <div style={{ textAlign: 'center' }}>
                <p style={{
                    fontFamily: 'var(--font-sans), sans-serif',
                    fontSize: 10,
                    fontWeight: 600,
                    letterSpacing: '0.12em',
                    color: '#A8A9AD',
                    marginBottom: 4,
                }}>
                    FOCUS TIMER
                </p>
                <h3 style={{
                    fontFamily: 'var(--font-serif), serif',
                    fontSize: 20,
                    color: '#1A1A1A',
                    margin: 0,
                }}>
                    Pomodoro
                </h3>
            </div>

            {/* Circular progress ring */}
            <div style={{ position: 'relative', width: SVG_SIZE, height: SVG_SIZE }}>
                <svg width={SVG_SIZE} height={SVG_SIZE} style={{ transform: 'rotate(-90deg)' }}>
                    {/* Background track */}
                    <circle
                        cx={SVG_SIZE / 2} cy={SVG_SIZE / 2} r={radius}
                        fill="none"
                        stroke="rgba(0,0,0,0.06)"
                        strokeWidth="10"
                    />
                    {/* Progress arc */}
                    <circle
                        cx={SVG_SIZE / 2} cy={SVG_SIZE / 2} r={radius}
                        fill="none"
                        stroke={isFinished ? '#4A6741' : '#2C3E50'}
                        strokeWidth="10"
                        strokeLinecap="round"
                        strokeDasharray={circumference}
                        strokeDashoffset={dashOffset}
                        style={{ transition: 'stroke-dashoffset 0.9s linear, stroke 0.4s' }}
                    />
                </svg>

                {/* Centre display */}
                <div style={{
                    position: 'absolute',
                    inset: 0,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                }}>
                    {isFinished ? (
                        <span style={{ fontSize: 56, lineHeight: 1 }}>✓</span>
                    ) : (
                        <>
                            <span style={{
                                fontFamily: 'var(--font-serif), serif',
                                fontSize: 64,
                                letterSpacing: '-0.03em',
                                color: '#1A1A1A',
                                lineHeight: 1,
                            }}>
                                {String(mins).padStart(2, '0')}:{String(secs).padStart(2, '0')}
                            </span>
                            <span style={{ fontSize: 13, color: '#999', marginTop: 6 }}>
                                {isRunning ? 'focusing...' : 'paused'}
                            </span>
                        </>
                    )}
                </div>
            </div>

            {/* Controls */}
            <div style={{ display: 'flex', gap: 12, width: '100%' }}>
                <button
                    onClick={() => isFinished ? reset(selectedMinutes) : setIsRunning(r => !r)}
                    style={{
                        flex: 1,
                        height: 52,
                        background: isFinished ? '#4A6741' : '#2C3E50',
                        color: '#fff',
                        border: 'none',
                        borderRadius: 10,
                        fontFamily: 'var(--font-sans), sans-serif',
                        fontSize: 13,
                        fontWeight: 600,
                        letterSpacing: '0.04em',
                        cursor: 'pointer',
                        transition: 'opacity 0.15s, transform 0.15s',
                    }}
                    onMouseEnter={e => (e.currentTarget.style.opacity = '0.85')}
                    onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
                >
                    {isFinished ? 'RESET' : isRunning ? 'PAUSE' : 'START'}
                </button>
                {!isFinished && (
                    <button
                        onClick={() => reset(selectedMinutes)}
                        style={{
                            width: 44,
                            height: 44,
                            background: 'rgba(0,0,0,0.04)',
                            border: '1px solid rgba(0,0,0,0.08)',
                            borderRadius: 10,
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: 16,
                            transition: 'background 0.15s',
                        }}
                        onMouseEnter={e => (e.currentTarget.style.background = 'rgba(0,0,0,0.08)')}
                        onMouseLeave={e => (e.currentTarget.style.background = 'rgba(0,0,0,0.04)')}
                        title="Reset"
                    >
                        ↺
                    </button>
                )}
            </div>

            {/* Preset duration selector */}
            <div style={{ width: '100%' }}>
                <p style={{
                    fontFamily: 'var(--font-sans), sans-serif',
                    fontSize: 10,
                    fontWeight: 600,
                    letterSpacing: '0.1em',
                    color: '#A8A9AD',
                    marginBottom: 10,
                    textAlign: 'center',
                }}>
                    SET DURATION
                </p>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
                    {PRESETS.map(p => (
                        <button
                            key={p.minutes}
                            onClick={() => selectPreset(p.minutes)}
                            style={{
                                padding: '6px 14px',
                                borderRadius: 8,
                                border: selectedMinutes === p.minutes && !showCustom
                                    ? '1.5px solid #2C3E50'
                                    : '1.5px solid rgba(0,0,0,0.10)',
                                background: selectedMinutes === p.minutes && !showCustom
                                    ? 'rgba(44,62,80,0.06)'
                                    : 'transparent',
                                fontFamily: 'var(--font-sans), sans-serif',
                                fontSize: 12,
                                fontWeight: 600,
                                color: selectedMinutes === p.minutes && !showCustom ? '#2C3E50' : '#888',
                                cursor: 'pointer',
                                transition: 'all 0.15s',
                            }}
                        >
                            {p.label}
                        </button>
                    ))}
                    <button
                        onClick={() => setShowCustom(v => !v)}
                        style={{
                            padding: '6px 14px',
                            borderRadius: 8,
                            border: showCustom ? '1.5px solid #B07A4A' : '1.5px solid rgba(0,0,0,0.10)',
                            background: showCustom ? 'rgba(176,122,74,0.06)' : 'transparent',
                            fontFamily: 'var(--font-sans), sans-serif',
                            fontSize: 12,
                            fontWeight: 600,
                            color: showCustom ? '#B07A4A' : '#888',
                            cursor: 'pointer',
                            transition: 'all 0.15s',
                        }}
                    >
                        Custom
                    </button>
                </div>

                {/* Custom input */}
                {showCustom && (
                    <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                        <input
                            type="number"
                            min={1}
                            max={300}
                            placeholder="mins (1–300)"
                            value={customInput}
                            onChange={e => setCustomInput(e.target.value)}
                            onKeyDown={e => e.key === 'Enter' && applyCustom()}
                            style={{
                                flex: 1,
                                height: 38,
                                border: '1.5px solid rgba(0,0,0,0.12)',
                                borderRadius: 8,
                                padding: '0 12px',
                                fontFamily: 'var(--font-sans), sans-serif',
                                fontSize: 13,
                                color: '#1A1A1A',
                                background: 'rgba(255,255,255,0.8)',
                                outline: 'none',
                            }}
                        />
                        <button
                            onClick={applyCustom}
                            style={{
                                height: 38,
                                padding: '0 16px',
                                background: '#B07A4A',
                                color: '#fff',
                                border: 'none',
                                borderRadius: 8,
                                fontFamily: 'var(--font-sans), sans-serif',
                                fontSize: 12,
                                fontWeight: 600,
                                cursor: 'pointer',
                            }}
                        >
                            Set
                        </button>
                    </div>
                )}
            </div>

            {/* Completion message */}
            {isFinished && (
                <div style={{
                    background: 'rgba(74,103,65,0.08)',
                    border: '1px solid rgba(74,103,65,0.2)',
                    borderRadius: 10,
                    padding: '10px 16px',
                    textAlign: 'center',
                    width: '100%',
                }}>
                    <p style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: '#4A6741', margin: 0, fontWeight: 600 }}>
                        Session complete — well done!
                    </p>
                    <p style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: '#888', margin: '4px 0 0' }}>
                        Take a short break before the next round.
                    </p>
                </div>
            )}
        </div>
    );
}
