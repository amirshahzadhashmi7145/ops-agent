export function OpsLogo({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 64 64"
      role="img"
      aria-label="Ops Agent"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="ops-logo-gradient" x1="8" y1="8" x2="56" y2="56" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#4F46E5" />
          <stop offset="1" stopColor="#06B6D4" />
        </linearGradient>
      </defs>
      <rect x="4" y="4" width="56" height="56" rx="14" fill="url(#ops-logo-gradient)" />
      <path
        d="M20 42a12 12 0 1 1 24 0 12 12 0 0 1-24 0zm12-8a8 8 0 1 0 0 16 8 8 0 0 0 0-16z"
        fill="#FFFFFF"
        fillRule="evenodd"
      />
    </svg>
  );
}
