import type { Metadata } from "next";
import Image from "next/image";
import { Icon } from "@/components/Icon";
import { JsonLd } from "@/components/JsonLd";
import { PageHero } from "@/components/PageHero";
import { getSiteContent, phoneHref, siteUrl } from "@/lib/site";

export const metadata: Metadata = {
  title: "Контакты",
  description: "Контакты управляющей компании АВЛИ в Бишкеке: телефоны, электронная почта, адрес офиса и схема проезда.",
  alternates: { canonical: "/contacts" },
  openGraph: { title: "Контакты АВЛИ", description: "Свяжитесь с управляющей компанией АВЛИ в Бишкеке.", url: "/contacts" },
};

export default async function ContactsPage() {
  const { settings } = await getSiteContent();
  const encodedAddress = encodeURIComponent(settings.address);
  const googleMapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodedAddress}`;
  const twoGisUrl = `https://2gis.kg/bishkek/search/${encodedAddress}`;

  return (
    <>
      <JsonLd data={{ "@context": "https://schema.org", "@type": "ContactPage", name: "Контакты АВЛИ", url: `${siteUrl}/contacts`, mainEntity: { "@id": `${siteUrl}/#organization` } }} />
      <PageHero title="Контакты" description="Мы рядом и готовы ответить на вопросы жителей, домовых комитетов и партнёров." current="Контакты" />
      <section className="section contacts-section"><div className="container contacts-grid">
        <div className="contact-cards">
          <article><span className="feature-icon"><Icon name="phone" width="28" height="28" /></span><div><h2>Телефоны</h2><a href={phoneHref(settings.phonePrimary)}>{settings.phonePrimary}</a><a href={phoneHref(settings.phoneSecondary)}>{settings.phoneSecondary}</a></div></article>
          <article><span className="feature-icon"><Icon name="mail" width="28" height="28" /></span><div><h2>Электронная почта</h2><a href={`mailto:${settings.email}`}>{settings.email}</a><p>Для обращений и документов</p></div></article>
          <article><span className="feature-icon"><Icon name="pin" width="28" height="28" /></span><div><h2>Адрес офиса</h2><p>{settings.address}</p></div></article>
          <article><span className="feature-icon"><Icon name="clock" width="28" height="28" /></span><div><h2>Режим работы</h2><p>Понедельник–суббота<br/>09:00–18:00</p></div></article>
          <a className="button button-whatsapp contact-whatsapp" href={`https://wa.me/${settings.whatsappNumber}`} target="_blank" rel="noreferrer"><Icon name="whatsapp" width="20" height="20" />Написать в WhatsApp</a>
        </div>
        <div className="location-panel">
          <Image src="/images/hero/bishkek.jpg" alt="Панорама Бишкека" fill sizes="(max-width: 850px) 100vw, 65vw" />
          <div className="location-panel-shade" />
          <div className="location-panel-content">
            <span className="location-kicker"><Icon name="pin" width="18" height="18" />Наш офис</span>
            <h2>Приезжайте в офис АВЛИ</h2>
            <address>{settings.address}</address>
            <p>Перед приездом рекомендуем позвонить — специалист подскажет ориентир и подготовит нужные документы.</p>
            <div className="location-actions">
              <a className="button button-primary" href={googleMapsUrl} target="_blank" rel="noreferrer"><Icon name="pin" width="19" height="19" />Открыть в Google Maps</a>
              <a className="button button-ghost" href={twoGisUrl} target="_blank" rel="noreferrer">Открыть в 2ГИС<Icon name="arrow" width="19" height="19" /></a>
            </div>
          </div>
        </div>
      </div></section>
    </>
  );
}
