import type { Metadata } from "next";

import "@fontsource-variable/fraunces";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/600.css";
import "@fontsource-variable/ibm-plex-sans";
import "./globals.css";

export const metadata: Metadata = {
  title: "Job Search Command Center",
  description: "A private local view of job applications, outcomes, and account access.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
