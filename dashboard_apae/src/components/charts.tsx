"use client";

import { useState } from "react";
import { CalendarDays } from "lucide-react";
import type { Summary } from "@/lib/types";
import { dateTime, number, statusLabel } from "@/lib/format";
import { EmptyState } from "./ui";

export function ReceiptsChart({ series }: { series: Summary["series"] }) {
  const [selected, select] = useState(series.length - 1);
  const max = Math.max(
    2,
    Math.ceil(Math.max(0, ...series.map((item) => item.total)) / 2) * 2,
  );
  const current = series[selected];
  return (
    <>
      <div className="chart-toolbar">
        <span className="chart-legend">
          <i />
          Submissões recebidas
        </span>
        <span className="period-chip">
          <CalendarDays size={13} />
          Últimos 30 dias
        </span>
      </div>
      <div className="chart-value">
        <strong>
          {number(series.reduce((sum, item) => sum + item.total, 0))}
        </strong>
        <span>recebimentos no período</span>
        <output>
          {current
            ? `${dateTime(current.dia)} · ${number(current.total)} recebimento(s)`
            : "Sem registros"}
        </output>
      </div>
      <div className="chart-scroll">
        <svg
          viewBox="0 0 800 218"
          className="receipts-chart"
          role="group"
          aria-label="Recebimentos por dia; use Tab para consultar cada barra"
        >
          {[0, 0.5, 1].map((fraction) => (
            <g key={fraction}>
              <line
                x1="35"
                x2="785"
                y1={174 - fraction * 150}
                y2={174 - fraction * 150}
                stroke="#e8eeeb"
                strokeDasharray="3 5"
              />
              <text
                x="23"
                y={178 - fraction * 150}
                textAnchor="end"
                className="chart-tick"
              >
                {number(Math.ceil(max * fraction))}
              </text>
            </g>
          ))}
          {series.map((item, i) => {
            const x = 43 + i * 24.7;
            const height = (item.total / max) * 150;
            return (
              <g key={item.dia}>
                <rect
                  x={x}
                  y={174 - Math.max(height, 2)}
                  width="13"
                  height={Math.max(height, 2)}
                  rx="3"
                  className={selected === i ? "bar selected" : "bar"}
                  tabIndex={0}
                  role="button"
                  aria-label={`${dateTime(item.dia)}: ${item.total} recebimentos`}
                  aria-pressed={selected === i}
                  onMouseEnter={() => select(i)}
                  onFocus={() => select(i)}
                  onClick={() => select(i)}
                  onKeyDown={(event) => {
                    if (["Enter", " "].includes(event.key)) {
                      event.preventDefault();
                      select(i);
                    }
                  }}
                >
                  <title>
                    {dateTime(item.dia)}: {item.total}
                  </title>
                </rect>
                {(i % 6 === 0 || i === series.length - 1) && (
                  <text
                    x={x + 7}
                    y="203"
                    textAnchor="middle"
                    className="chart-tick"
                  >
                    {item.dia.slice(8)}/{item.dia.slice(5, 7)}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>
      <details className="chart-data">
        <summary>Consultar dados em tabela</summary>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Data</th>
                <th>Recebimentos</th>
              </tr>
            </thead>
            <tbody>
              {series.map((item) => (
                <tr key={item.dia}>
                  <td>{dateTime(item.dia)}</td>
                  <td>{number(item.total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  );
}

export function StatusChart({
  submissions,
  notes,
}: {
  submissions: Summary["status_submissoes"];
  notes: Summary["status_notas"];
}) {
  const [mode, setMode] = useState<"submissions" | "notes">("submissions");
  const rows = mode === "submissions" ? submissions : notes;
  const total = rows.reduce((sum, item) => sum + item[1], 0);
  const colors = [
    "#36795e",
    "#c59547",
    "#93b4a1",
    "#7a8fa6",
    "#ac746e",
    "#bdc8c0",
    "#576d5f",
  ];
  return (
    <>
      <div className="segmented" role="group" aria-label="Tipo de distribuição">
        <button
          aria-pressed={mode === "submissions"}
          onClick={() => setMode("submissions")}
        >
          Submissões
        </button>
        <button
          aria-pressed={mode === "notes"}
          onClick={() => setMode("notes")}
        >
          Cadastro fiscal
        </button>
      </div>
      {total ? (
        <>
          <div className="status-total">
            <strong>{number(total)}</strong>
            <span>
              {mode === "submissions"
                ? "submissões registradas"
                : "notas fiscais únicas"}
            </span>
          </div>
          <div className="stacked-bar" aria-hidden="true">
            {rows.map(([status, amount], i) => (
              <span
                key={status}
                style={{
                  width: `${(amount / total) * 100}%`,
                  background: colors[i % colors.length],
                }}
              />
            ))}
          </div>
          <div className="status-list">
            {rows.map(([status, amount], i) => (
              <div key={status}>
                <span>
                  <i style={{ background: colors[i % colors.length] }} />
                  {statusLabel(status)}
                </span>
                <strong>
                  {number(amount)}
                  <small>{Math.round((amount / total) * 100)}%</small>
                </strong>
              </div>
            ))}
          </div>
          <p className="chart-caption">Distribuição de todo o histórico.</p>
        </>
      ) : (
        <EmptyState
          title="Sem registros"
          description="A distribuição aparecerá após os primeiros registros."
        />
      )}
    </>
  );
}
