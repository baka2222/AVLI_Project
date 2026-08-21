import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { HeroSlider } from "@/components/HeroSlider";
import { Icon } from "@/components/Icon";
import { JsonLd } from "@/components/JsonLd";
import { ServiceCard } from "@/components/ServiceCard";
import { WhyTabs } from "@/components/WhyTabs";
import { getSiteContent, safeImage, siteUrl } from "@/lib/site";

export async function generateMetadata(): Promise<Metadata> {
  const { settings } = await getSiteContent();
  return { title: { absolute: settings.seoTitle }, description: settings.seoDescription, alternates: { canonical: "/" } };
}

export default async function HomePage() {
  const content = await getSiteContent();
  const { settings } = content;
  const featured = content.services.filter((item) => item.isFeatured).slice(0, 3);
  const schema = [
    {
      "@context": "https://schema.org", "@type": ["Organization", "LocalBusiness"], "@id": `${siteUrl}/#organization`,
      name: settings.companyName, alternateName: settings.shortName, url: siteUrl, logo: `${siteUrl}/images/logo.png`, image: `${siteUrl}/opengraph-image`,
      description: settings.seoDescription, email: settings.email, telephone: settings.phonePrimary,
      address: { "@type": "PostalAddress", streetAddress: settings.address, addressLocality: "Бишкек", addressCountry: "KG" },
      areaServed: { "@type": "City", name: "Бишкек" },
      contactPoint: [{ "@type": "ContactPoint", telephone: settings.phonePrimary, contactType: "customer service", availableLanguage: ["ru", "ky"] }],
    },
    { "@context": "https://schema.org", "@type": "WebSite", "@id": `${siteUrl}/#website`, url: siteUrl, name: "АВЛИ", inLanguage: "ru-KG", publisher: { "@id": `${siteUrl}/#organization` } },
    { "@context": "https://schema.org", "@type": "FAQPage", mainEntity: content.faq.map((item) => ({ "@type": "Question", name: item.question, acceptedAnswer: { "@type": "Answer", text: item.answer } })) },
  ];

  return (
    <>
      <JsonLd data={schema} />
      <HeroSlider slides={content.heroSlides} />

      <section className="feature-strip" aria-label="Преимущества">
        <div className="container feature-grid">
          {content.features.map((feature) => (
            <article key={feature.title} className="feature-item">
              <span className="feature-icon"><Icon name={feature.icon} width="30" height="30" /></span>
              <div><h2>{feature.title}</h2><p>{feature.description}</p></div>
            </article>
          ))}
        </div>
      </section>

      <section className="section about-home">
        <div className="container split-grid">
          <div className="about-visual">
            <div className="about-image-main"><Image src="/images/sections/yard.webp" alt="Ухоженная территория жилого дома" fill sizes="(max-width: 850px) 100vw, 48vw" /></div>
            <div className="about-image-small"><Image src="/images/sections/professionalism.webp" alt="Работа специалистов АВЛИ" fill sizes="280px" /></div>
            <div className="experience-badge"><strong>5+</strong><span>домов доверяют нам</span></div>
          </div>
          <div className="section-copy">
            <span className="eyebrow">О компании</span><h2>{settings.aboutTitle}</h2><p>{settings.aboutText}</p><p>{settings.aboutTextSecondary}</p>
            <ul className="check-list">
              <li><Icon name="check" width="18" height="18" />Работаем по законодательству Кыргызской Республики</li>
              <li><Icon name="check" width="18" height="18" />Отчитываемся о каждом поступлении и расходе</li>
              <li><Icon name="check" width="18" height="18" />Решаем технические и бытовые вопросы дома</li>
            </ul>
            <Link href="/company" className="button button-secondary">Подробнее о нас <Icon name="arrow" width="19" height="19" /></Link>
          </div>
        </div>
      </section>

      <section className="metrics-section" aria-label="АВЛИ в цифрах"><div className="container metrics-grid">
        {content.metrics.map((metric) => <div key={metric.label} className="metric"><Icon name={metric.icon} width="34" height="34" /><strong>{metric.value}</strong><span>{metric.label}</span></div>)}
      </div></section>

      <section className="section services-home"><div className="container">
        <div className="section-heading centered"><span className="eyebrow">Наши услуги</span><h2>Заботимся о доме комплексно</h2><p>От ежедневного содержания до ремонта инженерных сетей — всё в одних ответственных руках.</p></div>
        <div className="services-grid">{featured.map((item) => <ServiceCard key={item.slug} service={item} />)}</div>
        <div className="section-action"><Link href="/uslugi" className="button button-secondary">Смотреть все услуги <Icon name="arrow" width="19" height="19" /></Link></div>
      </div></section>

      <section className="home-banner"><Image src="/images/hero/modern-house.jpg" alt="" fill sizes="100vw" /><div className="home-banner-shade" /><div className="container home-banner-content"><span>Управление без хаоса</span><h2>Ваш дом заслуживает порядка</h2><p>Проведём бесплатную первичную консультацию и расскажем, как перейти под управление АВЛИ.</p><a href="#callback" className="button button-primary">Обсудить ваш дом</a></div></section>

      <section className="section why-section"><div className="container"><div className="section-heading centered"><span className="eyebrow">Почему АВЛИ</span><h2>Понятная работа. Видимый результат.</h2></div><WhyTabs /></div></section>

      <section className="section testimonials-section"><div className="container">
        <div className="section-heading"><span className="eyebrow">Отзывы жителей</span><h2>Доверие начинается с дел</h2></div>
        <div className="testimonials-grid">{content.testimonials.map((item) => <blockquote key={item.name} className="testimonial"><div className="stars" role="img" aria-label="Оценка: 5 из 5">{[1,2,3,4,5].map((star) => <Icon key={star} name="star" width="17" height="17" />)}</div><p>«{item.text}»</p><footer><span className="avatar">{item.initials}</span><div><cite>{item.name}</cite><span>{item.role}</span></div></footer></blockquote>)}</div>
      </div></section>

      <section className="section faq-section"><div className="container faq-grid">
        <div className="faq-image"><Image src={safeImage("/images/sections/faq.jpg", "/images/hero/bishkek.jpg")} alt="Современный жилой комплекс" fill sizes="(max-width: 850px) 100vw, 42vw" /></div>
        <div><span className="eyebrow">Частые вопросы</span><h2>Отвечаем понятно</h2><div className="faq-list">{content.faq.map((item, index) => <details key={item.question} open={index === 0}><summary>{item.question}<span>+</span></summary><p>{item.answer}</p></details>)}</div></div>
      </div></section>
    </>
  );
}
