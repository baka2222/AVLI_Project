"use client";

import { type FormEvent, useState } from "react";

type CallbackState = {
  status: "idle" | "success" | "error";
  message: string;
};

type CallbackResponse = {
  ok?: boolean;
  saved?: boolean;
  id?: number;
  message?: string;
};

const initialCallbackState: CallbackState = { status: "idle", message: "" };

export function CallbackForm({ page = "Сайт" }: { page?: string }) {
  const [state, setState] = useState<CallbackState>(initialCallbackState);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 8000);

    setPending(true);
    setState(initialCallbackState);

    try {
      const response = await fetch("/api/v1/site/callback/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: String(formData.get("name") || "").trim().slice(0, 120),
          phone: String(formData.get("phone") || "").trim(),
          message: String(formData.get("message") || "").trim().slice(0, 2000),
          page: String(formData.get("page") || "").trim().slice(0, 320),
          contactTime: String(formData.get("contactTime") || "").trim(),
          privacyAccepted: formData.get("privacy") === "on",
        }),
        cache: "no-store",
        signal: controller.signal,
      });
      const result = (await response.json().catch(() => ({}))) as CallbackResponse;
      const wasSaved = response.ok
        && result.ok === true
        && result.saved === true
        && Number.isInteger(result.id)
        && Number(result.id) > 0;

      if (!wasSaved) {
        setState({ status: "error", message: result.message || "Не удалось отправить заявку. Позвоните нам напрямую." });
        return;
      }

      form.reset();
      setState({ status: "success", message: `Спасибо! Заявка №${result.id} сохранена. Мы свяжемся с вами в рабочее время.` });
    } catch {
      setState({ status: "error", message: "Сервис временно недоступен. Пожалуйста, позвоните нам напрямую." });
    } finally {
      window.clearTimeout(timeout);
      setPending(false);
    }
  }

  if (state.status === "success") {
    return <div className="form-success" role="status" aria-live="polite"><span>✓</span><strong>Заявка отправлена</strong><p>{state.message}</p></div>;
  }

  return (
    <form className="callback-form" aria-busy={pending} onSubmit={handleSubmit}>
      <input type="hidden" name="page" value={page} />
      <div className="honeypot" aria-hidden="true">
        <label>
          Дополнительное поле
          <input
            name="contactTime"
            tabIndex={-1}
            autoComplete="off"
            data-1p-ignore="true"
            data-lpignore="true"
            data-form-type="other"
          />
        </label>
      </div>
      <label>
        Ваше имя
        <input name="name" type="text" maxLength={120} autoComplete="name" placeholder="Как к вам обращаться" />
      </label>
      <label>
        Номер телефона <span aria-hidden="true">*</span>
        <input name="phone" type="tel" required maxLength={30} autoComplete="tel" inputMode="tel" placeholder="+996 ___ ___ ___" />
      </label>
      <label className="form-message">
        Комментарий
        <textarea name="message" maxLength={2000} rows={3} placeholder="Коротко опишите ваш вопрос" />
      </label>
      <label className="privacy-check">
        <input name="privacy" type="checkbox" required />
        <span>Согласен(на) на обработку контактных данных для ответа на заявку.</span>
      </label>
      {state.status === "error" && <p className="form-error" role="alert">{state.message}</p>}
      <button className="button button-primary" type="submit" disabled={pending}>{pending ? "Отправляем…" : "Отправить заявку"}</button>
    </form>
  );
}
