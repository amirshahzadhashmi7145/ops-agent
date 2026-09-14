export function NexarLogo({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 64 64"
      role="img"
      aria-label="Nexar logo"
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="nexar-logo-gradient" x1="8" y1="8" x2="56" y2="56" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#4F46E5" />
          <stop offset="1" stopColor="#06B6D4" />
        </linearGradient>
      </defs>
      <rect x="4" y="4" width="56" height="56" rx="14" fill="url(#nexar-logo-gradient)" />
      <path
        d="M18 44V20h4l20 24h-4L22 24v20h-4zm28 0V20h4v24h-4z"
        fill="#FFFFFF"
        fillRule="evenodd"
        clipRule="evenodd"
      />
    </svg>
  );
}
