import Image from "next/image";
import Link from "next/link";
import type { SiteSettings } from "@/lib/site";
import { phoneHref } from "@/lib/site";
import { Icon } from "./Icon";
import { MobileNav } from "./MobileNav";

export function Header({ settings }: { settings: SiteSettings }) {
  return (
    <>
      <div className="topbar">
        <div className="container topbar-inner">
          <div className="topbar-group">
            <a href={`mailto:${settings.email}`}><Icon name="mail" width="17" height="17" />{settings.email}</a>
            <span className="topbar-address"><Icon name="pin" width="17" height="17" />{settings.address}</span>
          </div>
          <div className="topbar-group">
            <span><Icon name="clock" width="17" height="17" />Пн–Сб: 09:00–18:00</span>
            <a href={phoneHref(settings.phonePrimary)}><Icon name="phone" width="17" height="17" />{settings.phonePrimary}</a>
          </div>
        </div>
      </div>
      <header className="site-header">
        <div className="container header-inner">
          <Link className="logo" href="/" aria-label="АВЛИ — на главную">
            <Image src="/images/logo.png" alt="АВЛИ" width={144} height={60} loading="eager" />
          </Link>
          <nav className="desktop-nav" aria-label="Основная навигация">
            <Link href="/">Главная</Link>
            <Link href="/company">О компании</Link>
            <Link href="/uslugi">Услуги</Link>
            <Link href="/contacts">Контакты</Link>
          </nav>
          <div className="header-actions">
            <a className="resident-button" href="/account/">Личный кабинет</a>
            <a className="button button-primary header-cta" href="#callback">Заказать звонок</a>
          </div>
          <MobileNav />
        </div>
      </header>
    </>
  );
}
