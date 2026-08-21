import type { Metadata } from "next";
import { JsonLd } from "@/components/JsonLd";
import { PageHero } from "@/components/PageHero";
import { ServiceCard } from "@/components/ServiceCard";
import { getSiteContent, siteUrl } from "@/lib/site";

export const metadata: Metadata = {
  title: "Услуги управляющей компании",
  description: "Услуги АВЛИ в Бишкеке: содержание многоквартирных домов, сантехнические работы, ремонт, уборка и монтаж инженерных сетей.",
  alternates: { canonical: "/uslugi" },
  openGraph: { title: "Услуги АВЛИ в Бишкеке", description: "Профессиональное обслуживание и ремонт многоквартирных домов.", url: "/uslugi" },
};

export default async function ServicesPage() {
  const { services } = await getSiteContent();
  return (
    <>
      <JsonLd data={{ "@context": "https://schema.org", "@type": "CollectionPage", name: "Услуги управляющей компании АВЛИ", url: `${siteUrl}/uslugi`, inLanguage: "ru-KG", mainEntity: { "@type": "ItemList", numberOfItems: services.length, itemListElement: services.map((item, index) => ({ "@type": "ListItem", position: index + 1, name: item.title, url: `${siteUrl}/uslugi/${item.slug}` })) } }} />
      <PageHero title="Услуги АВЛИ" description="Профессиональные работы для бесперебойной, безопасной и комфортной жизни вашего дома." current="Услуги" />
      <section className="section services-page"><div className="container">
        <div className="service-note"><strong>Комплексный подход</strong><p>Стоимость и состав работ зависят от задачи и состояния объекта. Оставьте заявку — специалист уточнит детали и подготовит предложение.</p></div>
        <div className="services-grid">{services.map((item) => <ServiceCard key={item.slug} service={item} />)}</div>
      </div></section>
    </>
  );
}
