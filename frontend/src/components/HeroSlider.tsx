"use client";

import Image from "next/image";
import { useState } from "react";
import type { HeroSlide } from "@/lib/site";
import { safeImage } from "@/lib/site";
import { Icon } from "./Icon";

export function HeroSlider({ slides }: { slides: HeroSlide[] }) {
  const [active, setActive] = useState(0);
  const shown = slides.length ? slides : [];
  const slide = shown[active];
  if (!slide) return null;
  const imageSrc = safeImage(slide.image, "/images/hero/bishkek.jpg");

  const change = (index: number) => setActive((index + shown.length) % shown.length);

  return (
    <section className="hero" aria-roledescription="carousel" aria-label="О компании АВЛИ">
      <div className="hero-image" key={slide.image}>
        <Image src={imageSrc} alt="" fill loading="eager" fetchPriority="high" unoptimized={imageSrc.startsWith("/media/")} sizes="100vw" />
      </div>
      <div className="hero-shade" />
      <div className="container hero-content" aria-live="polite">
        <span className="hero-eyebrow">{slide.eyebrow}</span>
        <h1>{slide.title}</h1>
        <p>{slide.description}</p>
        <div className="hero-buttons">
          <a className="button button-primary" href="#callback">{slide.buttonText}<Icon name="arrow" width="19" height="19" /></a>
          <a className="button button-ghost" href="/company">Узнать больше</a>
        </div>
      </div>
      {shown.length > 1 && (
        <div className="container hero-controls">
          <button type="button" onClick={() => change(active - 1)} aria-label="Предыдущий слайд"><Icon name="chevron" className="prev-icon" width="20" height="20" /></button>
          <div className="hero-dots">
            {shown.map((item, index) => <button key={item.title} className={index === active ? "active" : ""} type="button" onClick={() => change(index)} aria-label={`Слайд ${index + 1}`} aria-current={index === active ? "true" : undefined} />)}
          </div>
          <button type="button" onClick={() => change(active + 1)} aria-label="Следующий слайд"><Icon name="chevron" width="20" height="20" /></button>
        </div>
      )}
    </section>
  );
}
