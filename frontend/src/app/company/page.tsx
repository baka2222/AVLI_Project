import type { Metadata } from "next";
import Image from "next/image";
import { Icon } from "@/components/Icon";
import { JsonLd } from "@/components/JsonLd";
import { PageHero } from "@/components/PageHero";
import { getSiteContent, siteUrl } from "@/lib/site";

export const metadata: Metadata = {
  title: "О компании",
  description: "Узнайте об управляющей компании АВЛИ: прозрачный учёт, профессиональное обслуживание многоквартирных домов и забота о жителях Бишкека.",
  alternates: { canonical: "/company" },
  openGraph: { title: "О компании АВЛИ", description: "Надёжное и прозрачное управление многоквартирными домами в Бишкеке.", url: "/company" },
};

export default async function CompanyPage() {
  const { settings, metrics, features } = await getSiteContent();
  return (
    <>
      <JsonLd data={{ "@context": "https://schema.org", "@type": "AboutPage", "@id": `${siteUrl}/company#page`, url: `${siteUrl}/company`, name: "О компании АВЛИ", description: settings.seoDescription, inLanguage: "ru-KG", about: { "@id": `${siteUrl}/#organization` } }} />
      <PageHero title="О компании АВЛИ" description="Управляем домами так, чтобы жителям было спокойно, понятно и комфортно." current="О компании" />
      <section className="section company-intro"><div className="container split-grid">
        <div className="company-image"><Image src="/images/hero/management.png" alt="Команда управляющей компании АВЛИ" fill preload sizes="(max-width: 850px) 100vw, 48vw" /></div>
        <div className="section-copy"><span className="eyebrow">Кто мы</span><h2>{settings.aboutTitle}</h2><p>{settings.aboutText}</p><p>{settings.aboutTextSecondary}</p></div>
      </div></section>
      <section className="mission-section"><div className="container mission-grid">
        <div><span className="eyebrow light">Наша миссия</span><h2>Порядок, прозрачность и комфорт</h2></div>
        <p>{settings.mission}</p>
      </div></section>
      <section className="section values-section"><div className="container">
        <div className="section-heading centered"><span className="eyebrow">Принципы работы</span><h2>На чём строится доверие жителей</h2></div>
        <div className="values-grid">{features.map((feature) => <article key={feature.title}><span className="feature-icon"><Icon name={feature.icon} width="31" height="31" /></span><h3>{feature.title}</h3><p>{feature.description}</p></article>)}</div>
      </div></section>
      <section className="metrics-section" aria-label="АВЛИ в цифрах"><div className="container metrics-grid">{metrics.map((metric) => <div key={metric.label} className="metric"><Icon name={metric.icon} width="34" height="34" /><strong>{metric.value}</strong><span>{metric.label}</span></div>)}</div></section>
      <section className="section process-section"><div className="container">
        <div className="section-heading"><span className="eyebrow">Как начать</span><h2>Переход под управление АВЛИ</h2></div>
        <ol className="process-grid"><li><span>01</span><h3>Знакомство</h3><p>Обсуждаем задачи дома и отвечаем на вопросы жителей.</p></li><li><span>02</span><h3>Обследование</h3><p>Оцениваем техническое состояние и текущие процессы.</p></li><li><span>03</span><h3>Предложение</h3><p>Готовим прозрачный план работ, тариф и документы.</p></li><li><span>04</span><h3>Начало работы</h3><p>Принимаем дом и запускаем обслуживание по согласованному плану.</p></li></ol>
      </div></section>
    </>
  );
}
