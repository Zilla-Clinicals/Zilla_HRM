// Minimal 24x24 stroke icons (currentColor). Kept inline to avoid a dependency.
type P = { className?: string };

const base = (className?: string) => ({
  className,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
});

export function IconDashboard({ className }: P) {
  return (
    <svg {...base(className)}>
      <path d="M3 13h8V3H3v10Zm10 8h8V3h-8v18ZM3 21h8v-6H3v6Z" />
    </svg>
  );
}
export function IconSelf({ className }: P) {
  return (
    <svg {...base(className)}>
      <path d="M9 11l3 3L22 4" />
      <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
    </svg>
  );
}
export function IconReviews({ className }: P) {
  return (
    <svg {...base(className)}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6M9 15l2 2 4-4" />
    </svg>
  );
}
export function IconEmployees({ className }: P) {
  return (
    <svg {...base(className)}>
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13A4 4 0 0 1 16 11" />
    </svg>
  );
}
export function IconKpis({ className }: P) {
  return (
    <svg {...base(className)}>
      <path d="M12 2l3 6.9 7.6.6-5.8 5 1.8 7.4L12 18l-6.4 3.9 1.8-7.4-5.8-5 7.6-.6L12 2Z" />
    </svg>
  );
}
export function IconCycles({ className }: P) {
  return (
    <svg {...base(className)}>
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M16 2v4M8 2v4M3 10h18" />
    </svg>
  );
}
export function IconAnalytics({ className }: P) {
  return (
    <svg {...base(className)}>
      <path d="M3 3v18h18" />
      <path d="M7 14l3-3 3 3 5-6" />
    </svg>
  );
}
export function IconGoals({ className }: P) {
  return (
    <svg {...base(className)}>
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" />
      <circle cx="12" cy="12" r="1.5" />
    </svg>
  );
}
export function IconSurveys({ className }: P) {
  return (
    <svg {...base(className)}>
      <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
      <rect x="9" y="3" width="6" height="4" rx="1" />
      <path d="M9 12l1.5 1.5L13 11M9 17h5" />
    </svg>
  );
}
export function IconUser({ className }: P) {
  return (
    <svg {...base(className)}>
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}
export function IconAudit({ className }: P) {
  return (
    <svg {...base(className)}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <path d="M14 2v6h6M9 13h6M9 17h6M9 9h1" />
    </svg>
  );
}
