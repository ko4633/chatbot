import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OMNIS — Today's Intelligence",
  description: "Personal Intelligence OS — Phase 1",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="app-header">
          <h1>
            <a href="/">OMNIS</a>
          </h1>
          <span style={{ fontSize: 12, color: "var(--text-dim)" }}>
            Japan → Korea Product Opportunity Discovery
          </span>
        </header>
        {children}
      </body>
    </html>
  );
}
