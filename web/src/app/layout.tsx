import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { HydrationMarker } from "@/components/HydrationMarker";

// Humanist sans, per docs/design/coffee-counter-chat-ui-design.md Section 6.
const humanistSans = Inter({
  variable: "--font-humanist-sans",
  subsets: ["latin"],
});

// tabular-nums-friendly monospace for aliases, costs, latency.
const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Coffee Counter",
  description: "Project Coffee chat UI - a pure consumer of the Coffee Core Router event stream.",
};

// viewport-fit=cover is required for the env(safe-area-inset-*) values the
// composer/header use to clear the iPhone home indicator/notch.
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${humanistSans.variable} ${jetbrainsMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col overflow-x-hidden bg-cream text-espresso">
        <HydrationMarker />
        {children}
      </body>
    </html>
  );
}
