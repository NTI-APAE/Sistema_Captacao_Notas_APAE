"use client";
import { CircleAlert } from "lucide-react";

export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <section className="error-state" role="alert">
      <span className="error-icon">
        <CircleAlert size={30} />
      </span>
      <h2>Não foi possível abrir esta página</h2>
      <p>
        Tente novamente. Se o problema continuar, entre em contato com o
        responsável pelo sistema.
      </p>
      <button className="button primary" onClick={reset}>
        Tentar novamente
      </button>
    </section>
  );
}
