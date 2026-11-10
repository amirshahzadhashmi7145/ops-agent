import { Construction } from "lucide-react";

export function PlaceholderPage({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="flex min-h-full w-full flex-col justify-center px-5 py-10">
      <div className="surface-card flex flex-col items-center px-6 py-10 text-center">
        <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Construction className="h-5 w-5" />
        </div>
        <h2 className="page-header">{title}</h2>
        <p className="page-description max-w-md">{description}</p>
      </div>
    </div>
  );
}
