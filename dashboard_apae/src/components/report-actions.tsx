"use client";

import { Download, Printer } from "lucide-react";
import { dateTime, statusLabel } from "@/lib/format";
import type { Note } from "@/lib/types";

function csvValue(value: string | number | null): string {
  const text = value === null ? "" : String(value);
  return `"${text.replaceAll('"', '""')}"`;
}

export function ReportActions({ items }: { items: Note[] }) {
  function printReport() {
    window.print();
  }

  function downloadCsv() {
    const headers = [
      "Recebimento",
      "Contato",
      "Telefone mascarado",
      "Chave mascarada",
      "Submissão",
      "Cadastro fiscal",
      "Origem",
      "Instância",
    ];
    const rows = items.map((item) => [
      dateTime(item.data_recebimento),
      item.nome || "Sem nome informado",
      item.telefone,
      item.chave,
      statusLabel(item.status),
      statusLabel(item.cadastro || ""),
      statusLabel(item.origem),
      item.whatsapp_instance,
    ]);
    const csv = [headers, ...rows]
      .map((row) => row.map((value) => csvValue(value)).join(";"))
      .join("\r\n");
    const blob = new Blob([`\uFEFF${csv}`], {
      type: "text/csv;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `relatorio-notas-${new Date().toISOString().slice(0, 10)}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="report-actions">
      <button className="button secondary" type="button" onClick={printReport}>
        <Printer size={15} />
        Imprimir
      </button>
      <button
        className="button primary"
        type="button"
        onClick={downloadCsv}
        disabled={!items.length}
      >
        <Download size={15} />
        Exportar CSV
      </button>
    </div>
  );
}
