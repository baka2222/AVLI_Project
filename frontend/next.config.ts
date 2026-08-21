import type { NextConfig } from "next";

const legacyRedirects = [
  ["/index.htm", "/"],
  ["/company/index.htm", "/company"],
  ["/uslugi/index.htm", "/uslugi"],
  ["/contacts.html", "/contacts"],
  ["/uslugi/platnie-uslugi/16-smena-prokladki-v-soedinenii-dusha-so-smesitelem.html.htm", "/uslugi/zamena-prokladki-dusha"],
  ["/uslugi/platnie-uslugi/15-smena-gibkoj-podvodki.html.htm", "/uslugi/zamena-gibkoy-podvodki"],
  ["/uslugi/platnie-uslugi/14-remont-smesitelja-bez-snjatija-s-mesta-pri-nabivke-salnika.html.htm", "/uslugi/remont-smesitelya-salnik"],
  ["/uslugi/platnie-uslugi/13-remont-vodorazbornogo-krana-bez-snjatija-s-mesta.html.htm", "/uslugi/remont-smesitelya-prokladki"],
  ["/uslugi/platnie-uslugi/12-remont-vodorazbornogo-krana-bez-snjatija-s-mesta.html.htm", "/uslugi/remont-vodorazbornogo-krana"],
  ["/uslugi/platnie-uslugi/11-zamena-smesitelej-i-kranov.html.htm", "/uslugi/zamena-smesiteley-i-kranov"],
  ["/uslugi/platnie-uslugi/10-zamena-ili-ustanovka-santehpriborov-i-vodorazbornoj-armatury.html.htm", "/uslugi/ustanovka-santehpriborov"],
  ["/uslugi/besplatnie-uslugi/9-obrisovany-stena-ili-potolok.html.htm", "/uslugi/ochistka-sten-i-potolkov"],
  ["/uslugi/platnie-uslugi/8-montazh-truboprovoda.html.htm", "/uslugi/montazh-truboprovoda"],
];

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  compress: true,
  images: { formats: ["image/avif", "image/webp"], minimumCacheTTL: 86400 },
  async redirects() {
    return legacyRedirects.map(([source, destination]) => ({ source, destination, permanent: true }));
  },
  async headers() {
    return [{
      source: "/(.*)",
      headers: [
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "X-Frame-Options", value: "DENY" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
        { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
      ],
    }];
  },
};

export default nextConfig;
