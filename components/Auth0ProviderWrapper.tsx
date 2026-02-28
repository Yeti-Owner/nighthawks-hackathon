'use client';

import { Auth0Provider } from '@auth0/auth0-react';
import React, { useEffect, useState } from 'react';

export default function Auth0ProviderWrapper({ children }: { children: React.ReactNode }) {
    const [redirectUri, setRedirectUri] = useState<string>('');

    useEffect(() => {
        // Determine the current origin on the client
        setRedirectUri(window.location.origin);
    }, []);

    // Avoid rendering Auth0Provider with an empty redirectUri to prevent misconfiguration errors
    if (!redirectUri) {
        return <>{children}</>;
    }

    return (
        <Auth0Provider
            domain="dev-xtey287wxq2qgi04.us.auth0.com"
            clientId="FB6w2gSj3ARGsVBHGd3fByaTBdoUGQLn"
            authorizationParams={{
                redirect_uri: redirectUri,
            }}
        >
            {children}
        </Auth0Provider>
    );
}
