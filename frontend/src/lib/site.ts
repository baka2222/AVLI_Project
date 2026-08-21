import { cache } from "react";

export type SiteSettings = {
  companyName: string;
  shortName: string;
  tagline: string;
  aboutTitle: string;
  aboutText: string;
  aboutTextSecondary: string;
  mission: string;
  footerText: string;
  address: string;
  phonePrimary: string;
  phoneSecondary: string;
  email: string;
  whatsappNumber: string;
  telegramUrl: string;
  mapEmbedUrl: string;
  seoTitle: string;
  seoDescription: string;
  ogImage: string;
  updatedAt: string;
};

export type HeroSlide = {
  eyebrow: string;
  title: string;
  description: string;
  buttonText: string;
  image: string;
};

export type Feature = { title: string; description: string; icon: string };
export type Metric = { value: string; label: string; icon: string };
export type Testimonial = { name: string; role: string; text: string; initials: string };
export type Faq = { question: string; answer: string };

export type Service = {
  slug: string;
  title: string;
  shortDescription: string;
  description: string;
  priceLabel: string;
  category: string;
  image: string;
  isFeatured: boolean;
  legacyPath: string;
  metaTitle: string;
  metaDescription: string;
  updatedAt: string;
};

export type SiteContent = {
  ok: boolean;
  settings: SiteSettings;
  heroSlides: HeroSlide[];
  features: Feature[];
  metrics: Metric[];
  services: Service[];
  testimonials: Testimonial[];
  faq: Faq[];
};

const now = "2026-08-21T00:00:00+06:00";

const service = (
  slug: string,
  title: string,
  shortDescription: string,
  description: string,
  image: string,
  category = "paid",
  isFeatured = false,
): Service => ({
  slug,
  title,
  shortDescription,
  description,
  priceLabel: "По запросу",
  category,
  image,
  isFeatured,
  legacyPath: "",
  metaTitle: `${title} в Бишкеке — ОсОО «АВЛИ»`,
  metaDescription: shortDescription,
  updatedAt: now,
});

export const fallbackContent: SiteContent = {
  ok: true,
  settings: {
    companyName: "ОсОО «АВЛИ»",
    shortName: "АВЛИ",
    tagline: "Надёжное управление многоквартирными домами в Бишкеке",
    aboutTitle: "Надёжный партнёр вашего дома",
    aboutText:
      "ОсОО «АВЛИ» — современная управляющая компания, которая берёт на себя полную ответственность за управление многоквартирными домами. Мы обеспечиваем прозрачный финансовый учёт, регулярную отчётность и эффективное расходование средств жителей исключительно на благоустройство и содержание дома.",
    aboutTextSecondary:
      "Наши профессиональные бригады выполняют все необходимые работы: уборку подъездов и территории, ремонт, обслуживание кровли, освещения и входных групп. Собственные подрядчики позволяют предлагать жителям честные условия и качественно выполнять задачи в установленные сроки.",
    mission:
      "Наша миссия — порядок, прозрачность и комфорт. Мы работаем в соответствии с законодательством Кыргызской Республики и регулярно отчитываемся перед жителями о поступлениях и расходах.",
    footerText:
      "ОсОО «АВЛИ» — ваш надёжный партнёр в управлении многоквартирными домами. Порядок, прозрачность и забота о каждом доме.",
    address: "г. Бишкек, мкр. Улан-2, дом 2/25, офис 3",
    phonePrimary: "+996 225 215 740",
    phoneSecondary: "+996 555 215 740",
    email: "uk-avli@yandex.ru",
    whatsappNumber: "996225215740",
    telegramUrl: "",
    mapEmbedUrl:
      "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d1462.6587746889343!2d74.63196153882579!3d42.845027642787976!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x389eb66758988fcd%3A0x3c7b52b85d774065!2sUlan-2%2C%20Bishkek!5e0!3m2!1sen!2skg!4v1784060257213!5m2!1sen!2skg",
    seoTitle: "Управляющая компания АВЛИ в Бишкеке — обслуживание жилых домов",
    seoDescription:
      "ОсОО «АВЛИ» — управление многоквартирными домами в Бишкеке: прозрачная отчётность, уборка, ремонт, обслуживание инженерных сетей и поддержка 24/7.",
    ogImage: "/opengraph-image",
    updatedAt: now,
  },
  heroSlides: [
    {
      eyebrow: "Приветствуем!",
      title: "Прозрачное управление вашим домом",
      description:
        "Берём на себя полное управление многоквартирным домом: прозрачный учёт платежей, своевременные ремонты, уборку и содержание территории.",
      buttonText: "Заказать звонок",
      image: "/images/hero/bishkek.jpg",
    },
    {
      eyebrow: "Дом в надёжных руках",
      title: "Комфорт и порядок каждый день",
      description:
        "Профессиональные бригады, собственные подрядчики и полный цикл работ: от уборки до оперативного решения бытовых вопросов.",
      buttonText: "Получить консультацию",
      image: "/images/hero/management.png",
    },
    {
      eyebrow: "Понятно каждому жителю",
      title: "Полная прозрачность и контроль",
      description:
        "Регулярная отчётность, понятный единый тариф, профессиональная бухгалтерия и своевременная сдача документов.",
      buttonText: "Оставить заявку",
      image: "/images/hero/modern-house.jpg",
    },
  ],
  features: [
    {
      title: "Прозрачный учёт и контроль",
      description: "Подробно учитываем поступления и расходы и регулярно отчитываемся перед жителями.",
      icon: "shield-check",
    },
    {
      title: "Полная бухгалтерия и отчётность",
      description: "Берём на себя бухгалтерский учёт, налоги, обязательные платежи и отчётность.",
      icon: "file-chart",
    },
    {
      title: "Комфорт и чистота в доме",
      description: "Уборка, ремонт, освещение и другие услуги для поддержания порядка и уюта.",
      icon: "house-heart",
    },
    {
      title: "Профессиональные подрядчики",
      description: "Проверенные бригады, бесплатное обследование дома и составление сметы.",
      icon: "hard-hat",
    },
  ],
  metrics: [
    { value: "5+", label: "Домов под управлением", icon: "building" },
    { value: "98%", label: "Довольных жильцов", icon: "users" },
    { value: "24/7", label: "Служба поддержки", icon: "headphones" },
    { value: "504", label: "Улыбки жителей", icon: "smile" },
  ],
  services: [
    service("zamena-prokladki-dusha", "Смена прокладки в соединении душа со смесителем", "Устранение протечек и восстановление герметичности соединения душа со смесителем.", "Специалисты ОсОО «АВЛИ» оперативно заменят изношенную прокладку и восстановят герметичность соединения. Все работы выполняются с гарантией качества.", "/images/services/smena-prokladki-dusha.webp"),
    service("zamena-gibkoy-podvodki", "Смена гибкой подводки", "Быстрая замена подводки для надёжного и безопасного подключения воды.", "Наши специалисты выполняют замену быстро и аккуратно, используя надёжные материалы, соответствующие стандартам безопасности.", "/images/services/smena-gibkoy-podvodki.webp"),
    service("remont-smesitelya-salnik", "Ремонт смесителя при набивке сальника", "Ремонт смесителя без демонтажа с восстановлением герметичности сальника.", "Набивка сальника помогает устранить протечку и продлить срок службы смесителя. Работы выполняются на месте без демонтажа оборудования.", "/images/services/nabivka-salnika.webp"),
    service("remont-smesitelya-prokladki", "Ремонт смесителя с заменой прокладок", "Устранение течи и восстановление работы смесителя без снятия с места.", "Используем качественные прокладки и профессиональный инструмент, что обеспечивает долговечность выполненного ремонта.", "/images/services/remont-krana-prokladok.webp", "paid", true),
    service("remont-vodorazbornogo-krana", "Ремонт водоразборного крана без снятия", "Оперативное устранение протечек и замена изношенных деталей без демонтажа.", "Ремонтируем кран на месте, минимизируя неудобства для жителей и обеспечивая долговечный результат.", "/images/services/remont-krana.webp", "paid", true),
    service("zamena-smesiteley-i-kranov", "Замена смесителей и кранов", "Профессиональная установка и замена смесителей и водоразборных кранов.", "Выполняем установку и замену смесителей для кухни и ванной, а также кранов для водоснабжения.", "/images/services/zamena-smesiteley.webp"),
    service("ustanovka-santehpriborov", "Установка сантехприборов и водоразборной арматуры", "Монтаж раковин, унитазов, ванн, смесителей, кранов и вентилей.", "Гарантируем качественное выполнение работ и соблюдение технических норм.", "/images/services/zamena-vodorazbornoy-armaturi.webp"),
    service("ochistka-sten-i-potolkov", "Очистка стен и потолков от рисунков", "Удаление граффити, надписей и загрязнений в местах общего пользования.", "Удаляем граффити и надписи безопасными средствами, не повреждающими поверхность.", "/images/services/remont-podezda.webp", "included"),
    service("montazh-truboprovoda", "Монтаж и замена трубопровода", "Монтаж труб для горячей и холодной воды, канализации и отопления.", "Оцениваем состояние коммуникаций, предлагаем оптимальное решение и выполняем монтаж современными материалами.", "/images/services/montazh-truboprovoda.webp", "paid", true),
  ],
  testimonials: [
    { name: "Айдарбеков Нурлан", role: "Житель", initials: "АН", text: "С «АВЛИ» в нашем доме наконец-то появился порядок. Деньги идут именно на нужды дома, а по расходам всегда есть отчёт." },
    { name: "Светлана Петрова", role: "Жительница", initials: "СП", text: "Чистый двор, отремонтированная крыша и входная группа. Бухгалтерия прозрачная, всегда можно посмотреть отчёт." },
    { name: "Эсенбекова Айгуль", role: "Жительница", initials: "ЭА", text: "Быстро реагируют на заявки, качественно делают ремонт в подъездах. Особенно радует, что есть свои бригады." },
    { name: "Дмитрий Ким", role: "Житель", initials: "ДК", text: "С «АВЛИ» всё прозрачно: видим, куда идут деньги, подъезды чистые, территория ухоженная." },
  ],
  faq: [
    { question: "Как работает управление домом в «АВЛИ»?", answer: "Жители оплачивают единый тариф. Основная часть средств направляется на уборку, ремонты, освещение и благоустройство, а компания полностью берёт на себя управление домом." },
    { question: "Насколько прозрачно расходуются деньги жителей?", answer: "Все платежи идут на содержание и благоустройство вашего дома. Мы ведём прозрачный учёт и регулярно предоставляем отчёты о поступлениях и расходах." },
    { question: "Входят ли ремонт подъездов, крыши и территории в ваши обязанности?", answer: "Да. За счёт накопленных средств мы организуем уборку, ремонт входных групп и кровли, освещение и другие работы по содержанию дома." },
    { question: "Как заключить договор с «АВЛИ»?", answer: "Обсудите предложение с жильцами и обратитесь к домовому комитету. Наши специалисты проведут встречу, ответят на вопросы и помогут оформить документы." },
  ],
};

const API_BASE = (process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export const getSiteContent = cache(async (): Promise<SiteContent> => {
  try {
    const response = await fetch(`${API_BASE}/api/v1/site/content/`, {
      next: { revalidate: 300, tags: ["site-content"] },
      signal: AbortSignal.timeout(3500),
    });
    if (!response.ok) throw new Error(`Site API returned ${response.status}`);
    return (await response.json()) as SiteContent;
  } catch {
    return fallbackContent;
  }
});

export const getService = cache(async (slug: string): Promise<Service | undefined> => {
  const content = await getSiteContent();
  return content.services.find((item) => item.slug === slug);
});

export const siteUrl = (process.env.NEXT_PUBLIC_SITE_URL || "https://avli.kg").replace(/\/$/, "");

export function safeImage(src: string | undefined, fallback: string): string {
  return src?.startsWith("/") ? src : fallback;
}

export function phoneHref(phone: string): string {
  return `tel:${phone.replace(/[^\d+]/g, "")}`;
}
