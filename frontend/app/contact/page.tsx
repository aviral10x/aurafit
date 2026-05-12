import type { Metadata } from "next";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "Contact | AuraFit",
  description: "Get in touch with the AuraFit team.",
};

export default function ContactPage() {
  return (
    <>
      <Navbar />
      <main className="pt-32 pb-24 px-6 md:px-12 max-w-4xl mx-auto">
        <header className="mb-16">
          <span className="font-label text-[10px] tracking-[0.3em] uppercase text-primary mb-4 block">Get in touch</span>
          <h1 className="font-headline text-5xl mb-6">Contact Us</h1>
          <p className="font-body text-lg text-on-surface-variant max-w-xl leading-relaxed">
            Have a question, feedback, or a data request? We read every message.
          </p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Contact Cards */}
          <a
            href="mailto:hello@aurafit.fun"
            className="bg-surface-container-low rounded-xl p-8 editorial-shadow group hover:-translate-y-1 transition-transform"
          >
            <div className="w-14 h-14 rounded-full bg-primary-fixed flex items-center justify-center mb-6">
              <span className="material-symbols-outlined text-on-primary-fixed text-2xl">mail</span>
            </div>
            <h2 className="font-headline text-xl mb-2">General</h2>
            <p className="font-body text-sm text-on-surface-variant mb-4">Questions, feedback, partnerships.</p>
            <span className="font-label text-xs text-primary tracking-widest group-hover:underline underline-offset-4">
              hello@aurafit.fun
            </span>
          </a>

          <a
            href="mailto:privacy@aurafit.fun"
            className="bg-surface-container-low rounded-xl p-8 editorial-shadow group hover:-translate-y-1 transition-transform"
          >
            <div className="w-14 h-14 rounded-full bg-secondary-container flex items-center justify-center mb-6">
              <span className="material-symbols-outlined text-on-secondary-container text-2xl">shield</span>
            </div>
            <h2 className="font-headline text-xl mb-2">Privacy</h2>
            <p className="font-body text-sm text-on-surface-variant mb-4">Data requests, deletion, GDPR.</p>
            <span className="font-label text-xs text-primary tracking-widest group-hover:underline underline-offset-4">
              privacy@aurafit.fun
            </span>
          </a>

          <a
            href="mailto:support@aurafit.fun"
            className="bg-surface-container-low rounded-xl p-8 editorial-shadow group hover:-translate-y-1 transition-transform"
          >
            <div className="w-14 h-14 rounded-full bg-tertiary-container flex items-center justify-center mb-6">
              <span className="material-symbols-outlined text-on-tertiary-container text-2xl">support_agent</span>
            </div>
            <h2 className="font-headline text-xl mb-2">Support</h2>
            <p className="font-body text-sm text-on-surface-variant mb-4">Issues with analysis or your account.</p>
            <span className="font-label text-xs text-primary tracking-widest group-hover:underline underline-offset-4">
              support@aurafit.fun
            </span>
          </a>
        </div>

        <div className="mt-20 bg-surface-container-low rounded-xl p-10 editorial-shadow">
          <div className="flex gap-5 items-start">
            <div className="w-12 h-12 rounded-full bg-primary-fixed flex items-center justify-center shrink-0">
              <span className="material-symbols-outlined text-on-primary-fixed">schedule</span>
            </div>
            <div>
              <h3 className="font-headline text-xl mb-3">Response time</h3>
              <p className="font-body text-sm text-on-surface-variant leading-relaxed">
                We typically respond within <strong className="text-on-surface">1–3 business days</strong>.
                For data deletion requests, we respond within 14 business days as required by applicable privacy law.
              </p>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
