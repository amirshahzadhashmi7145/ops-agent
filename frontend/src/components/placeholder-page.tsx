import { Construction } from "lucide-react";

export function PlaceholderPage({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="mx-auto flex min-h-full max-w-6xl flex-col justify-center px-8 py-16">
      <div className="surface-card flex flex-col items-center px-8 py-16 text-center">
        <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <Construction className="h-7 w-7" />
        </div>
        <h2 className="page-header">{title}</h2>
        <p className="page-description max-w-md">{description}</p>
      </div>
    </div>
  );
}
