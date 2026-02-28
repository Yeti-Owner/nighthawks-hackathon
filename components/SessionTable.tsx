import { studySessions } from '../lib/data';

function getScorePillClass(score: number) {
    if (score >= 80) return 'score-green';
    if (score >= 60) return 'score-amber';
    return 'score-red';
}

function formatDate(dateStr: string) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
}

export default function SessionTable() {
    return (
        <div className="w-full">
            <div className="overflow-x-auto">
                <table className="w-full text-left" style={{ borderCollapse: 'collapse' }}>
                    <thead>
                        <tr>
                            {['SESSION DATE', 'SUBJECT', 'DURATION', 'INTERRUPTIONS', 'FOCUS SCORE', 'NOTES'].map((col) => (
                                <th
                                    key={col}
                                    style={{
                                        fontFamily: 'var(--font-sans), sans-serif',
                                        fontSize: 11,
                                        fontWeight: 600,
                                        letterSpacing: '0.1em',
                                        color: '#A8A9AD',
                                        textTransform: 'uppercase',
                                        padding: '0 16px 16px 16px',
                                        borderBottom: '1px solid rgba(0, 0, 0, 0.05)',
                                    }}
                                >
                                    {col}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {// Limit to 8 rows as requested for sample display
                            studySessions.slice(0, 8).map((session, index) => (
                                <tr
                                    key={index}
                                    className="group transition-colors duration-200"
                                    style={{
                                        borderBottom: index === 7 ? 'none' : '1px solid rgba(0,0,0,0.05)',
                                    }}
                                >
                                    <td style={{ padding: '16px' }} className="group-hover:bg-[#f2f3f4]">
                                        <span className="text-[13px] text-[#666666] font-inter">
                                            {formatDate(session.date)}
                                        </span>
                                    </td>
                                    <td style={{ padding: '16px' }} className="group-hover:bg-[#f2f3f4]">
                                        <span className="text-[14px] text-[#1A1A1A] font-inter font-medium">
                                            {session.subject}
                                        </span>
                                    </td>
                                    <td style={{ padding: '16px' }} className="group-hover:bg-[#f2f3f4]">
                                        <span className="text-[14px] text-[#1A1A1A] font-inter">
                                            {Math.floor(session.duration / 60)}h {session.duration % 60}m
                                        </span>
                                    </td>
                                    <td style={{ padding: '16px' }} className="group-hover:bg-[#f2f3f4]">
                                        <span className="text-[14px] text-[#1A1A1A] font-inter">
                                            {session.interruptions}
                                        </span>
                                    </td>
                                    <td style={{ padding: '16px' }} className="group-hover:bg-[#f2f3f4]">
                                        <span className={`pill ${getScorePillClass(session.focusScore)}`}>
                                            {session.focusScore}
                                        </span>
                                    </td>
                                    <td style={{ padding: '16px' }} className="group-hover:bg-[#f2f3f4]">
                                        <span className="text-[13px] text-[#666666] font-inter max-w-[200px] truncate block hover:text-clip">
                                            {session.notes}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                    </tbody>
                </table>
            </div>

            <div className="flex justify-center mt-8">
                <button className="btn-ghost" style={{ padding: '0 24px', height: 40, fontSize: 11 }}>
                    View All Sessions
                </button>
            </div>
        </div>
    );
}
