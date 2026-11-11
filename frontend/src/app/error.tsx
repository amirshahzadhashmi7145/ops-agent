"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";

export default function GlobalError({
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
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3 px-5 text-center">
      <h2 className="text-lg font-medium text-foreground">Something went wrong</h2>
      <p className="max-w-md text-sm text-muted-foreground">
        The page hit an unexpected error. You can try again without losing the rest of the app.
      </p>
      <Button type="button" onClick={reset}>
        Try again
      </Button>
    </div>
  );
}
