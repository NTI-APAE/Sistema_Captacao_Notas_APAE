import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Sistema de Captação de Notas Fiscais · APAE",
    template: "%s · APAE",
  },
  description: "Painel administrativo de captação de notas fiscais da APAE.",
  robots: { index: false, follow: false },
};
export const dynamic = "force-dynamic";

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>
        <a href="#conteudo" className="skip-link">
          Ir para o conteúdo
        </a>
        {children}
      </body>
    </html>
  );
}
