"use client";

import Image from "next/image";
import { useState } from "react";
import { Icon } from "./Icon";

const tabs = [
  { label: "Качество", title: "Качество, за которое отвечаем", text: "Собственные проверенные бригады, контроль каждого этапа и понятные сроки выполнения работ.", image: "/images/sections/quality.webp", points: ["Проверенные специалисты", "Контроль результата", "Аккуратная работа"] },
  { label: "Прозрачность", title: "Каждый сом — под контролем", text: "Жители видят поступления, расходы и результаты работ. Отчётность доступна и понятна.", image: "/images/sections/transparency.webp", points: ["Регулярные отчёты", "Понятный единый тариф", "Открытый учёт"] },
  { label: "Комфорт", title: "Дом, в котором приятно жить", text: "Чистые подъезды и двор, рабочее освещение и своевременный ремонт общих зон.", image: "/images/sections/comfort.webp", points: ["Уборка территории", "Содержание подъездов", "Быстрая реакция"] },
];

export function WhyTabs() {
  const [active, setActive] = useState(0);
  const tab = tabs[active];
  return (
    <div className="why-panel">
      <div className="why-tabs" role="tablist" aria-label="Преимущества АВЛИ">
        {tabs.map((item, index) => <button key={item.label} id={`why-tab-${index}`} type="button" role="tab" aria-selected={active === index} aria-controls={`why-panel-${index}`} onClick={() => setActive(index)}>{item.label}</button>)}
      </div>
      <div className="why-content" id={`why-panel-${active}`} role="tabpanel" aria-labelledby={`why-tab-${active}`}>
        <div className="why-image"><Image src={tab.image} alt="" fill sizes="(max-width: 800px) 100vw, 50vw" /></div>
        <div className="why-copy">
          <h3>{tab.title}</h3>
          <p>{tab.text}</p>
          <ul>{tab.points.map((point) => <li key={point}><Icon name="check" width="18" height="18" />{point}</li>)}</ul>
          <a href="#callback" className="text-link">Обсудить управление домом <Icon name="arrow" width="18" height="18" /></a>
        </div>
      </div>
    </div>
  );
}
