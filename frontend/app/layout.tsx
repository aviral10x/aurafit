import type { Metadata } from "next";
import { Playfair_Display, Inter, Space_Grotesk, Noto_Serif } from "next/font/google";
import "./globals.css";

const playfair = Playfair_Display({
  variable: "--font-headline",
  subsets: ["latin"],
  display: "swap",
});

const inter = Inter({
  variable: "--font-body",
  subsets: ["latin"],
  display: "swap",
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-label",
  subsets: ["latin"],
  display: "swap",
});

const notoSerif = Noto_Serif({
  variable: "--font-noto-serif",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "AuraFit — AI Style Analysis & Personal Color Profile",
  description:
    "Upload 3 photos. Get your Fitzpatrick skin tone, color season, body type, and 10 personalized outfit recommendations — powered by Claude AI. Free to try.",
  metadataBase: new URL("https://aurafit.fun"),
  openGraph: {
    title: "AuraFit — AI Style Analysis & Personal Color Profile",
    description:
      "Upload 3 photos. Get your color season, body type, and 10 personalized outfits in under 30 seconds.",
    url: "https://aurafit.fun",
    siteName: "AuraFit",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "AuraFit — AI Style Analysis",
    description:
      "Get your color palette, body type analysis, and 10 outfits picked just for you — in under 30 seconds.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${playfair.variable} ${inter.variable} ${spaceGrotesk.variable} ${notoSerif.variable}`}>
      <head>
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
        />
      </head>
      <body className="bg-background text-on-surface font-body selection:bg-primary-fixed selection:text-on-primary-fixed antialiased">
        {children}
      </body>
    </html>
  );
}
