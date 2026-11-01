import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Satya Agent – Celo",
  description: "AI content provenance on Celo",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
