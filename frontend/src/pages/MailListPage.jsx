import { useEffect, useMemo, useState } from "react";
import { fetchEmails } from "../api/client.js";
import { EmailTable } from "../components/EmailTable.jsx";
import { Icon } from "../components/Icon.jsx";

const FILTERS = [
  ["all", "전체"],
  ["quarantined", "격리"],
  ["needs_review", "검토"],
  ["normal", "정상"]
];

export function MailListPage({ onSelect }) {
  const [emails, setEmails] = useState([]);
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("final");

  useEffect(() => {
    fetchEmails({ limit: 120 }).then(setEmails);
  }, []);

  const rows = useMemo(() => {
    return emails
      .filter((email) => filter === "all" || email.status === filter)
      .filter((email) => !query || `${email.subject} ${email.sender}`.toLowerCase().includes(query.toLowerCase()))
      .sort((a, b) => sort === "final" ? b.finalScore - a.finalScore : new Date(b.receivedAt) - new Date(a.receivedAt));
  }, [emails, filter, query, sort]);

  return (
    <div className="list-page">
      <div className="list-toolbar">
        <div className="segmented">
          {FILTERS.map(([key, label]) => (
            <button className={filter === key ? "active" : ""} key={key} onClick={() => setFilter(key)}>{label}</button>
          ))}
        </div>
        <label className="search-box">
          <Icon name="search" size={16} />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="제목·발신자 검색" />
        </label>
        <button className="btn sm" onClick={() => setSort(sort === "final" ? "time" : "final")}>
          <Icon name="filter" size={14} />정렬: {sort === "final" ? "위험도순" : "최신순"}
        </button>
      </div>
      <section className="card table-card">
        <EmailTable emails={rows} onSelect={onSelect} />
      </section>
    </div>
  );
}
