import type { Metadata, Viewport } from "next";
import { CallbackSection } from "@/components/CallbackSection";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { getSiteContent, siteUrl } from "@/lib/site";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const { settings } = await getSiteContent();
  return {
    metadataBase: new URL(siteUrl),
    title: { default: settings.seoTitle, template: "%s | АВЛИ" },
    description: settings.seoDescription,
    applicationName: "АВЛИ",
    authors: [{ name: "ОсОО «АВЛИ»" }],
    creator: "ОсОО «АВЛИ»",
    publisher: "ОсОО «АВЛИ»",
    formatDetection: { email: false, address: false, telephone: false },
    openGraph: {
      type: "website", locale: "ru_KG", url: "/", siteName: "Управляющая компания АВЛИ",
      title: settings.seoTitle, description: settings.seoDescription,
      images: [{ url: "/opengraph-image", width: 1200, height: 630, alt: "Управляющая компания АВЛИ в Бишкеке" }],
    },
    twitter: { card: "summary_large_image", title: settings.seoTitle, description: settings.seoDescription, images: ["/opengraph-image"] },
    category: "Управление недвижимостью",
  };
}

export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#0189df", colorScheme: "light" };

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const { settings } = await getSiteContent();
  return (
    <html lang="ru">
      <body>
        <a className="skip-link" href="#main-content">Перейти к содержанию</a>
        <Header settings={settings} />
        <main id="main-content">{children}</main>
        <CallbackSection settings={settings} />
        <Footer settings={settings} />
      </body>
    </html>
  );
}
