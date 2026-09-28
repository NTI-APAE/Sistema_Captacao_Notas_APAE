import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { ShieldCheck, ChevronRight } from "lucide-react";
import { Navigation } from "@/components/navigation";
import { requestAuth } from "@/lib/auth-transport";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const cookieName = process.env.DASHBOARD_SESSION_COOKIE ?? "apae_session";
  const session = (await cookies()).get(cookieName)?.value;
  if (!session) redirect("/login?next=/dashboard");

  const apiUrl = process.env.NOTAS_API_URL ?? "http://127.0.0.1:8000";
  const identity = await requestAuth(apiUrl, "me", {
    cookie: `${cookieName}=${session}`,
  });
  if (!identity.ok || !identity.data.scopes.includes("dashboard:read")) {
    redirect("/login?next=/dashboard");
  }

  return (
    <>
      <Navigation />
      <div className="workspace">
        <header className="topbar">
          <div>
            APAE <ChevronRight size={13} /> <span>Captação de Recursos</span>
          </div>
          <span className="readonly">
            <ShieldCheck size={14} /> Somente consulta
          </span>
        </header>
        <main id="conteudo">{children}</main>
        <footer className="app-footer">
          <span>APAE · Captação de Recursos</span>
          <span>Horário de Brasília · Informações protegidas</span>
        </footer>
      </div>
    </>
  );
}
