import type { Metadata } from "next";
import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Entrar" };
export default function LoginPage() {
  return (
    <div className="login-page">
      <LoginForm />
    </div>
  );
}
