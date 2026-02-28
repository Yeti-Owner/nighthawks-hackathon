import { StudySession, DistractionSource, TopApp, DailyHour } from './types';

export const studySessions: StudySession[] = [
    { date: "2024-01-15", subject: "Physics", duration: 120, interruptions: 4, focusScore: 88, notes: "Thermodynamics chapter" },
    { date: "2024-01-16", subject: "Mathematics", duration: 95, interruptions: 7, focusScore: 71, notes: "Integration practice" },
    { date: "2024-01-17", subject: "History", duration: 60, interruptions: 2, focusScore: 93, notes: "WW2 essay prep" },
    { date: "2024-01-18", subject: "Physics", duration: 145, interruptions: 9, focusScore: 65, notes: "Quantum mechanics intro" },
    { date: "2024-01-19", subject: "Literature", duration: 80, interruptions: 1, focusScore: 97, notes: "Hamlet analysis" },
    { date: "2024-01-20", subject: "Mathematics", duration: 110, interruptions: 5, focusScore: 82, notes: "Differential equations" },
    { date: "2024-01-21", subject: "Chemistry", duration: 75, interruptions: 3, focusScore: 90, notes: "Organic compounds" },
    { date: "2024-01-22", subject: "Physics", duration: 130, interruptions: 11, focusScore: 58, notes: "Electromagnetism" },
    { date: "2024-01-23", subject: "Literature", duration: 90, interruptions: 2, focusScore: 91, notes: "Poetry analysis" },
    { date: "2024-01-24", subject: "Chemistry", duration: 105, interruptions: 6, focusScore: 76, notes: "Chemical bonding" },
];

export const distractionSources: DistractionSource[] = [
    { name: "Messages", value: 78, color: "#2C3E50" },
    { name: "Social Media", value: 54, color: "#D7C3B3" },
    { name: "Email", value: 39, color: "#A8A9AD" },
    { name: "System Alerts", value: 28, color: "#4A6741" },
    { name: "Other", value: 14, color: "#8B7355" },
];

export const topApps: TopApp[] = [
    { name: "Instagram", count: 47 },
    { name: "iMessage", count: 38 },
    { name: "Slack", count: 29 },
    { name: "Gmail", count: 22 },
    { name: "Twitter / X", count: 17 },
    { name: "YouTube", count: 11 },
];

export const dailyHours: DailyHour[] = [
    { date: "Jan 1", hours: 2.5 },
    { date: "Jan 2", hours: 3.1 },
    { date: "Jan 3", hours: 1.8 },
    { date: "Jan 4", hours: 4.2 },
    { date: "Jan 5", hours: 3.5 },
    { date: "Jan 6", hours: 2.0 },
    { date: "Jan 7", hours: 0.5 },
    { date: "Jan 8", hours: 3.8 },
    { date: "Jan 9", hours: 2.9 },
    { date: "Jan 10", hours: 4.1 },
    { date: "Jan 11", hours: 3.3 },
    { date: "Jan 12", hours: 1.2 },
    { date: "Jan 13", hours: 2.7 },
    { date: "Jan 14", hours: 3.6 },
    { date: "Jan 15", hours: 4.5 },
    { date: "Jan 16", hours: 2.3 },
    { date: "Jan 17", hours: 1.5 },
    { date: "Jan 18", hours: 3.9 },
    { date: "Jan 19", hours: 2.8 },
    { date: "Jan 20", hours: 4.0 },
    { date: "Jan 21", hours: 1.9 },
    { date: "Jan 22", hours: 3.4 },
    { date: "Jan 23", hours: 2.6 },
    { date: "Jan 24", hours: 3.7 },
    { date: "Jan 25", hours: 4.3 },
    { date: "Jan 26", hours: 2.1 },
    { date: "Jan 27", hours: 1.0 },
    { date: "Jan 28", hours: 3.2 },
    { date: "Jan 29", hours: 2.4 },
    { date: "Jan 30", hours: 3.0 },
];

// Pre-computed aggregates for KPI cards
export const totalStudyMinutes = studySessions.reduce((sum, s) => sum + s.duration, 0);
export const totalSessions = studySessions.length;
export const avgFocusScore = Math.round(studySessions.reduce((sum, s) => sum + s.focusScore, 0) / studySessions.length);
export const totalInterruptions = distractionSources.reduce((sum, s) => sum + s.value, 0);

// Subject hours for bar chart
export const subjectHours = Object.entries(
    studySessions.reduce<Record<string, number>>((acc, s) => {
        acc[s.subject] = (acc[s.subject] || 0) + s.duration / 60;
        return acc;
    }, {})
).map(([subject, hours]) => ({ subject, hours: Math.round(hours * 10) / 10 }))
    .sort((a, b) => b.hours - a.hours);

// Phone Pickup Data
export interface PhonePickupEvent {
    time: string;       // e.g. "09:14"
    minutesUnattended: number; // how long phone was left alone before this pickup
    durationSeconds: number;   // how long this pickup lasted
}

export const phonePickupEvents: PhonePickupEvent[] = [
    { time: "08:05", minutesUnattended: 0, durationSeconds: 45 },
    { time: "08:52", minutesUnattended: 47, durationSeconds: 120 },
    { time: "09:31", minutesUnattended: 39, durationSeconds: 30 },
    { time: "10:14", minutesUnattended: 43, durationSeconds: 210 },
    { time: "10:58", minutesUnattended: 44, durationSeconds: 60 },
    { time: "11:43", minutesUnattended: 45, durationSeconds: 15 },
    { time: "12:22", minutesUnattended: 39, durationSeconds: 300 },
    { time: "13:05", minutesUnattended: 43, durationSeconds: 90 },
    { time: "13:47", minutesUnattended: 42, durationSeconds: 25 },
    { time: "14:30", minutesUnattended: 43, durationSeconds: 180 },
    { time: "15:10", minutesUnattended: 40, durationSeconds: 45 },
    { time: "15:55", minutesUnattended: 45, durationSeconds: 75 },
    { time: "16:38", minutesUnattended: 43, durationSeconds: 20 },
    { time: "17:20", minutesUnattended: 42, durationSeconds: 240 },
    { time: "18:05", minutesUnattended: 45, durationSeconds: 60 },
];

export const totalPhonePickups = phonePickupEvents.length;
export const avgUnattendedMinutes = Math.round(
    phonePickupEvents.slice(1).reduce((sum, e) => sum + e.minutesUnattended, 0) /
    (phonePickupEvents.length - 1)
);
export const longestUnattended = Math.max(...phonePickupEvents.map(e => e.minutesUnattended));

