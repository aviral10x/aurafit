export default function Footer() {
  return (
    <footer className="w-full py-12 border-t border-stone-200 bg-stone-100">
      <div className="flex flex-col md:flex-row justify-between items-center px-12 gap-6 max-w-7xl mx-auto">
        <span className="text-lg font-serif text-stone-900 italic">AuraFit</span>
        <div className="flex gap-8">
          <a className="font-sans text-xs tracking-widest uppercase text-stone-500 hover:underline decoration-amber-500 underline-offset-4" href="#">Privacy</a>
          <a className="font-sans text-xs tracking-widest uppercase text-stone-500 hover:underline decoration-amber-500 underline-offset-4" href="#">Terms</a>
          <a className="font-sans text-xs tracking-widest uppercase text-stone-500 hover:underline decoration-amber-500 underline-offset-4" href="#">Contact</a>
        </div>
        <span className="font-sans text-xs tracking-widest uppercase text-stone-500">&copy; 2026 AuraFit. AI-assisted style engine</span>
      </div>
    </footer>
  );
}
