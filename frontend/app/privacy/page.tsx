import Link from "next/link";
import type { Metadata } from "next";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "Privacy Policy | AuraFit",
  description: "How AuraFit handles your photos, data, and personal information.",
};

export default function PrivacyPage() {
  return (
    <>
      <Navbar />
      <main className="pt-32 pb-24 px-6 md:px-12 max-w-3xl mx-auto">
        <header className="mb-16">
          <span className="font-label text-[10px] tracking-[0.3em] uppercase text-primary mb-4 block">Legal</span>
          <h1 className="font-headline text-5xl mb-6">Privacy Policy</h1>
          <p className="font-body text-on-surface-variant">Last updated: May 2026</p>
        </header>

        <div className="prose-aura space-y-12">

          <section className="bg-primary-fixed/10 border border-primary/10 rounded-xl p-8">
            <div className="flex gap-4">
              <span className="material-symbols-outlined text-primary text-3xl shrink-0">shield</span>
              <div>
                <h2 className="font-headline text-xl mb-3">The short version</h2>
                <ul className="space-y-2 font-body text-sm text-on-surface-variant leading-relaxed">
                  <li>• Your photos are encrypted in transit and at rest</li>
                  <li>• We never sell your data or photos to third parties</li>
                  <li>• Photos are auto-deleted after 30 days unless you request earlier deletion</li>
                  <li>• You can delete your account and all data at any time</li>
                  <li>• AI analysis is done by Anthropic's Claude — subject to their policies</li>
                </ul>
              </div>
            </div>
          </section>

          <PolicySection title="1. What we collect">
            <p>When you use AuraFit, we collect:</p>
            <ul>
              <li><strong>Photos you upload</strong> — used solely to generate your style analysis. Never used for training AI models.</li>
              <li><strong>Style preferences</strong> — gender, style archetypes, occasions, goals, and budget range you select during the upload flow.</li>
              <li><strong>Email address</strong> — collected if you create an account, used only for authentication (OTP) and service-related communication.</li>
              <li><strong>Analysis results</strong> — your style profile, color palette, body type, and outfit recommendations are stored so you can access them again.</li>
              <li><strong>Usage data</strong> — page views, feature interactions, and error logs used to improve the service. No tracking pixels or ad networks.</li>
            </ul>
          </PolicySection>

          <PolicySection title="2. How we use your photos">
            <p>Your uploaded photos are processed exclusively to generate your personalized style analysis. Specifically:</p>
            <ul>
              <li>Photos are sent to Anthropic's Claude API for vision analysis (skin tone, body type, face shape detection)</li>
              <li>Photos are stored temporarily in Supabase Storage with server-side encryption</li>
              <li>Photos are <strong>never</strong> shared with third parties, used in ads, or used to train AI models</li>
              <li>Photos are automatically deleted after <strong>30 days</strong></li>
              <li>You can request immediate deletion at any time — see Section 6</li>
            </ul>
          </PolicySection>

          <PolicySection title="3. AI processing & third parties">
            <p>AuraFit uses the following third-party services:</p>
            <ul>
              <li><strong>Anthropic (Claude API)</strong> — for photo analysis and outfit generation. Subject to <a href="https://www.anthropic.com/legal/privacy" target="_blank" rel="noopener noreferrer" className="text-primary underline underline-offset-4">Anthropic's Privacy Policy</a>.</li>
              <li><strong>Supabase</strong> — for database, authentication, and file storage. Subject to <a href="https://supabase.com/privacy" target="_blank" rel="noopener noreferrer" className="text-primary underline underline-offset-4">Supabase's Privacy Policy</a>.</li>
              <li><strong>Vercel</strong> — for frontend hosting. Subject to <a href="https://vercel.com/legal/privacy-policy" target="_blank" rel="noopener noreferrer" className="text-primary underline underline-offset-4">Vercel's Privacy Policy</a>.</li>
              <li><strong>OpenAI</strong> — for visual board image generation (where applicable). Subject to <a href="https://openai.com/policies/privacy-policy" target="_blank" rel="noopener noreferrer" className="text-primary underline underline-offset-4">OpenAI's Privacy Policy</a>.</li>
            </ul>
            <p>We do not sell, rent, or otherwise share your personal data with any other third parties for marketing or commercial purposes.</p>
          </PolicySection>

          <PolicySection title="4. Style analysis disclaimer">
            <p>AuraFit provides AI-generated style suggestions for <strong>informational and fashion guidance purposes only</strong>. Our analysis:</p>
            <ul>
              <li>Is not a medical or health assessment</li>
              <li>Does not constitute professional beauty, cosmetic, or surgical advice</li>
              <li>Should not be used as the basis for medical or surgical decisions</li>
              <li>Uses empowering, body-positive language — we do not generate harmful attractiveness scores</li>
            </ul>
            <p>If our analysis includes suggestions related to facial features or hairstyle, these are purely aesthetic and non-medical recommendations. Always consult qualified professionals for medical decisions.</p>
          </PolicySection>

          <PolicySection title="5. Data retention">
            <ul>
              <li><strong>Photos:</strong> Deleted automatically after 30 days. Deleted immediately on account deletion.</li>
              <li><strong>Style analysis results:</strong> Retained while your account is active. Deleted on account deletion or on request.</li>
              <li><strong>Account data:</strong> Retained while your account is active. Deleted within 30 days of account deletion request.</li>
              <li><strong>Usage logs:</strong> Retained for up to 90 days for debugging and service improvement, then deleted.</li>
            </ul>
          </PolicySection>

          <PolicySection title="6. Your rights & data deletion">
            <p>You have the right to:</p>
            <ul>
              <li>Access all personal data we hold about you</li>
              <li>Request correction of inaccurate data</li>
              <li>Request deletion of your account and all associated data</li>
              <li>Request an export of your data in machine-readable format</li>
              <li>Withdraw consent for photo storage at any time</li>
            </ul>
            <p>
              To exercise these rights, email us at{" "}
              <a href="mailto:privacy@aurafit.fun" className="text-primary underline underline-offset-4">
                privacy@aurafit.fun
              </a>{" "}
              or use the account deletion option in your profile. We will respond within 14 business days.
            </p>
          </PolicySection>

          <PolicySection title="7. Security">
            <p>We implement industry-standard security measures including:</p>
            <ul>
              <li>TLS encryption for all data in transit</li>
              <li>AES-256 encryption for data at rest in Supabase Storage</li>
              <li>Signed, time-limited URLs for photo access</li>
              <li>No direct client-side database access</li>
            </ul>
          </PolicySection>

          <PolicySection title="8. Contact">
            <p>
              For privacy concerns or data requests, contact us at{" "}
              <a href="mailto:privacy@aurafit.fun" className="text-primary underline underline-offset-4">
                privacy@aurafit.fun
              </a>
              .
            </p>
          </PolicySection>

        </div>

        <div className="mt-16 pt-8 border-t border-outline-variant/30 flex gap-6">
          <Link href="/terms" className="font-label text-xs uppercase tracking-widest text-on-surface-variant hover:text-primary transition-colors">
            Terms of Service
          </Link>
          <Link href="/contact" className="font-label text-xs uppercase tracking-widest text-on-surface-variant hover:text-primary transition-colors">
            Contact
          </Link>
        </div>
      </main>
      <Footer />
    </>
  );
}

function PolicySection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="font-headline text-2xl mb-5 text-on-surface">{title}</h2>
      <div className="font-body text-sm text-on-surface-variant leading-relaxed space-y-4 [&_ul]:space-y-2 [&_ul]:pl-4 [&_li]:leading-relaxed [&_strong]:text-on-surface [&_a]:text-primary">
        {children}
      </div>
    </section>
  );
}
