"use client";

import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { LockKeyhole, LogIn } from "lucide-react";

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const data = new FormData(event.currentTarget);
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: data.get("email"),
        senha: data.get("senha"),
      }),
    });
    if (!response.ok) {
      setLoading(false);
      setError(
        response.status === 401
          ? "E-mail ou senha inválidos."
          : response.status === 403
            ? "Este usuário não tem acesso ao painel."
            : "Não foi possível entrar. Tente novamente.",
      );
      return;
    }
    const next = params.get("next");
    router.replace(
      next?.startsWith("/dashboard") && !next.startsWith("//")
        ? next
        : "/dashboard",
    );
    router.refresh();
  }
  return (
    <form className="login-form" onSubmit={submit}>
      <span className="login-icon">
        <LockKeyhole size={28} />
      </span>
      <p className="eyebrow">ACESSO ADMINISTRATIVO</p>
      <h1>Entrar no painel</h1>
      <p>Use seu e-mail e senha de operador da APAE.</p>
      <label>
        E-mail
        <input
          name="email"
          type="email"
          required
          autoComplete="username"
          maxLength={254}
        />
      </label>
      <label>
        Senha
        <input
          name="senha"
          type="password"
          required
          autoComplete="current-password"
          minLength={8}
          maxLength={200}
        />
      </label>
      {error && (
        <p className="login-error" role="alert">
          {error}
        </p>
      )}
      <button className="button primary" disabled={loading}>
        <LogIn size={16} />
        {loading ? "Entrando…" : "Entrar"}
      </button>
      <small>
        Sessão protegida e acesso somente para usuários autorizados.
      </small>
    </form>
  );
}
