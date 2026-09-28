"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { RefreshCw } from "lucide-react";

export function RefreshButton({
  label = "Atualizar dados",
}: {
  label?: string;
}) {
  const router = useRouter();
  const [pending, start] = useTransition();
  return (
    <button
      className="button secondary"
      disabled={pending}
      onClick={() => start(() => router.refresh())}
      aria-live="polite"
    >
      <RefreshCw size={15} className={pending ? "spin" : ""} />
      {pending ? "Atualizando…" : label}
    </button>
  );
}
