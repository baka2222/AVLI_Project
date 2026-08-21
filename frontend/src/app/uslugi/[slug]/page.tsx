import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Icon } from "@/components/Icon";
import { JsonLd } from "@/components/JsonLd";
import { ServiceCard } from "@/components/ServiceCard";
import { getService, getSiteContent, safeImage, siteUrl } from "@/lib/site";

type Props = { params: Promise<{ slug: string }> };

export async function generateStaticParams() {
  const { services } = await getSiteContent();
  return services.map((item) => ({ slug: item.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const item = await getService(slug);
  if (!item) return {};
  return {
    title: { absolute: item.metaTitle }, description: item.metaDescription,
    alternates: { canonical: `/uslugi/${item.slug}` },
    openGraph: { type: "article", title: item.metaTitle, description: item.metaDescription, url: `/uslugi/${item.slug}`, images: [{ url: safeImage(item.image, "/opengraph-image") }] },
  };
}

export default async function ServiceDetailPage({ params }: Props) {
  const { slug } = await params;
  const item = await getService(slug);
  if (!item) notFound();
  const { services, settings } = await getSiteContent();
  const imageSrc = safeImage(item.image, "/images/services/montazh-truboprovoda.webp");
  const related = services.filter((service) => service.slug !== item.slug).slice(0, 3);
  const schema = [
    { "@context": "https://schema.org", "@type": "Service", name: item.title, description: item.metaDescription, url: `${siteUrl}/uslugi/${item.slug}`, image: `${siteUrl}${safeImage(item.image, "/opengraph-image")}`, provider: { "@id": `${siteUrl}/#organization` }, areaServed: { "@type": "City", name: "Бишкек" }, availableChannel: { "@type": "ServiceChannel", servicePhone: settings.phonePrimary } },
    { "@context": "https://schema.org", "@type": "BreadcrumbList", itemListElement: [{ "@type": "ListItem", position: 1, name: "Главная", item: siteUrl }, { "@type": "ListItem", position: 2, name: "Услуги", item: `${siteUrl}/uslugi` }, { "@type": "ListItem", position: 3, name: item.title, item: `${siteUrl}/uslugi/${item.slug}` }] },
  ];
  return (
    <>
      <JsonLd data={schema} />
      <section className="page-hero service-page-hero"><div className="container">
        <nav className="breadcrumbs" aria-label="Хлебные крошки"><Link href="/">Главная</Link><Icon name="chevron" width="15" height="15" /><Link href="/uslugi">Услуги</Link><Icon name="chevron" width="15" height="15" /><span aria-current="page">{item.title}</span></nav>
        <span className="service-type hero-type">{item.category === "included" ? "Включённая услуга" : "Платная услуга"}</span><h1>{item.title}</h1><p>{item.shortDescription}</p>
      </div></section>
      <section className="section service-detail"><div className="container service-detail-grid">
        <article className="service-article">
          <div className="service-detail-image"><Image src={imageSrc} alt={item.title} fill preload unoptimized={imageSrc.startsWith("/media/")} sizes="(max-width: 900px) 100vw, 65vw" /></div>
          <h2>Об услуге</h2>{item.description.split(/\n\n+/).map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
          <div className="quality-box"><Icon name="shield-check" width="34" height="34" /><div><strong>Работаем аккуратно и ответственно</strong><p>Перед началом уточняем объём задачи, согласовываем условия и используем проверенные материалы.</p></div></div>
        </article>
        <aside className="service-aside"><h2>Заказать услугу</h2><p>Оставьте контакты — уточним детали, сроки и стоимость.</p><a href="#callback" className="button button-primary">Оставить заявку</a><a href={`tel:${settings.phonePrimary.replace(/[^\d+]/g, "")}`} className="aside-phone"><Icon name="phone" width="20" height="20" />{settings.phonePrimary}</a><hr/><h3>Другие разделы</h3><Link href="/company">О компании <Icon name="arrow" width="17" height="17" /></Link><Link href="/contacts">Контакты <Icon name="arrow" width="17" height="17" /></Link></aside>
      </div></section>
      <section className="section related-services"><div className="container"><div className="section-heading"><span className="eyebrow">Другие услуги</span><h2>Вам также может подойти</h2></div><div className="services-grid">{related.map((service) => <ServiceCard key={service.slug} service={service} />)}</div></div></section>
    </>
  );
}
