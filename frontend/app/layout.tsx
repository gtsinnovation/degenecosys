import type { Metadata } from 'next';
import { Web3Providers } from './providers';
import './globals.css'; // Your Tailwind CSS styles entrypoint

export const metadata: Metadata = {
  title: 'Degen Warrior Portal',
  description: 'Ecosystem governance matrix driven by $DD',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Web3Providers>
          {children}
        </Web3Providers>
      </body>
    </html>
  );
}