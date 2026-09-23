import type { Metadata } from "next";
import "./globals.css";
import { AppShell } from "@/components/navigation/AppShell";
import { Providers } from "@/components/Providers";

export const metadata: Metadata = {
  title: "ContentSignal — Turn Search Data into Smarter Content Decisions",
  description: "ML-powered Content Intelligence SaaS platform that analyzes webpage search, traffic, and engagement signals to prioritize editorial reviews.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-50 dark:bg-[#070b14] text-slate-900 dark:text-slate-100 transition-colors duration-200">
        <Providers>
          <AppShell>
            {children}
          </AppShell>
        </Providers>
      </body>
    </html>
  );
}
