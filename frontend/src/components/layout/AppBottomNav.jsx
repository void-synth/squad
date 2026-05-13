import { NavLink } from "react-router-dom";
import { Notification, SecuritySafe } from "../../icons/isax.jsx";

function DockItem({ to, end, icon: Icon, label }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        [
          "relative flex min-w-[5rem] flex-col items-center justify-center gap-0.5 rounded-2xl px-3 py-2 no-underline transition-all duration-200 ease-out",
          "active:scale-[0.97]",
          isActive
            ? "bg-primary/20 text-primary shadow-[inset_0_1px_0_rgba(255,255,255,0.5)] ring-1 ring-primary/20"
            : "text-default-500 hover:bg-default-100/90 hover:text-default-800",
        ].join(" ")
      }
    >
      {({ isActive }) => (
        <>
          <span className="relative flex h-10 w-10 items-center justify-center">
            <Icon size={24} variant={isActive ? "Bold" : "Linear"} />
            {isActive ? (
              <span className="bg-primary absolute -bottom-0.5 h-1 w-7 rounded-full opacity-90 shadow-sm" aria-hidden />
            ) : null}
          </span>
          <span className="text-[0.65rem] font-semibold leading-none tracking-wide">{label}</span>
        </>
      )}
    </NavLink>
  );
}

/**
 * Floating bottom dock — soft pill, blur (no connection status; that stays in the app surface if needed elsewhere).
 */
export default function AppBottomNav() {
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex justify-center pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-2">
      <nav
        className="border-default-200/60 pointer-events-auto flex max-w-[min(100vw-1.25rem,18rem)] items-center gap-1.5 rounded-[2rem] border bg-content1/92 px-3 py-2 shadow-[0_14px_44px_-14px_rgba(15,23,42,0.2),inset_0_1px_0_rgba(255,255,255,0.75)] backdrop-blur-2xl"
        aria-label="Primary navigation"
      >
        <DockItem to="/" end icon={SecuritySafe} label="Monitor" />
        <DockItem to="/alerts" icon={Notification} label="Alerts" />
      </nav>
    </div>
  );
}
