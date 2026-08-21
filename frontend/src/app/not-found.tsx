import Link from "next/link";

export default function NotFound() {
  return <section className="not-found"><div className="container"><span>404</span><h1>Страница не найдена</h1><p>Возможно, адрес изменился или страница была удалена.</p><Link href="/" className="button button-primary">Вернуться на главную</Link></div></section>;
}
