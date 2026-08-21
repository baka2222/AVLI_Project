import Link from "next/link";
import { Icon } from "./Icon";

export function PageHero({ title, description, current }: { title: string; description: string; current: string }) {
  return (
    <section className="page-hero">
      <div className="container">
        <nav className="breadcrumbs" aria-label="Хлебные крошки">
          <Link href="/">Главная</Link><Icon name="chevron" width="15" height="15" /><span aria-current="page">{current}</span>
        </nav>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
    </section>
  );
}
