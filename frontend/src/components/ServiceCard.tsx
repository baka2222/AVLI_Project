import Image from "next/image";
import Link from "next/link";
import type { Service } from "@/lib/site";
import { safeImage } from "@/lib/site";
import { Icon } from "./Icon";

export function ServiceCard({ service }: { service: Service }) {
  const imageSrc = safeImage(service.image, "/images/services/montazh-truboprovoda.webp");
  return (
    <article className="service-card">
      <Link href={`/uslugi/${service.slug}`} className="service-image" tabIndex={-1} aria-hidden="true">
        <Image src={imageSrc} alt="" fill unoptimized={imageSrc.startsWith("/media/")} sizes="(max-width: 700px) 100vw, (max-width: 1100px) 50vw, 33vw" />
      </Link>
      <div className="service-card-body">
        <span className="service-type">{service.category === "included" ? "Включённая услуга" : "Платная услуга"}</span>
        <h3><Link href={`/uslugi/${service.slug}`}>{service.title}</Link></h3>
        <p>{service.shortDescription}</p>
        <Link className="text-link" href={`/uslugi/${service.slug}`}>Подробнее <Icon name="arrow" width="18" height="18" /></Link>
      </div>
    </article>
  );
}
