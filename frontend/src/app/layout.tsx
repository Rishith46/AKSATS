import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ALL KNOWN SERVICES | ATS",
  description: "Internal applicant tracking system",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}