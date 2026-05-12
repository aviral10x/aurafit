import Link from "next/link";

export default function Footer() {
  return (
    <footer className="w-full border-t border-outline-variant/20 bg-surface-container-low">
      <div className="max-w-7xl mx-auto px-8 py-12">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-8">
          {/* Brand */}
          <div>
            <Link href="/" className="text-xl font-headline italic text-on-surface hover:text-primary transition-colors">
              AuraFit
            </Link>
            <p className="font-body text-xs text-on-surface-variant mt-2 max-w-xs">
              AI-powered personal style analysis. Your aura, curated.
            </p>
          </div>

          {/* Links */}
          <div className="flex flex-wrap gap-8">
            <Link className="font-label text-xs tracking-widest uppercase text-on-surface-variant hover:text-primary transition-colors" href="/privacy">Privacy</Link>
            <Link className="font-label text-xs tracking-widest uppercase text-on-surface-variant hover:text-primary transition-colors" href="/terms">Terms</Link>
            <Link className="font-label text-xs tracking-widest uppercase text-on-surface-variant hover:text-primary transition-colors" href="/contact">Contact</Link>
          </div>

          {/* Copyright */}
          <span className="font-label text-xs tracking-widest uppercase text-on-surface-variant">
            &copy; {new Date().getFullYear()} AuraFit
          </span>
        </div>

        {/* Bottom strip */}
        <div className="mt-8 pt-6 border-t border-outline-variant/20 flex flex-wrap gap-4 items-center justify-between">
          <p className="font-label text-[10px] tracking-wider text-on-surface-variant/60 uppercase">
            AI analysis by Claude · Images by OpenAI · Not medical advice
          </p>
          <Link href="/privacy" className="font-label text-[10px] tracking-wider text-on-surface-variant/60 uppercase hover:text-primary transition-colors">
            Photos auto-deleted after 30 days
          </Link>
        </div>
      </div>
    </footer>
  );
}

