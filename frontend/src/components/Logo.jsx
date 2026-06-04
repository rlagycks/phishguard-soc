import { Icon } from "./Icon.jsx";

export function Logo({ size = 34 }) {
  return (
    <div className="logo-mark" style={{ width: size, height: size, borderRadius: Math.max(8, size * 0.26) }}>
      <Icon name="shield" size={size * 0.58} />
    </div>
  );
}
