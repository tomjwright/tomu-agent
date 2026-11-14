import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tomu",
  description: "A local agent that shows every step it takes",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
