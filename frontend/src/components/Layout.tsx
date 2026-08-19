import { useEffect, useState } from "react";
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
  const [mobileOpen, setMobileOpen] = useState(false);

  const onSignOut = async () => {
    await signOut();
    navigate("/login");
  };

  // Close the mobile drawer on navigation so tapping a link takes you there.
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  // While the drawer is open, close on Escape and lock background scroll.
  useEffect(() => {
    if (!mobileOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMobileOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [mobileOpen]);

  const items = NAV.filter((n) => !n.roles || hasRole(...n.roles));
  const displayName = me?.employee?.full_name ?? me?.user.email ?? "";
  const roleLabel = me ? ROLE_LABELS[me.user.role] : "";

  // Sidebar contents, shared by the desktop rail and the mobile drawer.
  // `onClose` is passed only for the drawer, which then shows a close button.
  const renderSidebar = (onClose?: () => void) => (
    <>
      <div className="flex items-center gap-3 px-5 py-5">
        <div className="grid h-10 w-10 place-items-center rounded-xl bg-white/15 text-lg font-black shadow-inner ring-1 ring-white/25 backdrop-blur">
          Z
        </div>
        <div>
          <p className="text-sm font-bold leading-tight">Zilla Clinicals</p>
          <p className="text-[11px] font-medium text-white/60">HR Management</p>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Close menu"
            className="ml-auto grid h-8 w-8 place-items-center rounded-lg text-white/70 hover:bg-white/10 hover:text-white"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        )}
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
    </>
  );

  return (
    <div className="flex min-h-screen">
      <SessionTimeout />
      {/* Desktop sidebar — sticky full-height so it stays put while the main area scrolls */}
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col self-start overflow-y-auto bg-sidebar-gradient text-white md:flex">
        {renderSidebar()}
      </aside>

      {/* Mobile drawer + backdrop (always mounted so it can animate; ignored on md+) */}
      <div
        className={`fixed inset-0 z-40 md:hidden ${mobileOpen ? "" : "pointer-events-none"}`}
        aria-hidden={!mobileOpen}
      >
        <div
          className={`absolute inset-0 bg-slate-900/50 backdrop-blur-sm transition-opacity duration-300 ${
            mobileOpen ? "opacity-100" : "opacity-0"
          }`}
          onClick={() => setMobileOpen(false)}
        />
        <aside
          role="dialog"
          aria-modal="true"
          aria-label="Main menu"
          className={`absolute inset-y-0 left-0 flex w-64 max-w-[82%] flex-col overflow-y-auto bg-sidebar-gradient text-white shadow-2xl transition-transform duration-300 ease-out ${
            mobileOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          {renderSidebar(() => setMobileOpen(false))}
        </aside>
      </div>

      {/* Main column */}
      <div className="flex flex-1 flex-col">
        <header className="glass sticky top-0 z-20 flex items-center justify-between border-b px-5 py-3">
          <div className="flex items-center gap-2 md:hidden">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              aria-label="Open menu"
              aria-expanded={mobileOpen}
              className="grid h-9 w-9 place-items-center rounded-lg text-slate-600 hover:bg-slate-100"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
                <path d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
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
