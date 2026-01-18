import type { Metadata } from "next";
import { Bangers, Comic_Neue } from "next/font/google";
import "./comic.css";

const bangers = Bangers({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-bangers",
});

const comicNeue = Comic_Neue({
  weight: ["400", "700"],
  subsets: ["latin"],
  variable: "--font-comic",
});

export const metadata: Metadata = {
  title: "Comic Audio Generator",
  description: "Generate comics from your audiobook files",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${bangers.variable} ${comicNeue.variable} antialiased`}>
        {children}
      </body>
    </html>
  );
}
