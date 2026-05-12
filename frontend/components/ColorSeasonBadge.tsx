"use client";

const seasonData: Record<string, { label: string; palette: string[]; gradient: string }> = {
  spring_light: {
    label: "Light Spring",
    palette: ["#FADADD", "#FFD700", "#98FB98", "#87CEEB"],
    gradient: "from-amber-50 to-rose-50",
  },
  spring_warm: {
    label: "Warm Spring",
    palette: ["#FF7F50", "#FFD700", "#90EE90", "#F0E68C"],
    gradient: "from-amber-100 to-orange-50",
  },
  spring_clear: {
    label: "Clear Spring",
    palette: ["#FF6347", "#FFD700", "#00CED1", "#FF69B4"],
    gradient: "from-yellow-50 to-pink-50",
  },
  summer_light: {
    label: "Light Summer",
    palette: ["#B0C4DE", "#D8BFD8", "#E6E6FA", "#F0F8FF"],
    gradient: "from-blue-50 to-purple-50",
  },
  summer_cool: {
    label: "Cool Summer",
    palette: ["#6495ED", "#DDA0DD", "#98AFC7", "#C9C0BB"],
    gradient: "from-slate-100 to-blue-50",
  },
  summer_soft: {
    label: "Soft Summer",
    palette: ["#C4AEAD", "#B0C4DE", "#A9A9A9", "#D2B48C"],
    gradient: "from-stone-100 to-blue-50",
  },
  autumn_soft: {
    label: "Soft Autumn",
    palette: ["#C19A6B", "#8B7D6B", "#9CAF88", "#CD853F"],
    gradient: "from-amber-50 to-stone-100",
  },
  autumn_warm: {
    label: "Warm Autumn",
    palette: ["#B7410E", "#D2691E", "#8B4513", "#DAA520"],
    gradient: "from-orange-50 to-amber-50",
  },
  autumn_deep: {
    label: "Deep Autumn",
    palette: ["#800020", "#8B0000", "#556B2F", "#B8860B"],
    gradient: "from-red-950/10 to-amber-50",
  },
  winter_deep: {
    label: "Deep Winter",
    palette: ["#191970", "#800020", "#006400", "#2F4F4F"],
    gradient: "from-indigo-950/10 to-slate-100",
  },
  winter_cool: {
    label: "Cool Winter",
    palette: ["#4169E1", "#C71585", "#008B8B", "#708090"],
    gradient: "from-blue-100 to-slate-50",
  },
  winter_clear: {
    label: "Clear Winter",
    palette: ["#FF0000", "#0000FF", "#00FF00", "#FFFFFF"],
    gradient: "from-blue-50 to-pink-50",
  },
};

interface ColorSeasonBadgeProps {
  season: string;
  size?: "sm" | "md" | "lg";
}

export default function ColorSeasonBadge({ season, size = "md" }: ColorSeasonBadgeProps) {
  const data = seasonData[season] || {
    label: season?.replace(/_/g, " ") || "Unknown",
    palette: ["#C19A6B", "#8B7D6B", "#9CAF88", "#CD853F"],
    gradient: "from-stone-100 to-amber-50",
  };

  const sizeClasses = {
    sm: { swatch: "w-5 h-5", text: "text-[10px]", gap: "gap-1.5", padding: "px-3 py-2" },
    md: { swatch: "w-7 h-7", text: "text-xs", gap: "gap-2", padding: "px-4 py-3" },
    lg: { swatch: "w-9 h-9", text: "text-sm", gap: "gap-2.5", padding: "px-5 py-4" },
  };

  const s = sizeClasses[size];

  return (
    <div className={`bg-gradient-to-br ${data.gradient} rounded-xl ${s.padding} inline-flex flex-col ${s.gap}`}>
      <span className={`font-label ${s.text} uppercase tracking-widest text-on-surface-variant`}>
        Color Season
      </span>
      <span className="font-headline text-lg italic text-on-surface capitalize">
        {data.label}
      </span>
      <div className="flex gap-1.5">
        {data.palette.map((hex, i) => (
          <div
            key={i}
            className={`${s.swatch} rounded-full ring-1 ring-black/5`}
            style={{ backgroundColor: hex }}
          />
        ))}
      </div>
    </div>
  );
}
