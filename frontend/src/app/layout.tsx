import type { Metadata } from "next";
import "./globals.css";
import { ClerkProvider } from "@clerk/nextjs";
import { dark } from "@clerk/themes";
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
    <ClerkProvider
      publishableKey={process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || "pk_test_placeholder_for_build"}
      appearance={{
        baseTheme: dark,
        variables: {
          colorPrimary: "#0d9488",
          colorBackground: "#070b14",
          colorInputBackground: "#0b1220",
          colorInputText: "#f8fafc",
          colorText: "#f8fafc",
          colorTextSecondary: "#94a3b8",
        },
        elements: {
          card: "bg-[#0b1220] border border-slate-800 shadow-2xl rounded-2xl",
          headerTitle: "text-slate-100 font-bold",
          headerSubtitle: "text-slate-400 text-sm",
          formButtonPrimary: "bg-teal-600 hover:bg-teal-500 text-white font-semibold transition-all shadow-md shadow-teal-900/30",
          formFieldInput: "bg-[#070b14] border-slate-800 text-slate-100 focus:border-teal-500 focus:ring-teal-500/20",
          footerActionLink: "text-teal-400 hover:text-teal-300 font-medium",
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
