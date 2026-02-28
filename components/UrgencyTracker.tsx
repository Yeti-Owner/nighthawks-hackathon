import { useStatsData } from '../lib/DataContext';
import LiquidCard from './LiquidCard';

export default function UrgencyTracker() {
    const { data } = useStatsData();
    if (!data) return null;

    const { totalHighUrgency = 0, totalLowUrgency = 0 } = data as any;
    const total = totalHighUrgency + totalLowUrgency || 1;
    const highPct = Math.round((totalHighUrgency / total) * 100) || 0;
    const lowPct = totalHighUrgency + totalLowUrgency === 0 ? 0 : 100 - highPct;

    return (
        <LiquidCard padding="p-8">
            <h3 className="micro-label mb-6">NOTIFICATION URGENCY</h3>

            <div className="flex gap-4 mb-6">
                <div className="flex-1 p-4 rounded-xl" style={{ background: 'rgba(192,57,43,0.05)', border: '1px solid rgba(192,57,43,0.1)' }}>
                    <p style={{ fontFamily: 'var(--font-sans)', fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', color: '#C0392B', marginBottom: 4 }}>HIGH PRIORITY</p>
                    <p style={{ fontFamily: 'var(--font-serif)', fontSize: 32, color: '#1A1A1A', margin: 0 }}>{totalHighUrgency}</p>
                </div>
                <div className="flex-1 p-4 rounded-xl" style={{ background: 'rgba(44,62,80,0.05)', border: '1px solid rgba(44,62,80,0.1)' }}>
                    <p style={{ fontFamily: 'var(--font-sans)', fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', color: '#2C3E50', marginBottom: 4 }}>LOW PRIORITY</p>
                    <p style={{ fontFamily: 'var(--font-serif)', fontSize: 32, color: '#1A1A1A', margin: 0 }}>{totalLowUrgency}</p>
                </div>
            </div>

            <div style={{ height: 8, borderRadius: 99, display: 'flex', overflow: 'hidden', background: 'rgba(0,0,0,0.05)' }}>
                <div style={{ width: `${highPct}%`, background: '#C0392B', transition: 'width 1s ease' }} />
                <div style={{ width: `${lowPct}%`, background: '#2C3E50', transition: 'width 1s ease' }} />
            </div>

            <div className="flex justify-between mt-3">
                <span style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: '#888' }}>{highPct}% High</span>
                <span style={{ fontFamily: 'var(--font-sans)', fontSize: 11, color: '#888' }}>{lowPct}% Low</span>
            </div>
        </LiquidCard>
    );
}
