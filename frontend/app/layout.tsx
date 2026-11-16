import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "私人智囊",
  description: "Private Advisor MVP"
};

export default function RootLayout({
  children
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
