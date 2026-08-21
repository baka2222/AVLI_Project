import type { MetadataRoute } from "next";
import { siteUrl } from "@/lib/site";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: "*", allow: "/", disallow: ["/admin/", "/api/", "/account/", "/receipts", "/reports/"] },
    sitemap: `${siteUrl}/sitemap.xml`,
    host: siteUrl,
  };
}
