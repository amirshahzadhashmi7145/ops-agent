function formatJson(value: unknown) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function JsonPane({ title, value }: { title: string; value: unknown }) {
  return (
    <div className="min-w-0 flex-1">
      <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        {title}
      </p>
      <div className="max-h-[42vh] overflow-auto rounded-xl border border-border bg-muted/30 p-3">
        <pre className="whitespace-pre-wrap break-words font-mono text-xs leading-relaxed text-foreground/85 [overflow-wrap:anywhere]">
          {formatJson(value)}
        </pre>
      </div>
    </div>
  );
}
