export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-bg p-4">
      <div className="w-full max-w-sm rounded-card border border-border bg-card p-8 shadow-sm">
        {children}
      </div>
    </main>
  );
}
