"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Icon } from "./Icon";

const links = [
  ["/", "Главная"],
  ["/company", "О компании"],
  ["/uslugi", "Услуги"],
  ["/contacts", "Контакты"],
];

export function MobileNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  return (
    <div className="mobile-nav">
      <button className="menu-button" type="button" onClick={() => setOpen(!open)} aria-expanded={open} aria-controls="mobile-menu" aria-label={open ? "Закрыть меню" : "Открыть меню"}>
        <Icon name={open ? "close" : "menu"} width="25" height="25" />
      </button>
      <nav id="mobile-menu" className={open ? "mobile-menu is-open" : "mobile-menu"} aria-label="Мобильная навигация">
        {links.map(([href, label]) => (
          <Link key={href} href={href} className={pathname === href || (href !== "/" && pathname.startsWith(href)) ? "active" : ""} onClick={() => setOpen(false)}>
            {label}
          </Link>
        ))}
        <a href="/account/" className="resident-link" onClick={() => setOpen(false)}>Личный кабинет</a>
      </nav>
    </div>
  );
}
