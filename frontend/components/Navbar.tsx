"use client";

import Link from "next/link";
import { useState } from "react";

interface NavbarProps {
  variant?: "light" | "dark";
}

export default function Navbar({ variant = "light" }: NavbarProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const textClass = variant === "dark" ? "text-surface-container-lowest" : "text-stone-600";
  const hoverClass = "hover:text-amber-600 transition-colors duration-300";
  const links = [
    { href: "/#process", label: "Process" },
    { href: "/#results", label: "Results" },
    { href: "/account", label: "My Profiles" },
  ];

  return (
    <nav className="fixed top-0 w-full z-50 border-b border-outline-variant/20 bg-surface/75 backdrop-blur-xl">
      <div className="flex justify-between items-center max-w-7xl mx-auto px-8 py-6">
        <Link href="/" className="text-2xl font-serif italic tracking-tight text-amber-600">
          AuraFit
        </Link>
        <div className="hidden md:flex items-center gap-12 font-serif italic">
          {links.map((link) => (
            <Link key={link.href} className={`${textClass} ${hoverClass}`} href={link.href}>
              {link.label}
            </Link>
          ))}
          <Link
            href="/upload"
            className="bg-primary text-on-primary px-6 py-2 rounded-lg font-label uppercase tracking-widest text-xs active:scale-95 duration-200 not-italic"
          >
            Get Started
          </Link>
        </div>
        <button
          aria-expanded={menuOpen}
          aria-label="Toggle navigation menu"
          className="md:hidden text-on-surface"
          onClick={() => setMenuOpen((current) => !current)}
        >
          <span className="material-symbols-outlined">menu</span>
        </button>
      </div>
      {menuOpen && (
        <div className="md:hidden mx-4 mb-4 rounded-2xl border border-outline-variant/30 bg-surface-container-lowest p-4 editorial-shadow">
          <div className="flex flex-col gap-3 font-label text-[11px] uppercase tracking-widest">
            {links.map((link) => (
              <Link key={link.href} className="rounded-xl px-4 py-3 text-on-surface-variant" href={link.href} onClick={() => setMenuOpen(false)}>
                {link.label}
              </Link>
            ))}
            <Link className="rounded-xl bg-primary px-4 py-3 text-on-primary" href="/upload" onClick={() => setMenuOpen(false)}>
              Get Started
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
}
