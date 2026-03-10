import type { Metadata } from "next";
import { Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const mono = Geist_Mono({ variable: "--font-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "FAB-SENTINEL",
  description: "반도체 공정 AI 이상감지 시스템",
};

const NAV = [
  { href: "/", label: "대시보드" },
  { href: "/bus", label: "토픽 버스" },
  { href: "/anomalies", label: "이상 목록" },
  { href: "/rules", label: "규칙 관리" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className={`${mono.variable} font-mono bg-gray-950 text-gray-100 min-h-screen`}>
        <nav className="border-b border-gray-800 bg-gray-900/80 backdrop-blur sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 flex items-center h-14 gap-8">
            <Link href="/" className="text-lg font-bold text-emerald-400 tracking-tight">
              FAB-SENTINEL
            </Link>
            <div className="flex gap-1">
              {NAV.map((n) => (
                <Link
                  key={n.href}
                  href={n.href}
                  className="px-3 py-1.5 rounded text-sm text-gray-400 hover:text-white hover:bg-gray-800 transition"
                >
                  {n.label}
                </Link>
              ))}
            </div>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
