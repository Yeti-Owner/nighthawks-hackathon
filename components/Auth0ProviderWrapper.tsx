'use client';

import { Auth0Provider } from '@auth0/auth0-react';
import { ReactNode } from 'react';

export default function Auth0ProviderWrapper({ children }: { children: ReactNode }) {
    // In Server-Side Rendering (Next.js), `window` is not defined on the server.
    // We pass a valid URL when running on the client, and an empty string on the server.
    const redirectUri = typeof window !== 'undefined' ? window.location.origin : '';

    return (
        <Auth0Provider
            domain="dev-xtey287wxq2qgi04.us.auth0.com"
            clientId="uu4NXQB9XhxIKznkzZuR6wdYSNCEorGt"
            authorizationParams={{ redirect_uri: redirectUri }}
        >
            {children}
        </Auth0Provider>
    );
}
