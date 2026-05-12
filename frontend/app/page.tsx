"use client";

import Link from "next/link";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export default function Home() {
  return (
    <>
      <Navbar />

      <main>
        {/* Hero Section */}
        <section className="relative min-h-screen flex items-center editorial-gradient gold-shimmer pt-20 overflow-hidden">
          <div className="max-w-7xl mx-auto px-8 w-full grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
            {/* Content Column */}
            <div className="lg:col-span-6 z-10">
              <h1 className="font-headline text-6xl md:text-8xl text-on-surface leading-[1.1] mb-8 tracking-tight">
                Dress like you <span className="italic">mean</span> it.
              </h1>
              <p className="font-body text-xl text-on-surface-variant mb-10 max-w-lg leading-relaxed">
                Upload your photos. Get your color palette, body type analysis, and 10 outfits picked just for you — in under 30 seconds.
              </p>
              <div className="flex flex-col sm:flex-row gap-6 items-start">
                <Link href="/upload" className="satin-button text-on-primary px-8 py-4 rounded-md font-label uppercase tracking-widest text-sm flex items-center gap-3 hover:opacity-90 transition-all">
                  Get My Style Profile
                  <span className="material-symbols-outlined text-sm">arrow_forward</span>
                </Link>
                <button
                  onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })}
                  className="group px-8 py-4 rounded-md font-label uppercase tracking-widest text-sm border border-primary text-primary hover:bg-primary/5 transition-all"
                >
                  See How It Works
                  <div className="h-[2px] w-0 group-hover:w-full bg-primary transition-all duration-300 mt-1"></div>
                </button>
              </div>
            </div>

            {/* Editorial Image Column */}
            <div className="lg:col-span-6 relative mt-12 lg:mt-0">
              <div className="relative w-full aspect-[4/5] overflow-hidden rounded-sm shadow-2xl translate-x-4 lg:translate-x-12 z-10 bg-surface-container-highest">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img className="w-full h-full object-cover" alt="High-end fashion editorial of a sophisticated model in a cream silk suit" src="https://lh3.googleusercontent.com/aida-public/AB6AXuB8_2D9qx5mcJ48WZbOSh3ZuZKO00b4FvMcPDKPFKYJubl14B8rp4KgjG-lsvK1DbkwusSNMfh255sS1bB3fGUYHZgjJmk9KB5oyUIGP6Dr3QBN2Y0lW18h16S0Afnw4PEUSebARahECaAZ4PeCqyEqGdN2dw_mPN5vhF3pbKgFpyDDoz-oXhVTazaFxkoHLDYtoTf9ahcKrXKzRzcA6px0KvU1vZO73Vhs9fnb8Iu3S11hCpJ88fyeS6IkvnU9WnkxYrOBwPqfi8k" />
              </div>
              <div className="absolute -top-12 -left-8 w-2/3 aspect-[3/4] overflow-hidden rounded-sm border-[12px] border-surface-container-low z-0 opacity-80 hidden md:block bg-surface-container-high">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img className="w-full h-full object-cover grayscale brightness-110" alt="Abstract fashion detail shot showing luxury fabric texture" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBWTsV51ncIfpTCkrIIs4xaink1KYm70Ubj_g2p97rHWBHcAqakoK42HbwGaG1mK02i7XconZLDB6aEv7r0Wor9d32C3ZKKOiotw9E_YUByM7dwFPeC3jN1Cu37QZWRY-h34lmosaQTAoalO7VQNKkcOPFPdkOT-0PtzT5ggJYpk-SWWG9P7S3rqaXSKdZ2d4Jn46rkpWnFNtQBrlMAzSMZE2nlx_mjc2I0sBE0Iz14_sJR38IJFPezuYuYHlDExmCoasWtNhjmUFo" />
              </div>

              {/* Aura Score Overlay */}
              <div className="absolute bottom-12 -left-12 bg-surface-container-lowest/90 backdrop-blur-xl p-6 rounded-xl shadow-lg z-20 hidden md:flex items-center gap-4 border border-outline-variant/20">
                <div className="relative w-16 h-16 flex items-center justify-center">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle className="text-surface-container-high" cx="32" cy="32" fill="transparent" r="28" stroke="currentColor" strokeWidth="4"></circle>
                    <circle className="text-primary" cx="32" cy="32" fill="transparent" r="28" stroke="currentColor" strokeDasharray="175" strokeDashoffset="40" strokeWidth="4"></circle>
                  </svg>
                  <span className="absolute font-label font-bold text-primary text-sm">94%</span>
                </div>
                <div>
                  <p className="font-label text-[10px] uppercase tracking-tighter text-on-surface-variant">Aura Match Score</p>
                  <p className="font-headline italic text-lg text-on-surface">Perfect Harmony</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Trust Strip */}
        <section className="py-10 bg-surface-container-low border-y border-outline-variant/10">
          <div className="max-w-7xl mx-auto px-8 flex flex-wrap justify-between items-center gap-8 opacity-70">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-primary text-sm">auto_awesome</span>
              <span className="font-label text-xs uppercase tracking-[0.2em] font-bold">Powered by Claude AI</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-primary text-sm">lock</span>
              <span className="font-label text-xs uppercase tracking-[0.2em] font-bold">Photos encrypted & private</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-primary text-sm">timer</span>
              <span className="font-label text-xs uppercase tracking-[0.2em] font-bold">Results in under 30 seconds</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-primary text-sm">auto_delete</span>
              <span className="font-label text-xs uppercase tracking-[0.2em] font-bold">Photos deleted after 30 days</span>
            </div>
          </div>
        </section>


        {/* How It Works */}
        <section id="how-it-works" className="py-32 bg-surface">
          <div className="max-w-7xl mx-auto px-8">
            <div className="mb-24 flex flex-col md:flex-row md:items-end justify-between gap-6">
              <div className="max-w-2xl">
                <span className="font-label text-primary uppercase tracking-widest text-xs mb-4 block">The Process</span>
                <h2 className="font-headline text-5xl text-on-surface">Elevate your presence <br />in three curated steps.</h2>
              </div>
              <div className="h-px flex-grow bg-outline-variant/30 mb-4 hidden lg:block mx-12"></div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-16">
              {/* Step 1 */}
              <div className="relative pt-12">
                <span className="font-headline text-8xl text-primary/10 absolute top-0 left-0 -z-0 pointer-events-none">01</span>
                <div className="relative z-10">
                  <h3 className="font-headline text-2xl mb-4 italic">The Digital Mirror</h3>
                  <p className="text-on-surface-variant leading-relaxed font-body">Upload 3 full-body photos. Our AI maps your unique proportions, skin undertones, and natural contrast levels.</p>
                  <div className="mt-8 h-[2px] w-12 bg-primary"></div>
                </div>
              </div>
              {/* Step 2 */}
              <div className="relative pt-12 md:mt-12">
                <span className="font-headline text-8xl text-primary/10 absolute top-0 left-0 -z-0 pointer-events-none">02</span>
                <div className="relative z-10">
                  <h3 className="font-headline text-2xl mb-4 italic">The Essence Analysis</h3>
                  <p className="text-on-surface-variant leading-relaxed font-body">We decode your &apos;Style Aura&apos;—blending Kibbe body typing with advanced color theory to find your perfect palette.</p>
                  <div className="mt-8 h-[2px] w-12 bg-primary"></div>
                </div>
              </div>
              {/* Step 3 */}
              <div className="relative pt-12 md:mt-24">
                <span className="font-headline text-8xl text-primary/10 absolute top-0 left-0 -z-0 pointer-events-none">03</span>
                <div className="relative z-10">
                  <h3 className="font-headline text-2xl mb-4 italic">The Curated Closet</h3>
                  <p className="text-on-surface-variant leading-relaxed font-body">Receive 10 fully styled outfits tailored to your body and palette, complete with links to similar pieces.</p>
                  <div className="mt-8 h-[2px] w-12 bg-primary"></div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Before/After Section */}
        <section className="py-32 bg-surface-container-low">
          <div className="max-w-7xl mx-auto px-8">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
              <div className="order-2 lg:order-1 flex flex-col sm:flex-row gap-6">
                <div className="flex-1 group">
                  <div className="relative aspect-[3/4] rounded-sm overflow-hidden mb-4 bg-surface-dim">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img className="w-full h-full object-cover filter grayscale opacity-80 group-hover:grayscale-0 transition-all duration-700" alt="Before AuraFit styling" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDPtlZ1utNm41xNrQT_lf_hPB7TiUgEi5SNcmgfON5Qcj99IRFnPTAgtWpK-7kbkI5oi3uDC1zbS-65TRzCRjcEUQ6hyrpfnb06Yf1eHfGbsRRxEjU_pQO5zF1DLsX_tEwSXgiK4l7C1LzaEVPbbQRKvO5kMiMevZs2h9H62aaeepaA8ZeFH1YeYYthWcnkeioe6hKycYare6OigXqJPoU1-qgTpRsw7p0fa0okiBoSKMEAwg0HMvW0hZXqPGtKouqfHO7TDMM7q2g" />
                    <div className="absolute top-4 left-4 bg-on-surface text-surface text-[10px] font-label uppercase tracking-widest px-3 py-1">Before AuraFit</div>
                  </div>
                </div>
                <div className="flex-1 group mt-12 sm:mt-24">
                  <div className="relative aspect-[3/4] rounded-sm overflow-hidden mb-4 shadow-xl ring-1 ring-primary/20 bg-surface-container-lowest">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img className="w-full h-full object-cover" alt="After AuraFit styling" src="https://lh3.googleusercontent.com/aida-public/AB6AXuB34I7bEBNiVTgBVYm9Kbuu3pnJus2_vF9AjoRlf245XewZ0FlvVSsxELgVOF8wFhnlmh0AVHbSctweGTJ-9BO3qs74xoECjsBqrrN_98X2KjqXyMiiESBYEcgvuPrceXew24peJkXJyqZHWfsFjxkCdHxX-gQ86vzx6zDqzR6Z6GobQJMGVEKfD3ZPoNHhDEaGjUr7H4rlg7AT7QKwMh7g5qR5CjCZXqCaZz7TB5u9eig89LeC8CidjUzNmqFYfSQEHZ_57kN1J5Q" />
                    <div className="absolute top-4 left-4 bg-primary text-on-primary text-[10px] font-label uppercase tracking-widest px-3 py-1">After AuraFit</div>
                  </div>
                </div>
              </div>
              <div className="order-1 lg:order-2 pl-0 lg:pl-16">
                <h2 className="font-headline text-5xl mb-8 leading-tight">The power of <br /><span className="italic">intentional</span> dressing.</h2>
                <p className="text-lg text-on-surface-variant font-body mb-8 leading-relaxed">
                  Most people wear only 20% of their wardrobe. We help you find the 100% that makes you feel like the most authentic version of yourself.
                </p>
                <blockquote className="border-l-2 border-primary pl-6 py-2 italic font-headline text-xl text-on-surface/80">
                  &ldquo;I finally understand why certain clothes never felt right. AuraFit gave me a blueprint for my own beauty.&rdquo;
                  <footer className="mt-4 font-label text-xs uppercase tracking-widest not-italic">— Elena V., Paris</footer>
                </blockquote>
              </div>
            </div>
          </div>
        </section>

        {/* Final CTA Section */}
        <section className="py-40 relative">
          <div className="absolute inset-0 z-0">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img className="w-full h-full object-cover opacity-20 filter blur-sm" alt="Fashion atelier background" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAzXnt8ohxfGalBIyXRKRC3momUkp-Oc-7dSVxkFGew1XXB6yQEMnHTaJVIskapWEtsgkygRd2c2GIPRZoAl769lNxMV1T3jVp214uN-KB7-9ABi6dc08iCJst-Qzpn_ZOUYwBo8uvd9VoelrpinGy-6lZhjUup9hp2m026B05LfbBkqdgfW24xltbwCY8cbAg6OTbVzkOhm431fBRMS_eNDrpiqzFlBCQugc__6xoBjlG6pxxejbXYPpDVpjNno5MKZiozt_Yn5kM" />
          </div>
          <div className="max-w-4xl mx-auto px-8 relative z-10 text-center">
            <h2 className="font-headline text-6xl mb-12">Your signature style <br />is waiting to be found.</h2>
            <Link href="/upload" className="satin-button text-on-primary px-12 py-5 rounded-md font-label uppercase tracking-widest text-lg shadow-2xl hover:scale-105 transition-transform inline-block">
              Start Your Analysis
            </Link>
          </div>
        </section>
      </main>

      <Footer />
    </>
  );
}
