import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MCP AI Research Assistant",
  description: "Tool-calling AI research assistant using MCP architecture"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
