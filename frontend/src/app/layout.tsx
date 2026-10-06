import type { Metadata } from "next";
import "./globals.css";
import { ClerkProvider } from "@clerk/nextjs";
import { dark } from "@clerk/themes";
import { AppShell } from "@/components/navigation/AppShell";
import { Providers } from "@/components/Providers";

export const metadata: Metadata = {
  title: "ContentSignal — Turn Search Data into Smarter Content Decisions",
  description: "ML-powered Content Intelligence SaaS platform that analyzes webpage search, traffic, and engagement signals to prioritize editorial reviews.",
  icons: {
    icon: [
      { url: "/icon.svg", type: "image/svg+xml" },
      { url: "/favicon.ico", sizes: "32x32" },
    ],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider
      publishableKey={process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY}
      appearance={{
        baseTheme: dark,
        variables: {
          colorPrimary: "#0d9488",
          colorBackground: "#0b1220",
          colorInputBackground: "#070b14",
          colorInputText: "#f8fafc",
          colorText: "#f8fafc",
          colorTextSecondary: "#94a3b8",
        },
      }}
    >
      <html lang="en" className="dark">
        <body className="min-h-screen bg-slate-50 dark:bg-[#070b14] text-slate-900 dark:text-slate-100 transition-colors duration-200">
          <Providers>
            <AppShell>
              {children}
            </AppShell>
          </Providers>
        </body>
      </html>
    </ClerkProvider>
  );
}
