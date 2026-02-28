'use client';

import { useEffect, useRef } from 'react';
import { useAuth0 } from '@auth0/auth0-react';

export default function UserSync() {
    const { user, isAuthenticated } = useAuth0();
    const hasSynced = useRef(false);

    useEffect(() => {
        // Only attempt to sync once per login to avoid spamming the backend
        if (isAuthenticated && user?.sub && !hasSynced.current) {
            hasSynced.current = true;

            fetch('http://localhost:8000/user', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ user_id: user.sub }),
            })
                .then(res => res.json())
                .then(data => console.log('Successfully synced Auth0 user ID:', data.user_id))
                .catch(err => {
                    hasSynced.current = false; // allow retry if failed
                    console.error('Failed to sync user ID:', err);
                });
        }
    }, [isAuthenticated, user]);

    return null; // This is a logic-only component that doesn't render anything
}
