'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import type { StudySession, DistractionSource, TopApp, DailyHour } from './types';
import type { PhonePickupEvent, FaceAwayEvent } from './types'; // Wait I'll add these to lib/types.ts

export interface StatsData {
    studySessions: StudySession[];
    distractionSources: DistractionSource[];
    topApps: TopApp[];
    dailyHours: DailyHour[];
    totalStudyMinutes: number;
    totalSessions: number;
    avgFocusScore: number;
    totalInterruptions: number;
    subjectHours: Array<{ subject: string, hours: number }>;
    phonePickupEvents: PhonePickupEvent[];
    totalPhonePickups: number;
    avgUnattendedMinutes: number;
    longestUnattended: number;
    faceAwayEvents: FaceAwayEvent[];
    totalLookAways: number;
    avgLookAwaySeconds: number;
    longestLookAway: number;
    totalSecondsDistracted: number;
}

const StatsContext = createContext<{ data: StatsData | null; loading: boolean; error: string | null }>({
    data: null,
    loading: true,
    error: null
});

export function DataProvider({ children }: { children: React.ReactNode }) {
    const [data, setData] = useState<StatsData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function fetchStats() {
            try {
                const res = await fetch('/api/stats');
                if (!res.ok) throw new Error(`HTTP error ${res.status}`);
                const json = await res.json();
                if (json.error) throw new Error(json.error);
                setData(json);
            } catch (e: any) {
                setError(e.message);
            } finally {
                setLoading(false);
            }
        }
        fetchStats();
    }, []);

    return (
        <StatsContext.Provider value={{ data, loading, error }}>
            {children}
        </StatsContext.Provider>
    );
}

export function useStatsData() {
    const context = useContext(StatsContext);
    if (!context) {
        throw new Error('useStatsData must be used within a DataProvider');
    }
    return context;
}
