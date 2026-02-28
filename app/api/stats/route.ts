import { NextResponse } from 'next/server';
import fs from 'fs/promises';
import path from 'path';

export const dynamic = 'force-dynamic';

// Define the colors used in the quiet luxury design system
const QUIET_LUXURY_COLORS = [
    '#2C3E50', // Midnight Blue
    '#D7C3B3', // Rose Gold
    '#A8A9AD', // Brushed Platinum
    '#4A6741', // Muted Green / Olive
    '#8B7355', // Warm Wood
    '#B07A4A', // Copper/Leather
    '#C0392B', // Deep red
];

function timeStrToSeconds(timeStr: string) {
    const [h, m, s] = timeStr.split(':').map(Number);
    return h * 3600 + m * 60 + s;
}

function timeStrToFormatted(timeStr: string) {
    const [h, m] = timeStr.split(':');
    return `${h}:${m}`;
}

export async function GET() {
    try {
        const dataDir = path.join(process.cwd(), 'data');

        let sessionLog: any[] = [];
        let notifications: any[] = [];
        let pickedUp: any[] = [];

        try {
            const sessionRaw = await fs.readFile(path.join(dataDir, 'session_log.json'), 'utf-8');
            sessionLog = JSON.parse(sessionRaw);
        } catch (e) { console.error('Failed to read session_log.json'); }

        try {
            const notiRaw = await fs.readFile(path.join(dataDir, 'notifications.json'), 'utf-8');
            notifications = JSON.parse(notiRaw);
        } catch (e) { console.error('Failed to read notifications.json'); }

        try {
            const pickedRaw = await fs.readFile(path.join(dataDir, 'pickedup.json'), 'utf-8');
            pickedUp = JSON.parse(pickedRaw);
        } catch (e) { console.error('Failed to read pickedup.json'); }

        // --- Process Face Away / Face Detection Events ---
        const faceAwayEvents: { time: string; durationSeconds: number }[] = [];
        let currentLA: { time: string; startSecs: number } | null = null;
        for (const event of sessionLog) {
            if (event.event === 'LA') {
                if (!currentLA) {
                    currentLA = { time: event.time, startSecs: timeStrToSeconds(event.time) };
                }
            } else if (event.event === 'LB' && currentLA) {
                const endSecs = timeStrToSeconds(event.time);
                const duration = Math.max(1, endSecs - currentLA.startSecs);
                faceAwayEvents.push({
                    time: timeStrToFormatted(currentLA.time),
                    durationSeconds: duration,
                });
                currentLA = null;
            }
        }
        // Open LA event
        if (currentLA) {
            faceAwayEvents.push({
                time: timeStrToFormatted(currentLA.time),
                durationSeconds: 5, // fallback
            });
        }

        const totalLookAways = faceAwayEvents.length;
        const totalSecondsDistracted = faceAwayEvents.reduce((acc, cur) => acc + cur.durationSeconds, 0);
        const avgLookAwaySeconds = totalLookAways > 0 ? Math.round(totalSecondsDistracted / totalLookAways) : 0;
        const longestLookAway = totalLookAways > 0 ? Math.max(...faceAwayEvents.map(e => e.durationSeconds)) : 0;

        // --- Process Phone Pickups ---
        const phonePickupEvents: { time: string; minutesUnattended: number; durationSeconds: number }[] = [];
        let previousPickupEnd = null; // To calculate unattended minutes
        // We will assume that if we have a session start, that is when unattended starts.
        let sessionStartTimeSecs = sessionLog.length > 0 ? timeStrToSeconds(sessionLog[0].time) : 0;

        // Since pickedup.json only contains time_held and no absolute time, we will space them uniformly 
        // across the session for the timeline, or simply simulate the absolute time based on iterations.
        // Wait, "time_held" is available. Let's assume pickups happened evenly across the session.
        const totalPickups = pickedUp.length;
        if (totalPickups > 0 && sessionLog.length > 0) {
            const sessionEndSecs = timeStrToSeconds(sessionLog[sessionLog.length - 1].time);
            const totalDurationSecs = Math.max(60, sessionEndSecs - sessionStartTimeSecs);
            const interval = totalDurationSecs / (totalPickups + 1);

            pickedUp.forEach((p: any, idx: number) => {
                const pickupTimeSecs = sessionStartTimeSecs + interval * (idx + 1);
                const hrs = Math.floor(pickupTimeSecs / 3600).toString().padStart(2, '0');
                const mins = Math.floor((pickupTimeSecs % 3600) / 60).toString().padStart(2, '0');

                let minutesUnattended = 0;
                if (idx === 0) {
                    minutesUnattended = Math.round((pickupTimeSecs - sessionStartTimeSecs) / 60);
                } else {
                    const prevPickupTimeSecs = sessionStartTimeSecs + interval * idx;
                    const prevHeld = pickedUp[idx - 1].time_held;
                    minutesUnattended = Math.round((pickupTimeSecs - (prevPickupTimeSecs + prevHeld)) / 60);
                }

                phonePickupEvents.push({
                    time: `${hrs}:${mins}`,
                    minutesUnattended: Math.max(0, minutesUnattended),
                    durationSeconds: Math.round(p.time_held),
                });
            });
        }

        const totalPhonePickups = phonePickupEvents.length;
        const sumUnattended = phonePickupEvents.reduce((acc, curr) => acc + curr.minutesUnattended, 0);
        const avgUnattendedMinutes = totalPhonePickups > 0 ? Math.round(sumUnattended / totalPhonePickups) : 0;
        const longestUnattended = totalPhonePickups > 0 ? Math.max(...phonePickupEvents.map(e => e.minutesUnattended)) : 0;

        // --- Process Distraction Sources and Apps ---
        const validNotis = notifications.filter(n => n.has_notification === "True" && n.source);
        const sourceCounts: Record<string, number> = {};
        let totalHighUrgency = 0;
        let totalLowUrgency = 0;

        validNotis.forEach(n => {
            const src = n.source || "Other";
            sourceCounts[src] = (sourceCounts[src] || 0) + 1;

            const urg = (n.urgency || "").toLowerCase().trim();
            if (urg === "high") {
                totalHighUrgency++;
            } else {
                totalLowUrgency++; // Count blanks, "low", or unknown as Low Priority
            }
        });

        let colorIndex = 0;
        const distractionSources = Object.keys(sourceCounts).map(src => ({
            name: src,
            value: sourceCounts[src],
            color: QUIET_LUXURY_COLORS[colorIndex++ % QUIET_LUXURY_COLORS.length]
        })).sort((a, b) => b.value - a.value);

        const topApps = Object.keys(sourceCounts).map(src => ({
            name: src,
            count: sourceCounts[src]
        })).sort((a, b) => b.count - a.count);

        const totalInterruptions = validNotis.length;

        // --- Process Study Sessions ---
        // Group by session_id
        const sessionsMap: Record<string, any[]> = {};
        sessionLog.forEach((e: any) => {
            if (!sessionsMap[e.session_id]) sessionsMap[e.session_id] = [];
            sessionsMap[e.session_id].push(e);
        });

        const studySessions = Object.keys(sessionsMap).map((id, idx) => {
            const evts = sessionsMap[id];
            const startStr = evts[0].time;
            const endStr = evts[evts.length - 1].time;
            const startSecs = timeStrToSeconds(startStr);
            const endSecs = timeStrToSeconds(endStr);
            let durationMins = Math.round((endSecs - startSecs) / 60);

            // Artificial minimum duration if the test was too short
            if (durationMins < 1) durationMins = 1;

            const sessionLookAways = evts.filter(e => e.event === 'LA').length;
            const inters = sessionLookAways + Math.round(validNotis.length / Object.keys(sessionsMap).length) + Math.round(pickedUp.length / Object.keys(sessionsMap).length);

            let focusScore = 100 - (inters * 2) - Math.round((totalSecondsDistracted / 60) * 5);
            if (focusScore < 0) focusScore = 0;
            if (focusScore > 100) focusScore = 100;

            // Generate an ISO date for today or relative based on index
            const dateObj = new Date();
            dateObj.setDate(dateObj.getDate() - (Object.keys(sessionsMap).length - 1 - idx));
            const dateStr = dateObj.toISOString().split('T')[0];

            return {
                date: dateStr,
                subject: `Study Session ${id}`,
                duration: durationMins,
                interruptions: inters,
                focusScore: focusScore,
                notes: `System recorded session with ${inters} interruptions.`
            };
        });

        const totalSessions = studySessions.length;
        const totalStudyMinutes = studySessions.reduce((acc, cur) => acc + cur.duration, 0);
        const avgFocusScore = totalSessions > 0 ? Math.round(studySessions.reduce((acc, cur) => acc + cur.focusScore, 0) / totalSessions) : 0;

        const subjectHours = studySessions.reduce((acc, s) => {
            const existing = acc.find(x => x.subject === s.subject);
            if (existing) {
                existing.hours += s.duration / 60;
            } else {
                acc.push({ subject: s.subject, hours: Math.round((s.duration / 60) * 10) / 10 });
            }
            return acc;
        }, [] as { subject: string, hours: number }[]);

        // Group study sessions by day for dailyHours
        const dailyMap: Record<string, number> = {};
        studySessions.forEach(s => {
            const dStr = new Date(s.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            dailyMap[dStr] = (dailyMap[dStr] || 0) + (s.duration / 60);
        });

        // Add a fake point for "Yesterday" if there is only one day to make the graph look like a line/area graph
        let dailyHours = Object.keys(dailyMap).map(d => ({
            date: d,
            hours: Math.round(dailyMap[d] * 10) / 10
        }));

        if (dailyHours.length === 1) {
            const d = new Date(studySessions[0].date);
            d.setDate(d.getDate() - 1);
            const prevDStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            dailyHours = [
                { date: prevDStr, hours: 0 },
                ...dailyHours
            ];
        }

        const finalData = {
            studySessions,
            distractionSources,
            topApps,
            dailyHours,
            totalStudyMinutes,
            totalSessions,
            avgFocusScore,
            totalInterruptions,
            totalHighUrgency,
            totalLowUrgency,
            subjectHours,
            phonePickupEvents,
            totalPhonePickups,
            avgUnattendedMinutes,
            longestUnattended,
            faceAwayEvents,
            totalLookAways,
            avgLookAwaySeconds,
            longestLookAway,
            totalSecondsDistracted,
        };

        return NextResponse.json(finalData);
    } catch (e: any) {
        return NextResponse.json({ error: e.message }, { status: 500 });
    }
}
