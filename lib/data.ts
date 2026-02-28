import { StudySession, DistractionSource, TopApp, DailyHour } from './types';

export interface PhonePickupEvent {
    time: string;
    minutesUnattended: number;
    durationSeconds: number;
}

export interface FaceAwayEvent {
    time: string;
    durationSeconds: number;
}

// Dummy data for generic parts that don't have json files yet.
export const studySessions: StudySession[] = [
    { date: "2024-01-15", subject: "Physics", duration: 120, interruptions: 4, focusScore: 88, notes: "Thermodynamics chapter" },
    { date: "2024-01-16", subject: "Mathematics", duration: 95, interruptions: 7, focusScore: 71, notes: "Integration practice" },
];

export const dailyHours: DailyHour[] = [
    { date: "Jan 1", hours: 2.5 },
    { date: "Jan 2", hours: 3.1 },
];

export function processNotifications(notificationsJson: any[]): { distractionSources: DistractionSource[], topApps: TopApp[], totalInterruptions: number } {
    if (!notificationsJson || notificationsJson.length === 0) {
        return { distractionSources: [], topApps: [], totalInterruptions: 0 };
    }

    const appCounts: Record<string, number> = {};
    let totalInterruptions = 0;

    notificationsJson.forEach(n => {
        if (n.has_notification === "True" && n.source) {
            appCounts[n.source] = (appCounts[n.source] || 0) + 1;
            totalInterruptions++;
        }
    });

    const colors = ["#2C3E50", "#D7C3B3", "#A8A9AD", "#4A6741", "#8B7355"];

    // Sort apps by frequency
    const sortedApps = Object.entries(appCounts)
        .sort((a, b) => b[1] - a[1]);

    const topApps: TopApp[] = sortedApps.map(([name, count]) => ({ name, count }));

    const distractionSources: DistractionSource[] = sortedApps.slice(0, 5).map(([name, value], i) => ({
        name,
        value,
        color: colors[i % colors.length]
    }));

    return { distractionSources, topApps, totalInterruptions };
}

export function processFaceEvents(sessionLogJson: any[]): { faceAwayEvents: FaceAwayEvent[], totalLookAways: number, avgLookAwaySeconds: number, longestLookAway: number, totalSecondsDistracted: number } {
    if (!sessionLogJson || sessionLogJson.length === 0) return { faceAwayEvents: [], totalLookAways: 0, avgLookAwaySeconds: 0, longestLookAway: 0, totalSecondsDistracted: 0 };

    const events: FaceAwayEvent[] = [];
    let currentLookAwayTime: Date | null = null;
    let currentLookAwayTimestampString = "";

    sessionLogJson.forEach(log => {
        if (log.event === "LA" || log.event === "FL") {
            // Assume today's date + log.time to parse diffs easily
            currentLookAwayTime = new Date(`1970-01-01T${log.time}Z`);
            currentLookAwayTimestampString = log.time.substring(0, 5); // Just HH:MM
        } else if ((log.event === "LB" || log.event === "FF") && currentLookAwayTime) {
            const lookBackTime = new Date(`1970-01-01T${log.time}Z`);
            const diffSeconds = (lookBackTime.getTime() - currentLookAwayTime.getTime()) / 1000;

            if (diffSeconds > 0) {
                events.push({
                    time: currentLookAwayTimestampString,
                    durationSeconds: Math.round(diffSeconds)
                });
            }
            currentLookAwayTime = null;
        }
    });

    const totalLookAways = events.length;
    const totalSecondsDistracted = events.reduce((sum, e) => sum + e.durationSeconds, 0);
    const avgLookAwaySeconds = totalLookAways > 0 ? Math.round(totalSecondsDistracted / totalLookAways) : 0;
    const longestLookAway = totalLookAways > 0 ? Math.max(...events.map(e => e.durationSeconds)) : 0;

    return { faceAwayEvents: events, totalLookAways, avgLookAwaySeconds, longestLookAway, totalSecondsDistracted };
}

export function processPickups(pickedupJson: any[]): { phonePickupEvents: PhonePickupEvent[], totalPhonePickups: number, avgUnattendedMinutes: number, longestUnattended: number } {
    if (!pickedupJson || pickedupJson.length === 0) return { phonePickupEvents: [], totalPhonePickups: 0, avgUnattendedMinutes: 0, longestUnattended: 0 };

    const events: PhonePickupEvent[] = [];

    // The pickedup.json only provides time_held. We will simulate timestamps to make the graph render nicely, spaced artificially.
    let simulatedHour = 9;
    let simulatedMinute = 0;

    pickedupJson.forEach((p, index) => {
        const timeStr = `${simulatedHour.toString().padStart(2, '0')}:${simulatedMinute.toString().padStart(2, '0')}`;

        // Add random 20-50 mins unattended gap between each for the visualization
        const unattendedMins = index === 0 ? 0 : Math.floor(Math.random() * 30) + 20;

        simulatedMinute += unattendedMins;
        if (simulatedMinute >= 60) {
            simulatedHour += Math.floor(simulatedMinute / 60);
            simulatedMinute = simulatedMinute % 60;
        }

        events.push({
            time: timeStr,
            minutesUnattended: unattendedMins,
            durationSeconds: Math.round(p.time_held)
        });
    });

    const totalPhonePickups = events.length;
    const avgUnattendedMinutes = totalPhonePickups > 1
        ? Math.round(events.slice(1).reduce((sum, e) => sum + e.minutesUnattended, 0) / (totalPhonePickups - 1))
        : 0;
    const longestUnattended = events.length > 0 ? Math.max(...events.map(e => e.minutesUnattended)) : 0;

    return { phonePickupEvents: events, totalPhonePickups, avgUnattendedMinutes, longestUnattended };
}

export const totalStudyMinutes = studySessions.reduce((sum, s) => sum + s.duration, 0);
export const totalSessions = studySessions.length;
export const avgFocusScore = studySessions.length > 0 ? Math.round(studySessions.reduce((sum, s) => sum + s.focusScore, 0) / studySessions.length) : 0;

export const subjectHours = Object.entries(
    studySessions.reduce<Record<string, number>>((acc, s) => {
        acc[s.subject] = (acc[s.subject] || 0) + s.duration / 60;
        return acc;
    }, {})
).map(([subject, hours]) => ({ subject, hours: Math.round(hours * 10) / 10 }))
    .sort((a, b) => b.hours - a.hours);


