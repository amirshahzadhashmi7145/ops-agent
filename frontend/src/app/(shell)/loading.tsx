export default function ShellLoading() {
  return (
    <div className="mx-auto max-w-6xl animate-pulse px-8 py-10">
      <div className="mb-8 space-y-3">
        <div className="h-8 w-48 rounded-lg bg-muted/60" />
        <div className="h-4 w-full max-w-xl rounded-md bg-muted/40" />
      </div>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row">
        <div className="h-10 flex-1 rounded-lg bg-muted/50" />
        <div className="h-10 w-full rounded-lg bg-muted/50 sm:w-44" />
      </div>
      <div className="surface-card space-y-3 p-6">
        {Array.from({ length: 5 }).map((_, index) => (
          <div key={index} className="h-12 rounded-lg bg-muted/60" />
        ))}
      </div>
    </div>
  );
}
