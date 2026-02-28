/**
 * exportPdf.ts
 * Generates and downloads a styled Focus Report PDF using jsPDF.
 * Import and call exportFocusReportPdf() from a client component.
 */

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
    distractionSources,
    phonePickupEvents,
    faceAwayEvents,
    studySessions,
} from './data';

export async function exportFocusReportPdf() {
    // Dynamically import jsPDF so it only loads client-side
    const { jsPDF } = await import('jspdf');

    const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
    const PAGE_W = 210;
    const PAGE_H = 297;
    const MARGIN = 20;
    const CONTENT_W = PAGE_W - MARGIN * 2;

    // ── Color palette ──
    const DARK_NAVY = [44, 62, 80] as [number, number, number];
    const AMBER = [176, 122, 74] as [number, number, number];
    const SAND = [215, 195, 179] as [number, number, number];
    const GREEN = [74, 103, 65] as [number, number, number];
    const RED = [192, 57, 43] as [number, number, number];
    const LIGHT_BG = [249, 248, 245] as [number, number, number];
    const GREY = [140, 140, 140] as [number, number, number];

    let y = MARGIN;

    // ── Helper functions ──
    function setFont(style: 'normal' | 'bold', size: number, color = [26, 26, 26] as [number, number, number]) {
        doc.setFont('helvetica', style);
        doc.setFontSize(size);
        doc.setTextColor(...color);
    }

    function drawRect(x: number, yPos: number, w: number, h: number, color: [number, number, number], radius = 0) {
        doc.setFillColor(...color);
        if (radius > 0) {
            doc.roundedRect(x, yPos, w, h, radius, radius, 'F');
        } else {
            doc.rect(x, yPos, w, h, 'F');
        }
    }

    function drawLine(x1: number, y1: number, x2: number, y2: number, color: [number, number, number], width = 0.3) {
        doc.setDrawColor(...color);
        doc.setLineWidth(width);
        doc.line(x1, y1, x2, y2);
    }

    function sectionTitle(title: string) {
        y += 6;
        drawRect(MARGIN, y, 3, 7, DARK_NAVY, 0);
        setFont('bold', 11, DARK_NAVY);
        doc.text(title, MARGIN + 6, y + 5.5);
        y += 13;
    }

    function kpiRow(items: { label: string; value: string; color: [number, number, number] }[]) {
        const colW = CONTENT_W / items.length;
        items.forEach((item, i) => {
            const cx = MARGIN + i * colW;
            drawRect(cx, y, colW - 4, 22, LIGHT_BG, 3);
            setFont('normal', 8, GREY);
            doc.text(item.label.toUpperCase(), cx + 5, y + 7);
            setFont('bold', 16, item.color);
            doc.text(item.value, cx + 5, y + 17);
        });
        y += 28;
    }

    function tableRow(cols: string[], widths: number[], isHeader = false, rowIndex = 0) {
        const rowH = 8;
        if (isHeader) {
            drawRect(MARGIN, y, CONTENT_W, rowH, DARK_NAVY, 0);
            setFont('bold', 8, [255, 255, 255]);
        } else {
            if (rowIndex % 2 === 0) drawRect(MARGIN, y, CONTENT_W, rowH, LIGHT_BG, 0);
            setFont('normal', 8, [50, 50, 50]);
        }
        let cx = MARGIN + 3;
        cols.forEach((col, i) => {
            doc.text(col, cx, y + 5.5, { maxWidth: widths[i] - 4 });
            cx += widths[i];
        });
        y += rowH;
    }

    function checkPageBreak(needed = 30) {
        if (y + needed > PAGE_H - MARGIN) {
            doc.addPage();
            y = MARGIN + 10;
        }
    }

    // ═══════════════════════════════════════════════
    // PAGE 1 — COVER
    // ═══════════════════════════════════════════════
    drawRect(0, 0, PAGE_W, PAGE_H, LIGHT_BG);
    drawRect(0, 0, PAGE_W, 80, [255, 255, 255]);
    drawRect(0, 0, PAGE_W, 4, DARK_NAVY);

    // Accent line
    drawRect(MARGIN, 16, 40, 1.5, SAND);

    // Brand
    setFont('bold', 9, DARK_NAVY);
    doc.text('AURELIUS', MARGIN, 28);
    setFont('normal', 8, GREY);
    doc.text('Focus Intelligence Platform', MARGIN, 34);

    // Date top-right
    setFont('normal', 8, GREY);
    const dateStr = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
    doc.text(dateStr, PAGE_W - MARGIN, 28, { align: 'right' });

    // Concentric circles decoration
    doc.setDrawColor(...SAND);
    doc.setLineWidth(0.4);
    for (const r of [28, 20, 12]) doc.circle(PAGE_W - 30, 18, r, 'S');

    // Main title
    setFont('bold', 32, [26, 26, 26]);
    doc.text('Your Focus', MARGIN, 60);
    setFont('bold', 32, AMBER);
    doc.text('Report.', MARGIN, 73);

    setFont('normal', 11, GREY);
    doc.text('A comprehensive analysis of your attention,', MARGIN, 88);
    doc.text('distractions, and productivity rhythms.', MARGIN, 95);

    // Divider
    drawLine(MARGIN, 104, PAGE_W - MARGIN, 104, SAND, 0.5);

    // Quick stats strip
    y = 112;
    kpiRow([
        { label: 'Study Time', value: `${Math.floor(totalStudyMinutes / 60)}h ${totalStudyMinutes % 60}m`, color: DARK_NAVY },
        { label: 'Sessions', value: String(totalSessions), color: AMBER },
        { label: 'Focus Score', value: `${avgFocusScore}/100`, color: GREEN },
        { label: 'Interruptions', value: String(totalInterruptions), color: RED },
    ]);

    // Large number accent
    drawLine(MARGIN, y + 4, PAGE_W - MARGIN, y + 4, SAND, 0.5);
    y += 14;

    // ── Phone Pickups Summary ──
    sectionTitle('Phone Activity Summary');
    kpiRow([
        { label: 'Total Pickups', value: String(totalPhonePickups), color: AMBER },
        { label: 'Avg Focus Window', value: `${avgUnattendedMinutes} min`, color: GREEN },
        { label: 'Best Phone-Free', value: `${longestUnattended} min`, color: DARK_NAVY },
    ]);

    // ── Face Detection Summary ──
    sectionTitle('Gaze & Focus Analysis');
    kpiRow([
        { label: 'Look-Aways', value: String(totalLookAways), color: DARK_NAVY },
        { label: 'Avg Duration', value: `${avgLookAwaySeconds}s`, color: AMBER },
        { label: 'Total Distracted', value: `${Math.floor(totalSecondsDistracted / 60)}m ${totalSecondsDistracted % 60}s`, color: RED },
    ]);

    // ── Interruption Breakdown ──
    sectionTitle('Interruption Source Breakdown');
    distractionSources.forEach((src, i) => {
        checkPageBreak(12);
        const pct = Math.round((src.value / totalInterruptions) * 100);
        const barW = (src.value / totalInterruptions) * (CONTENT_W - 50);
        setFont('normal', 9, [50, 50, 50]);
        doc.text(src.name, MARGIN, y + 4);
        drawRect(MARGIN + 50, y - 1, barW, 6, SAND, 2);
        setFont('bold', 9, DARK_NAVY);
        doc.text(`${src.value} (${pct}%)`, MARGIN + 50 + barW + 3, y + 4);
        y += 9;
    });
    y += 4;

    // ═══════════════════════════════════════════════
    // PAGE 2 — DETAIL TABLES
    // ═══════════════════════════════════════════════
    doc.addPage();
    y = MARGIN;
    drawRect(0, 0, PAGE_W, 4, DARK_NAVY);

    // Header
    setFont('bold', 9, DARK_NAVY);
    doc.text('AURELIUS', MARGIN, 14);
    setFont('normal', 8, GREY);
    doc.text('Focus Report — Detailed Data', MARGIN, 20);
    drawLine(MARGIN, 24, PAGE_W - MARGIN, 24, SAND, 0.5);
    y = 32;

    // ── Phone Pickup Events Table ──
    sectionTitle('Phone Pickup Events');
    const pickupColW = [30, 50, 70];
    tableRow(['Time', 'Duration (s)', 'Phone-Free Window Before'], pickupColW, true);
    phonePickupEvents.slice(0, 20).forEach((e: any, i: number) => {
        checkPageBreak(10);
        tableRow([e.time, `${e.durationSeconds}s`, e.minutesUnattended > 0 ? `${e.minutesUnattended} min` : '—'], pickupColW, false, i);
    });
    y += 6;

    // ── Look-Away Events Table ──
    checkPageBreak(40);
    sectionTitle('Look-Away Events');
    const faceColW = [30, 50, 50, 40];
    tableRow(['Time', 'Duration (s)', 'Severity', 'Category'], faceColW, true);
    faceAwayEvents.slice(0, 20).forEach((e: any, i: number) => {
        checkPageBreak(10);
        const sev = e.durationSeconds > 60 ? 'High' : e.durationSeconds > 20 ? 'Medium' : 'Low';
        tableRow([e.time, `${e.durationSeconds}s`, sev, 'Face away'], faceColW, false, i);
    });
    y += 6;

    // ── Session Log Table ──
    checkPageBreak(40);
    sectionTitle('Recent Study Sessions');
    const sessColW = [28, 30, 28, 28, 28, 28];
    tableRow(['Date', 'Subject', 'Duration', 'Focus %', 'Interruptions', 'Quality'], sessColW, true);
    studySessions.slice(0, 15).forEach((s: any, i: number) => {
        checkPageBreak(10);
        const dur = s.duration ? `${Math.floor(s.duration / 60)}h ${s.duration % 60}m` : '—';
        const qual = s.focusScore >= 90 ? 'Excellent' : s.focusScore >= 75 ? 'Good' : s.focusScore >= 60 ? 'Fair' : 'Poor';
        tableRow([
            s.date ?? '—',
            s.subject ?? '—',
            dur,
            s.focusScore ? `${s.focusScore}%` : '—',
            s.interruptions != null ? String(s.interruptions) : '—',
            qual,
        ], sessColW, false, i);
    });

    // ── Footer ──
    const totalPages = doc.getNumberOfPages();
    for (let p = 1; p <= totalPages; p++) {
        doc.setPage(p);
        setFont('normal', 7, GREY);
        doc.text(`Aurelius Focus Report  •  Generated ${new Date().toLocaleDateString()}  •  Page ${p} of ${totalPages}`, PAGE_W / 2, PAGE_H - 8, { align: 'center' });
        drawLine(MARGIN, PAGE_H - 12, PAGE_W - MARGIN, PAGE_H - 12, SAND, 0.3);
    }

    // ── Save ──
    const filename = `aurelius-focus-report-${new Date().toISOString().slice(0, 10)}.pdf`;
    doc.save(filename);
}
