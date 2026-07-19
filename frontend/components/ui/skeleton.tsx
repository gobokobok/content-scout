export function SkeletonLine({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-chip bg-border ${className}`} />;
}

export function SkeletonCard() {
  return (
    <div className="rounded-card border border-border bg-card p-4">
      <div className="mb-2 flex items-center gap-2">
        <SkeletonLine className="h-5 w-14" />
        <SkeletonLine className="h-4 w-28" />
      </div>
      <SkeletonLine className="mb-1.5 h-3 w-full" />
      <SkeletonLine className="mb-3 h-3 w-3/4" />
      <div className="flex gap-2">
        <SkeletonLine className="h-6 w-24" />
        <SkeletonLine className="h-6 w-20" />
      </div>
    </div>
  );
}

export function SkeletonList({ count = 4 }: { count?: number }) {
  return (
    <div className="flex flex-col gap-3">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}

export function SkeletonRow() {
  return (
    <div className="flex items-center gap-3 rounded-card border border-border bg-card px-4 py-3">
      <SkeletonLine className="h-4 flex-1" />
      <SkeletonLine className="h-7 w-20 shrink-0" />
      <SkeletonLine className="h-7 w-20 shrink-0" />
    </div>
  );
}

export function SkeletonRows({ count = 4 }: { count?: number }) {
  return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonRow key={i} />
      ))}
    </div>
  );
}
