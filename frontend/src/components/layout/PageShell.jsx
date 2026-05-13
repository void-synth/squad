/**
 * Standard page width + padding. Use for every route so layout stays consistent.
 */
const MAX = {
  narrow: "max-w-3xl",
  default: "max-w-5xl",
  wide: "max-w-[1600px]",
};

export default function PageShell({ title, description, variant = "default", className = "", children }) {
  const max = MAX[variant] ?? MAX.default;
  return (
    <div className={`mx-auto flex w-full flex-1 flex-col px-4 py-6 sm:px-6 sm:py-8 ${max} ${className}`.trim()}>
      {title || description ? (
        <header className="border-default-200/80 mb-6 border-b pb-5">
          {title ? <h1 className="text-default-foreground text-xl font-bold tracking-tight sm:text-2xl">{title}</h1> : null}
          {description ? <p className="text-default-500 mt-1 max-w-2xl text-sm leading-relaxed">{description}</p> : null}
        </header>
      ) : null}
      {children}
    </div>
  );
}
