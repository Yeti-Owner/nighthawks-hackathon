import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function POST(request: Request) {
    try {
        const body = await request.json();

        if (!body.user_id) {
            return NextResponse.json({ error: 'Missing user_id' }, { status: 400 });
        }

        // Write the user ID to user.txt in the root of the project
        const filePath = path.join(process.cwd(), 'user.txt');
        fs.writeFileSync(filePath, `User ID: ${body.user_id}\nTimestamp: ${new Date().toISOString()}\n`, { flag: 'w' });

        return NextResponse.json({ success: true, user_id: body.user_id });
    } catch (error) {
        console.error('Error writing user.txt:', error);
        return NextResponse.json({ error: 'Failed to write user data' }, { status: 500 });
    }
}
