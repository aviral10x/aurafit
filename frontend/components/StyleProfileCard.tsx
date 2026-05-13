"use client";

import { motion } from "framer-motion";
import type { StyleProfile } from "@/lib/api";
import ColorPalette from "./ColorPalette";
import BodyTypeSilhouette from "./BodyTypeSilhouette";

interface StyleProfileCardProps {
  profile: StyleProfile;
}

export default function StyleProfileCard({ profile }: StyleProfileCardProps) {
  return (
    <motion.div
      className="bg-white rounded-2xl shadow-sm shadow-black/5 p-8 max-w-2xl w-full"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
    >
      <h2 className="font-headline text-2xl text-charcoal mb-6">
        Your Style Profile
      </h2>

      {/* Skin Tone */}
      <div className="mb-6">
        <h3 className="font-body text-xs uppercase tracking-widest text-charcoal/50 mb-3">
          Skin Tone
        </h3>
        <div className="flex items-center gap-3">
          <div
            className="w-8 h-8 rounded-full shadow-sm border border-black/5"
            style={{ backgroundColor: profile.skin_tone.hex_color }}
          />
          <div>
            <span className="font-body text-sm text-charcoal font-medium">
              {profile.skin_tone.label}
            </span>
            <span className="font-body text-xs text-charcoal/50 ml-2">
              {profile.skin_tone.fitzpatrick} &middot; {profile.skin_tone.undertone} undertone
            </span>
          </div>
        </div>
      </div>

      {/* Color Palette */}
      <div className="mb-6">
        <h3 className="font-body text-xs uppercase tracking-widest text-charcoal/50 mb-3">
          Your Colors
        </h3>
        <ColorPalette colors={profile.color_palette} />
      </div>

      {/* Body Type */}
      <div className="mb-6">
        <h3 className="font-body text-xs uppercase tracking-widest text-charcoal/50 mb-3">
          Body Type
        </h3>
        <BodyTypeSilhouette
          shape={profile.body_type.shape}
          build={profile.body_type.build}
        />
      </div>

      {/* Style Vibes */}
      <div>
        <h3 className="font-body text-xs uppercase tracking-widest text-charcoal/50 mb-3">
          Style Vibes
        </h3>
        <div className="flex flex-wrap gap-2">
          {profile.style_vibes.map((vibe) => (
            <span
              key={vibe}
              className="bg-cream-dark rounded-full px-4 py-1 font-body text-sm text-charcoal"
            >
              {vibe}
            </span>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
