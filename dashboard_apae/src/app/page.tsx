import Link from "next/link";
import { ArrowRight, HeartHandshake, LockKeyhole } from "lucide-react";

export default function HomePage() {
  return (
    <main className="home-page" id="conteudo">
      <section className="home-card">
        <span className="home-symbol">
          <HeartHandshake size={38} />
        </span>
        <p className="eyebrow">APAE · CAPTAÇÃO DE RECURSOS</p>
        <h1>Sistema de Captação de Notas Fiscais</h1>
        <p className="home-description">
          Acompanhe os recebimentos, as notas fiscais e os contatos que apoiam o
          trabalho da APAE.
        </p>
        <Link className="button primary home-action" href="/login">
          Acessar o sistema <ArrowRight size={17} />
        </Link>
        <small>
          <LockKeyhole size={14} /> Acesso exclusivo para usuários autorizados
        </small>
      </section>
    </main>
  );
}
