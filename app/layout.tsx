import { Instrument_Serif, Inter } from 'next/font/google';
import './globals.css';
import Navbar from '../components/Navbar';
import Auth0ProviderWrapper from '../components/Auth0ProviderWrapper';
import UserSync from '../components/UserSync';

const instrumentSerif = Instrument_Serif({
  weight: '400',
  subsets: ['latin'],
  variable: '--font-instrument-serif'
});

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  weight: ['400', '500', '600']
});

export const metadata = {
  title: 'Aurelius | Focus Intelligence Platform',
  description: 'Master your attention. Command your time.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${instrumentSerif.variable} ${inter.variable}`}>
      <body>
        <Auth0ProviderWrapper>
          <UserSync />
          <Navbar />
          {children}
        </Auth0ProviderWrapper>
      </body>
    </html>
  );
}
