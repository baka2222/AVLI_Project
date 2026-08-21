import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Управляющая компания АВЛИ",
    short_name: "АВЛИ",
    description: "Управление и обслуживание многоквартирных домов в Бишкеке",
    start_url: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#0189df",
    lang: "ru-KG",
    icons: [{ src: "/icon.svg", sizes: "any", type: "image/svg+xml" }],
  };
}
