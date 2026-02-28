'use client';

import { useState, useEffect } from 'react';
import { Camera, Maximize, Play, CheckCircle2, Loader2, X } from 'lucide-react';

type Step = 'idle' | 'camera_select' | 'config' | 'ready' | 'active';

export default function SessionSetupModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
    const [step, setStep] = useState<Step>('idle');
    const [error, setError] = useState<string | null>(null);

    // Call backend to start a script
    const startScript = async (script: string) => {
        try {
            const res = await fetch(`http://localhost:8000/start/${script}`, { method: 'POST' });
            if (!res.ok) throw new Error(`Failed to start ${script}`);
        } catch (err: any) {
            setError(err.message);
        }
    };

    // Poll backend for script status
    const pollStatus = async (script: string): Promise<boolean> => {
        try {
            const res = await fetch(`http://localhost:8000/status/${script}`);
            if (!res.ok) return false;
            const data = await res.json();
            return data.status === 'completed';
        } catch {
            return false;
        }
    };

    // Start flow
    useEffect(() => {
        if (!isOpen) {
            setStep('idle');
            setError(null);
            return;
        }
        if (isOpen && step === 'idle') {
            setStep('camera_select');
            startScript('camera_select');
        }
    }, [isOpen]);

    // Polling logic for camera_select
    useEffect(() => {
        if (step !== 'camera_select') return;
        const interval = setInterval(async () => {
            const done = await pollStatus('camera_select');
            if (done) {
                setStep('config');
                startScript('configlandmarks');
            }
        }, 1000);
        return () => clearInterval(interval);
    }, [step]);

    // Polling logic for configlandmarks
    useEffect(() => {
        if (step !== 'config') return;
        const interval = setInterval(async () => {
            const done = await pollStatus('configlandmarks');
            if (done) setStep('ready');
        }, 1000);
        return () => clearInterval(interval);
    }, [step]);

    // Start actual tracking
    const handleStartTracking = async () => {
        await startScript('study_tracker');
        await startScript('noti_watcher');
        setStep('active');
        setTimeout(() => {
            onClose();
        }, 800);
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ background: 'rgba(26,26,26,0.4)', backdropFilter: 'blur(8px)' }}>
            <div
                className="relative w-full max-w-md bg-white rounded-2xl shadow-2xl overflow-hidden animate-fade-up"
                style={{ border: '1px solid rgba(215,195,179,0.5)' }}
            >
                {/* Header */}
                <div className="flex justify-between items-center p-6 border-b border-gray-100 bg-gray-50/50">
                    <div>
                        <h3 style={{ fontFamily: 'var(--font-serif), serif', fontSize: 24, color: '#1A1A1A', lineHeight: 1 }}>
                            Session Launch
                        </h3>
                        <p style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: '#888', marginTop: 4 }}>
                            Preparing Aurelius tracking environment
                        </p>
                    </div>
                    {step !== 'active' && (
                        <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
                            <X className="w-5 h-5 text-gray-400" />
                        </button>
                    )}
                </div>

                {/* Body */}
                <div className="p-8">
                    {error ? (
                        <div className="p-4 bg-red-50 text-red-600 rounded-xl text-sm border border-red-100">
                            <strong>Error:</strong> {error}
                        </div>
                    ) : (
                        <div className="space-y-8">

                            {/* Step 1: Camera */}
                            <div className={`flex items-start gap-4 transition-opacity duration-300 ${step === 'camera_select' ? 'opacity-100' : 'opacity-40'}`}>
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 transition-colors ${step === 'camera_select' ? 'bg-[#D7C3B3] text-white' : step === 'config' || step === 'ready' || step === 'active' ? 'bg-[#4A6741] text-white' : 'bg-gray-100 text-gray-400'}`}>
                                    {step === 'config' || step === 'ready' || step === 'active' ? <CheckCircle2 className="w-5 h-5" /> : <Camera className="w-5 h-5" />}
                                </div>
                                <div>
                                    <h4 style={{ fontFamily: 'var(--font-sans)', fontSize: 15, fontWeight: 600, color: '#1A1A1A' }}>Hardware Selection</h4>
                                    <p style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: '#666', marginTop: 2 }}>Please select your active camera from the popup window.</p>
                                    {step === 'camera_select' && <div className="mt-3 flex items-center gap-2 text-[#B07A4A] text-sm"><Loader2 className="w-4 h-4 animate-spin" /> Waiting for selection...</div>}
                                </div>
                            </div>

                            {/* Step 2: Calibration */}
                            <div className={`flex items-start gap-4 transition-opacity duration-300 ${step === 'config' ? 'opacity-100' : (step === 'ready' || step === 'active' ? 'opacity-40' : 'opacity-30')}`}>
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 transition-colors ${step === 'config' ? 'bg-[#D7C3B3] text-white' : step === 'ready' || step === 'active' ? 'bg-[#4A6741] text-white' : 'bg-gray-100 text-gray-400'}`}>
                                    {step === 'ready' || step === 'active' ? <CheckCircle2 className="w-5 h-5" /> : <Maximize className="w-5 h-5" />}
                                </div>
                                <div>
                                    <h4 style={{ fontFamily: 'var(--font-sans)', fontSize: 15, fontWeight: 600, color: '#1A1A1A' }}>Facial Calibration</h4>
                                    <p style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: '#666', marginTop: 2 }}>Align your face and adjust landmark boundaries.</p>
                                    {step === 'config' && <div className="mt-3 flex items-center gap-2 text-[#B07A4A] text-sm"><Loader2 className="w-4 h-4 animate-spin" /> Calibrating...</div>}
                                </div>
                            </div>

                            {/* Step 3: Ready */}
                            <div className={`flex items-start gap-4 transition-opacity duration-300 ${step === 'ready' || step === 'active' ? 'opacity-100' : 'opacity-30'}`}>
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 transition-colors ${step === 'active' ? 'bg-[#4A6741] text-white' : step === 'ready' ? 'bg-[#D7C3B3] text-white' : 'bg-gray-100 text-gray-400'}`}>
                                    {step === 'active' ? <CheckCircle2 className="w-5 h-5" /> : <Play className="w-5 h-5" />}
                                </div>
                                <div>
                                    <h4 style={{ fontFamily: 'var(--font-sans)', fontSize: 15, fontWeight: 600, color: '#1A1A1A' }}>Ready to Begin</h4>
                                    <p style={{ fontFamily: 'var(--font-sans)', fontSize: 13, color: '#666', marginTop: 2 }}>Environment is secured. Start when you are ready to focus.</p>

                                    {step === 'ready' && (
                                        <button
                                            onClick={handleStartTracking}
                                            className="mt-6 w-full py-3 px-4 rounded-xl text-white font-semibold transition-transform hover:scale-[1.02] active:scale-[0.98]"
                                            style={{ background: 'linear-gradient(135deg, #1A1A1A, #2C3E50)', boxShadow: '0 4px 14px rgba(44,62,80,0.2)' }}
                                        >
                                            Start Study Session
                                        </button>
                                    )}
                                    {step === 'active' && (
                                        <div className="mt-4 flex items-center gap-2 text-[#4A6741] text-sm font-semibold">
                                            <div style={{ position: 'relative', width: 6, height: 6 }}>
                                                <div style={{ position: 'absolute', inset: -4, borderRadius: '50%', background: 'rgba(74,103,65,0.2)', animation: 'pulseRing 2s ease-in-out infinite' }} />
                                                <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#4A6741' }} />
                                            </div>
                                            Session Active
                                        </div>
                                    )}
                                </div>
                            </div>

                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
