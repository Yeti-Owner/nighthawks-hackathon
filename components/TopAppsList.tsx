import { topApps, distractionSources } from '../lib/data';
import LiquidCard from './LiquidCard';

export default function TopAppsList() {
    const maxCount = Math.max(...topApps.map(app => app.count));

    // Try to match app colors based on standard brand colors or fall back to luxury palette
    const getAppColor = (name: string) => {
        const n = name.toLowerCase();
        if (n.includes('instagram')) return '#D7C3B3'; // Rose gold
        if (n.includes('imessage')) return '#4A6741'; // Muted Green
        if (n.includes('slack')) return '#8B7355'; // Warm Wood
        if (n.includes('gmail')) return '#C62828'; // Muted Red
        if (n.includes('twitter') || n.includes('x')) return '#1A1A1A'; // Off black
        if (n.includes('youtube')) return '#C62828'; // Muted red
        return '#A8A9AD'; // Brushed Platinum
    };

    return (
        <LiquidCard padding="p-8">
            <div className="flex items-center justify-between mb-8">
                <h3 className="micro-label">TOP DISTRACTION SOURCES — THIS MONTH</h3>
            </div>

            <div className="flex flex-col gap-4">
                {topApps.map((app, index) => {
                    const widthPercent = (app.count / maxCount) * 100;
                    const color = getAppColor(app.name);

                    return (
                        <div key={app.name} className="relative flex items-center h-12">
                            {/* Background proportion bar */}
                            <div
                                className="absolute inset-y-0 left-0 rounded-r opacity-50"
                                style={{
                                    width: `${widthPercent}%`,
                                    background: 'rgba(44, 62, 80, 0.06)',
                                    pointerEvents: 'none',
                                    zIndex: 0
                                }}
                            />

                            {/* Content layer */}
                            <div className="relative z-10 flex items-center justify-between w-full px-4">
                                <div className="flex items-center gap-4">
                                    <div
                                        style={{
                                            width: 16,
                                            height: 16,
                                            backgroundColor: color,
                                            borderRadius: 4
                                        }}
                                    />
                                    <span
                                        style={{
                                            fontFamily: 'var(--font-sans), sans-serif',
                                            fontSize: 14,
                                            color: '#1A1A1A'
                                        }}
                                    >
                                        {app.name}
                                    </span>
                                </div>

                                <span
                                    style={{
                                        fontFamily: 'var(--font-sans), sans-serif',
                                        fontSize: 14,
                                        fontWeight: 600,
                                        color: '#2C3E50'
                                    }}
                                >
                                    {app.count}
                                </span>
                            </div>
                        </div>
                    );
                })}
            </div>
        </LiquidCard>
    );
}
