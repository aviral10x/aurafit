"use client";

import Image from "next/image";
import { useState } from "react";
import { motion } from "framer-motion";
import { Heart, ExternalLink, ShoppingBag } from "lucide-react";
import type { OutfitRecommendation } from "@/lib/api";

interface OutfitCardProps {
  outfit: OutfitRecommendation;
}

export default function OutfitCard({ outfit }: OutfitCardProps) {
  const [saved, setSaved] = useState(false);

  const firstBuyUrl = outfit.items[0]?.buy_url;

  return (
    <motion.div
      className="bg-white rounded-2xl overflow-hidden shadow-sm shadow-black/5 flex flex-col"
      whileHover={{ scale: 1.02 }}
      transition={{ type: "spring", stiffness: 300, damping: 25 }}
    >
      {/* Outfit Image */}
      <div className="relative aspect-[3/4] w-full bg-cream overflow-hidden">
        {outfit.image_url ? (
          <Image
            src={outfit.image_url}
            alt={outfit.name}
            fill
            sizes="(min-width: 1280px) 24vw, (min-width: 768px) 33vw, 100vw"
            className="object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-charcoal/20">
            <ShoppingBag size={48} />
          </div>
        )}
        {/* Save Button */}
        <button
          onClick={() => setSaved((s) => !s)}
          className="absolute top-3 right-3 w-9 h-9 rounded-full bg-white/80 backdrop-blur-sm flex items-center justify-center hover:bg-white transition-colors"
          aria-label={saved ? "Unsave outfit" : "Save outfit"}
        >
          <Heart
            size={18}
            className={saved ? "fill-red-500 text-red-500" : "text-charcoal/60"}
          />
        </button>
      </div>

      {/* Content */}
      <div className="p-5 flex flex-col flex-1">
        <h3 className="font-headline text-lg text-charcoal mb-1">
          {outfit.name}
        </h3>
        <p className="font-body text-sm italic text-charcoal/60 mb-4 leading-relaxed">
          {outfit.why_it_works}
        </p>

        {/* Items */}
        <div className="space-y-2 mb-4 flex-1">
          {outfit.items.map((item, index) => (
            <a
              key={index}
              href={item.buy_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between py-1.5 group"
            >
              <div className="flex-1 min-w-0">
                <span className="font-body text-xs text-charcoal/50 uppercase tracking-wide">
                  {item.brand}
                </span>
                <p className="font-body text-sm text-charcoal truncate">
                  {item.name}
                </p>
              </div>
              <div className="flex items-center gap-1.5 ml-3 shrink-0">
                <span className="font-body text-sm font-medium text-charcoal">
                  ${item.price_usd}
                </span>
                <ExternalLink
                  size={12}
                  className="text-charcoal/30 group-hover:text-gold transition-colors"
                />
              </div>
            </a>
          ))}
        </div>

        {/* Total */}
        <div className="flex items-center justify-between border-t border-black/5 pt-3 mb-4">
          <span className="font-body text-xs uppercase tracking-widest text-charcoal/50">
            Total
          </span>
          <span className="font-headline text-lg text-charcoal">
            ${outfit.total_price_usd}
          </span>
        </div>

        {/* Style Tags */}
        {outfit.style_tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-4">
            {outfit.style_tags.map((tag) => (
              <span
                key={tag}
                className="bg-cream-dark rounded-full px-3 py-0.5 font-body text-xs text-charcoal/70"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* CTA */}
        {firstBuyUrl && (
          <a
            href={firstBuyUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full bg-gold text-white font-body text-sm font-medium text-center rounded-full py-3 hover:opacity-90 transition-opacity"
          >
            Shop This Look
          </a>
        )}
      </div>
    </motion.div>
  );
}
