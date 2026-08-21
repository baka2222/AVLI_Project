import Image from "next/image";
import Link from "next/link";
import type { SiteSettings } from "@/lib/site";
import { phoneHref } from "@/lib/site";
import { Icon } from "./Icon";

export function Footer({ settings }: { settings: SiteSettings }) {
  return (
    <footer className="footer">
      <div className="container footer-grid">
        <div className="footer-about">
          <Link href="/" className="footer-logo"><Image src="/images/logo.png" alt="АВЛИ" width={137} height={57} /></Link>
          <p>{settings.footerText}</p>
        </div>
        <div>
          <h2>Навигация</h2>
          <nav className="footer-links" aria-label="Навигация в подвале">
            <Link href="/company">О компании</Link>
            <Link href="/uslugi">Все услуги</Link>
            <Link href="/contacts">Контакты</Link>
            <a href="/account/">Личный кабинет</a>
          </nav>
        </div>
        <div>
          <h2>Контакты</h2>
          <div className="footer-contacts">
            <a href={phoneHref(settings.phonePrimary)}><Icon name="phone" width="19" height="19" />{settings.phonePrimary}</a>
            <a href={phoneHref(settings.phoneSecondary)}><Icon name="phone" width="19" height="19" />{settings.phoneSecondary}</a>
            <a href={`mailto:${settings.email}`}><Icon name="mail" width="19" height="19" />{settings.email}</a>
            <span><Icon name="pin" width="19" height="19" />{settings.address}</span>
          </div>
        </div>
        <div>
          <h2>Связаться</h2>
          <p>Ответим на вопросы об управлении домом и услугах.</p>
          <a className="button button-whatsapp" href={`https://wa.me/${settings.whatsappNumber}`} target="_blank" rel="noreferrer">
            <Icon name="whatsapp" width="20" height="20" /> WhatsApp
          </a>
        </div>
      </div>
      <div className="container footer-bottom">
        <span>© {new Date().getFullYear()} ОсОО «АВЛИ». Все права защищены.</span>
        <span>Управляющая компания в Бишкеке</span>
      </div>
    </footer>
  );
}
