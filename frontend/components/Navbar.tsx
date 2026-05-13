"use client";

import { useState } from "react";
import Link from "next/link";

interface NavbarProps {
  variant?: "light" | "dark";
}

const links = [
  { href: "/#how-it-works", label: "Process" },
  { href: "/#results", label: "Results" },
  { href: "/account", label: "My Profiles" },
];

export default function Navbar({ variant = "light" }: NavbarProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const textClass = variant === "dark" ? "text-surface-container-lowest" : "text-on-surface-variant";
  const hoverClass = "hover:text-primary transition-colors duration-300";

  return (
    <>
      <nav className="fixed top-0 w-full z-50 bg-surface/80 backdrop-blur-md border-b border-outline-variant/10">
        <div className="flex justify-between items-center max-w-7xl mx-auto px-8 py-6">
          <Link href="/" className="text-2xl font-headline italic tracking-tight text-primary">
            AuraFit
          </Link>
          <div className="hidden md:flex items-center gap-12 font-headline italic">
            {links.map((link) => (
              <Link key={link.href} className={`${textClass} ${hoverClass}`} href={link.href}>
                {link.label}
              </Link>
            ))}
            <Link
              href="/upload"
              className="bg-primary text-on-primary px-6 py-2 rounded-lg font-label uppercase tracking-widest text-xs active:scale-95 duration-200 not-italic hover:opacity-90 transition-opacity"
            >
              Get Started
            </Link>
          </div>
          <button
            className="md:hidden text-on-surface"
            onClick={() => setMobileOpen(true)}
            aria-label="Open navigation menu"
          >
            <span className="material-symbols-outlined">menu</span>
          </button>
        </div>
      </nav>

      {mobileOpen && (
        <div className="fixed inset-0 z-[100]">
          <div
            className="absolute inset-0 bg-on-surface/40 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          <div className="absolute right-0 top-0 h-full w-72 bg-surface-container-lowest shadow-2xl p-8 flex flex-col gap-8 animate-[slideIn_0.2s_ease-out]">
            <div className="flex justify-between items-center">
              <span className="font-headline italic text-xl text-primary">AuraFit</span>
              <button
                onClick={() => setMobileOpen(false)}
                aria-label="Close navigation menu"
                className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-surface-container-high transition-colors"
              >
                <span className="material-symbols-outlined text-on-surface">close</span>
              </button>
            </div>
            <div className="flex flex-col gap-6 font-headline italic text-lg">
              {links.map((link) => (
                <Link key={link.href} className={`${textClass} ${hoverClass}`} href={link.href} onClick={() => setMobileOpen(false)}>
                  {link.label}
                </Link>
              ))}
            </div>
            <Link
              href="/upload"
              onClick={() => setMobileOpen(false)}
              className="bg-primary text-on-primary px-6 py-3 rounded-lg font-label uppercase tracking-widest text-xs text-center not-italic hover:opacity-90 transition-opacity"
            >
              Get Started
            </Link>
          </div>
        </div>
      )}
    </>
  );
}
