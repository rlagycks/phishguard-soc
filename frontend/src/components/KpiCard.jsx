import { Icon } from "./Icon.jsx";

export function KpiCard({ icon, label, value, sub, tone = "accent" }) {
  return (
    <section className={`card kpi-card accent-${tone}`}>
      <div className="kpi-top">
        <span>{label}</span>
        <div className="kpi-icon"><Icon name={icon} size={16} /></div>
      </div>
      <div className="kpi-value">
        <strong className="mono">{value}</strong>
        {sub && <small>{sub}</small>}
      </div>
    </section>
  );
}
