export function AuthCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-sidebar-gradient p-4">
      {/* Floating gradient orbs */}
      <div className="pointer-events-none absolute -left-24 -top-24 h-96 w-96 animate-float rounded-full bg-accent-500/40 blur-3xl" />
      <div
        className="pointer-events-none absolute -bottom-32 -right-16 h-[26rem] w-[26rem] animate-float rounded-full bg-brand-400/40 blur-3xl"
        style={{ animationDelay: "-3s" }}
      />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(49,46,129,.35)_100%)]" />

      <div className="relative w-full max-w-md animate-scale-in">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-white/15 text-2xl font-black text-white shadow-2xl ring-1 ring-white/30 backdrop-blur">
            Z
          </div>
          <p className="text-sm font-semibold uppercase tracking-widest text-white/70">
            Zilla Clinicals
          </p>
        </div>

        <div className="rounded-2xl border border-white/50 bg-white/95 p-8 shadow-2xl backdrop-blur-xl">
          <div className="mb-6 text-center">
            <h1 className="text-xl font-bold text-slate-800">{title}</h1>
            {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
          </div>
          {children}
        </div>

        <p className="mt-6 text-center text-xs text-white/60">
          Human Resource Management · Performance Reviews
        </p>
      </div>
    </div>
  );
}
