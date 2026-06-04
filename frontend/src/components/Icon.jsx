import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  Check,
  Clock,
  Cpu,
  Eye,
  Filter,
  Grid2X2,
  Link,
  List,
  LogOut,
  Mail,
  RefreshCw,
  Search,
  ShieldCheck,
  ShieldX,
  X
} from "lucide-react";

const ICONS = {
  activity: Activity,
  alert: AlertTriangle,
  chart: BarChart3,
  bell: Bell,
  check: Check,
  clock: Clock,
  cpu: Cpu,
  eye: Eye,
  filter: Filter,
  grid: Grid2X2,
  link: Link,
  list: List,
  logout: LogOut,
  mail: Mail,
  refresh: RefreshCw,
  search: Search,
  shield: ShieldCheck,
  quarantine: ShieldX,
  x: X
};

export function Icon({ name, size = 18, ...props }) {
  const Component = ICONS[name] || ShieldCheck;
  return <Component size={size} strokeWidth={1.8} {...props} />;
}
