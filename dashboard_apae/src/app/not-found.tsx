import Link from "next/link";
import { FileSearch } from "lucide-react";

export default function NotFound() {
  return (
    <section className="error-state">
      <span className="error-icon">
        <FileSearch size={30} />
      </span>
      <h2>Registro ou página não encontrado</h2>
      <p>Volte à visão geral para continuar a consulta.</p>
      <Link href="/" className="button primary">
        Voltar ao dashboard
      </Link>
    </section>
  );
}
