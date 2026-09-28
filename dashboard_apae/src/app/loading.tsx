export default function Loading() {
  return (
    <div className="loading-state" role="status" aria-label="Carregando dados">
      <div className="skeleton skeleton-title" />
      <div className="skeleton skeleton-description" />
      <div className="metric-grid">
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} className="skeleton skeleton-card" />
        ))}
      </div>
      <div className="skeleton skeleton-chart" />
      <p>Carregando informações da operação…</p>
    </div>
  );
}
