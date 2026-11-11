"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";

export default function ShellError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-[40vh] flex-col items-center justify-center gap-3 px-5 text-center">
      <h2 className="text-lg font-medium text-foreground">This page failed to load</h2>
      <p className="max-w-md text-sm text-muted-foreground">
        Check the API is up, then retry. Your other tabs should still work.
      </p>
      <Button type="button" onClick={reset}>
        Retry
      </Button>
    </div>
  );
}
