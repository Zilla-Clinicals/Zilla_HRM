export function LoadingSpinner({ full = false }: { full?: boolean }) {
  const spinner = (
    <span className="relative inline-flex h-8 w-8" role="status" aria-label="Loading">
      <span className="absolute inset-0 animate-ping rounded-full bg-brand-400/30" />
      <span className="h-8 w-8 animate-spin rounded-full border-[3px] border-brand-100 border-t-brand-600" />
    </span>
  );
  if (full) {
    return (
      <div className="flex h-full min-h-[60vh] items-center justify-center">{spinner}</div>
    );
  }
  return spinner;
}
