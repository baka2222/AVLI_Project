import type { SiteSettings } from "@/lib/site";
import { phoneHref } from "@/lib/site";
import { CallbackForm } from "./CallbackForm";
import { Icon } from "./Icon";

export function CallbackSection({ settings }: { settings: SiteSettings }) {
  return (
    <section className="callback-section" id="callback" aria-labelledby="callback-title">
      <div className="container callback-grid">
        <div>
          <span className="eyebrow light">Остались вопросы?</span>
          <h2 id="callback-title">Расскажем, как сделать управление домом понятным</h2>
          <p>Оставьте номер — специалист АВЛИ перезвонит, ответит на вопросы и предложит следующий шаг.</p>
          <a className="callback-phone" href={phoneHref(settings.phonePrimary)}><Icon name="phone" width="23" height="23" />{settings.phonePrimary}</a>
        </div>
        <div className="callback-card">
          <CallbackForm page="Общая форма сайта" />
        </div>
      </div>
    </section>
  );
}
