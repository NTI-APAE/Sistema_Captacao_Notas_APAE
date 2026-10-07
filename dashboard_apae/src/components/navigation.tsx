"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  ArrowUpRight,
  HeartHandshake,
  LayoutDashboard,
  Menu,
  FileBarChart,
  ReceiptText,
  ShieldCheck,
  UsersRound,
  X,
} from "lucide-react";
import { LogoutButton } from "./logout-button";

const links = [
  { href: "/dashboard", label: "Visão geral", icon: LayoutDashboard },
  { href: "/dashboard/notas", label: "Notas fiscais", icon: ReceiptText },
  { href: "/dashboard/relatorios", label: "Relatórios", icon: FileBarChart },
  { href: "/dashboard/contatos", label: "Contatos", icon: UsersRound },
];

export function Navigation() {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  return (
    <>
      <div className="mobile-bar">
        <span>
          APAE <small>Captação de Recursos</small>
        </span>
        <button
          className="icon-button"
          aria-label={open ? "Fechar menu" : "Abrir menu"}
          aria-expanded={open}
          aria-controls="sidebar"
          onClick={() => setOpen(!open)}
        >
          {open ? <X /> : <Menu />}
        </button>
      </div>
      <aside id="sidebar" className={`sidebar ${open ? "is-open" : ""}`}>
        <Link
          className="brand"
          href="/dashboard"
          onClick={() => setOpen(false)}
        >
          <span className="brand-symbol">
            <HeartHandshake size={27} strokeWidth={1.5} />
          </span>
          <span>
            APAE<small>Captação de Recursos</small>
          </span>
        </Link>
        <div className="sidebar-divider" />
        <p className="nav-section">ACOMPANHAMENTO</p>
        <nav aria-label="Navegação principal">
          {links.map(({ href, label, icon: Icon }) => {
            const active =
              href === "/dashboard" ? path === href : path.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                prefetch={false}
                aria-current={active ? "page" : undefined}
                onClick={() => setOpen(false)}
              >
                <Icon size={19} strokeWidth={1.6} />
                <span>{label}</span>
                {active && <span className="nav-dot" />}
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-note">
          <HeartHandshake size={22} strokeWidth={1.5} />
          <p>
            Cada nota faz
            <br />
            <strong>a diferença.</strong>
          </p>
          <span>
            Uma visão mais próxima de
            <br />
            quem apoia a APAE.
          </span>
        </div>
        <div className="sidebar-bottom">
          <ShieldCheck size={17} />
          <div>
            Painel administrativo
            <small>Acesso restrito · somente consulta</small>
          </div>
          <ArrowUpRight size={14} />
        </div>
        <LogoutButton />
      </aside>
    </>
  );
}
