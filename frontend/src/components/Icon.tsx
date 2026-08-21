import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { name: string };

const paths: Record<string, React.ReactNode> = {
  phone: <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6A19.79 19.79 0 0 1 2.12 4.18 2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.12.9.33 1.78.62 2.63a2 2 0 0 1-.45 2.11L8 9.73a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.85.29 1.73.5 2.63.62A2 2 0 0 1 22 16.92Z" />,
  mail: <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></>,
  pin: <><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></>,
  clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
  arrow: <><path d="M5 12h14"/><path d="m14 7 5 5-5 5"/></>,
  check: <path d="m5 12 4 4L19 6" />,
  "shield-check": <><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-5"/></>,
  "file-chart": <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6M8 17v-3m4 3V9m4 8v-5"/></>,
  "house-heart": <><path d="m3 11 9-8 9 8"/><path d="M5 10v10h14V10"/><path d="M12 18s-4-2.2-4-4.5a2.2 2.2 0 0 1 4-1.3 2.2 2.2 0 0 1 4 1.3c0 2.3-4 4.5-4 4.5Z"/></>,
  "hard-hat": <><path d="M2 18h20M5 18v-2a7 7 0 0 1 14 0v2M9 9V5h6v4M12 5V2"/></>,
  building: <><rect x="4" y="3" width="16" height="19" rx="1"/><path d="M8 7h2m4 0h2M8 11h2m4 0h2M8 15h2m4 0h2M9 22v-3h6v3"/></>,
  users: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></>,
  headphones: <><path d="M4 14v-2a8 8 0 0 1 16 0v2"/><path d="M18 19c0 1.1-.9 2-2 2h-2M4 14h3v6H5a1 1 0 0 1-1-1Zm16 0h-3v6h2a1 1 0 0 0 1-1Z"/></>,
  smile: <><circle cx="12" cy="12" r="9"/><path d="M8 14s1.5 2 4 2 4-2 4-2M9 9h.01M15 9h.01"/></>,
  star: <path d="m12 2 3 6 6.5.9-4.7 4.6 1.1 6.5-5.9-3.1L6.1 20l1.1-6.5-4.7-4.6L9 8Z" />,
  menu: <><path d="M4 7h16M4 12h16M4 17h16"/></>,
  close: <><path d="m6 6 12 12M18 6 6 18"/></>,
  chevron: <path d="m9 18 6-6-6-6" />,
  whatsapp: <><path d="M20.5 11.6a8.5 8.5 0 0 1-12.6 7.5L3 20.5l1.4-4.7a8.5 8.5 0 1 1 16.1-4.2Z"/><path d="M8.3 8.2c.4 3.2 2 4.8 5.3 5.7l1.5-1.5 2 .9c-.2 2-1.4 2.8-3.2 2.7-4.4-.4-7.5-3.2-8-7.4-.2-1.8.7-3 2.6-3.3l1 2Z"/></>,
};

export function Icon({ name, ...props }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {paths[name] ?? paths.check}
    </svg>
  );
}
