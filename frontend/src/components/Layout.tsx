import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/useAuth";
import { ROLE_LABELS } from "../lib/permissions";
import { PhotoAvatar } from "./PhotoAvatar";
import { SessionTimeout } from "./SessionTimeout";
import type { Role } from "../shared/types";
import {
  IconAnalytics,
  IconAudit,
  IconCycles,
  IconDashboard,
  IconEmployees,
  IconGoals,
  IconKpis,
  IconReviews,
  IconSelf,
  IconSurveys,
} from "./icons";

type IconCmp = (p: { className?: string }) => React.ReactNode;

interface NavItem {
  to: string;
  label: string;
  icon: IconCmp;
  roles?: Role[];
}

const NAV: NavItem[] = [
  { to: "/", label: "Dashboard", icon: IconDashboard },
  { to: "/goals", label: "My Goals", icon: IconGoals },
  { to: "/self-assessment", label: "Self-Assessment", icon: IconSelf },
  { to: "/surveys", label: "Surveys", icon: IconSurveys },
  {
    to: "/reviews",
    label: "My Reviews",
    icon: IconReviews,
    roles: ["manager", "hr", "executive", "admin"],
  },
  {
    to: "/employees",
    label: "Employees",
    icon: IconEmployees,
    roles: ["manager", "hr", "executive", "admin"],
  },
  { to: "/kpis", label: "KPIs", icon: IconKpis, roles: ["hr", "executive", "admin"] },
  { to: "/cycles", label: "Review Cycles", icon: IconCycles, roles: ["hr", "executive", "admin"] },
  { to: "/analytics", label: "Analytics", icon: IconAnalytics, roles: ["hr", "executive", "admin"] },
  { to: "/audit", label: "Audit Log", icon: IconAudit, roles: ["hr", "executive", "admin"] },
];

function initials(name?: string | null, email?: string) {
  const src = (name || email || "?").trim();
  const parts = src.split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return src.slice(0, 2).toUpperCase();
}

export function Layout() {
  const { me, signOut, hasRole } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const onSignOut = async () => {
    await signOut();
    navigate("/login");
  };

  const items = NAV.filter((n) => !n.roles || hasRole(...n.roles));
  const displayName = me?.employee?.full_name ?? me?.user.email ?? "";
  const roleLabel = me ? ROLE_LABELS[me.user.role] : "";

  return (
    <div className="flex min-h-screen">
      <SessionTimeout />
      {/* Sidebar — sticky full-height so it stays put while the main area scrolls */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col self-start overflow-y-auto bg-sidebar-gradient text-white md:flex">
        <div className="flex items-center gap-3 px-5 py-5">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-white/15 text-lg font-black shadow-inner ring-1 ring-white/25 backdrop-blur">
            Z
          </div>
          <div>
            <p className="text-sm font-bold leading-tight">Zilla Clinicals</p>
            <p className="text-[11px] font-medium text-white/60">HR Management</p>
          </div>
        </div>

        <nav className="flex-1 space-y-1 px-3 py-2">
          {items.map((n) => {
            const Icon = n.icon;
            return (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === "/"}
                className={({ isActive }) =>
                  `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? "bg-white/15 text-white shadow-inner ring-1 ring-white/20"
                      : "text-white/70 hover:bg-white/10 hover:text-white"
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon
                      className={`h-5 w-5 shrink-0 transition-transform duration-200 group-hover:scale-110 ${
                        isActive ? "text-white" : "text-white/70"
                      }`}
                    />
                    <span>{n.label}</span>
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>

        <div className="m-3 rounded-xl bg-white/10 p-4 ring-1 ring-white/15">
          <p className="text-xs font-semibold text-white">Twice-yearly reviews</p>
          <p className="mt-1 text-[11px] leading-relaxed text-white/60">
            Self-assessment + manager review, scored to 100.
          </p>
        </div>
      </aside>

      {/* Main column */}
      <div className="flex flex-1 flex-col">
        <header className="glass sticky top-0 z-20 flex items-center justify-between border-b px-5 py-3">
          <div className="flex items-center gap-2 md:hidden">
            <div className="grid h-8 w-8 place-items-center rounded-lg bg-brand-gradient text-sm font-black text-white">
              Z
            </div>
            <span className="font-bold text-slate-800">Zilla HRM</span>
          </div>

          <div className="ml-auto flex items-center gap-3">
            <div className="hidden text-right sm:block">
              <p className="text-sm font-semibold text-slate-800">{displayName}</p>
              <p className="text-xs capitalize text-slate-400">{roleLabel}</p>
            </div>
            {me?.employee ? (
              <PhotoAvatar
                employeeId={me.employee.id}
                hasPhoto={me.employee.has_photo}
                className="h-9 w-9 rounded-full bg-brand-gradient shadow-glow-sm ring-2 ring-white"
                iconClassName="h-5 w-5 text-white"
              />
            ) : (
              <div className="grid h-9 w-9 place-items-center rounded-full bg-brand-gradient text-xs font-bold text-white shadow-glow-sm ring-2 ring-white">
                {initials(me?.employee?.full_name, me?.user.email)}
              </div>
            )}
            <div className="mx-1 hidden h-6 w-px bg-slate-200 sm:block" />
            <NavLink to="/settings" className="btn-secondary px-3 py-1.5 text-xs">
              Settings
            </NavLink>
            <button onClick={onSignOut} className="btn-secondary px-3 py-1.5 text-xs">
              Sign out
            </button>
          </div>
        </header>

        <main className="flex-1 p-5 md:p-8">
          <div key={location.pathname} className="page-enter">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
