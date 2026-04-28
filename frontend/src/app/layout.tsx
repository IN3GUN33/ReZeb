"use client";
import { Inter } from "next/font/google";
import { useEffect } from "react";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin", "cyrillic"] });

export default function RootLayout({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    }
  }, []);

  return (
    <html lang="ru" suppressHydrationWarning>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#2563eb" />
        <link rel="manifest" href="/manifest.json" />
        <title>ReZeb — AI-платформа строительного контроля</title>
      </head>
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
