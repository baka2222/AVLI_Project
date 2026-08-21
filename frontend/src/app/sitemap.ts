import type { MetadataRoute } from "next";
import { getSiteContent, safeImage, siteUrl } from "@/lib/site";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const content = await getSiteContent();
  const updated = new Date(content.settings.updatedAt || Date.now());
  const pages: MetadataRoute.Sitemap = [
    { url: siteUrl, lastModified: updated, changeFrequency: "weekly", priority: 1, images: [`${siteUrl}/images/hero/bishkek.jpg`] },
    { url: `${siteUrl}/company`, lastModified: updated, changeFrequency: "monthly", priority: 0.8, images: [`${siteUrl}/images/hero/management.png`] },
    { url: `${siteUrl}/uslugi`, lastModified: updated, changeFrequency: "weekly", priority: 0.9 },
    { url: `${siteUrl}/contacts`, lastModified: updated, changeFrequency: "monthly", priority: 0.7 },
  ];
  return pages.concat(content.services.map((item) => ({
    url: `${siteUrl}/uslugi/${item.slug}`,
    lastModified: new Date(item.updatedAt || content.settings.updatedAt || Date.now()),
    changeFrequency: "monthly" as const,
    priority: 0.75,
    images: [`${siteUrl}${safeImage(item.image, "/opengraph-image")}`],
  })));
}
