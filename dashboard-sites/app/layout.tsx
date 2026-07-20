import type { Metadata, Viewport } from "next";
import { headers } from "next/headers";
import "./globals.css";

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host = requestHeaders.get("x-forwarded-host") ?? requestHeaders.get("host") ?? "localhost:3000";
  const forwardedProtocol = requestHeaders.get("x-forwarded-proto");
  const protocol = forwardedProtocol === "http" || forwardedProtocol === "https"
    ? forwardedProtocol
    : host.startsWith("localhost") || host.startsWith("127.0.0.1") ? "http" : "https";
  const metadataBase = new URL(`${protocol}://${host}`);

  return {
    metadataBase,
    title: "Job Search Command Center",
    description:
      "A private, hosted-safe companion for reviewing job-application activity without uploading tracker or credential data.",
    openGraph: {
      type: "website",
      title: "Job Search Command Center",
      description: "Private job-search intelligence, without uploading your tracker.",
      images: [{ url: "/og.png", width: 1693, height: 929, alt: "Job Search Command Center" }],
    },
    twitter: {
      card: "summary_large_image",
      title: "Job Search Command Center",
      description: "Private job-search intelligence, without uploading your tracker.",
      images: ["/og.png"],
    },
  };
}

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#f2eee3",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
