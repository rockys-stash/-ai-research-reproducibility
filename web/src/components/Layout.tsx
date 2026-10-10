import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

const NAV = [
  { to: "/overview", label: "Overview" },
  { to: "/artifacts", label: "Artifacts" },
  { to: "/experiments", label: "Experiments" },
  { to: "/method", label: "Method" },
];

type Theme = "system" | "light" | "dark";

function readTheme(): Theme {
  try {
    const t = localStorage.getItem("laboratory-theme");
    return t === "light" || t === "dark" ? t : "system";
  } catch {
    return "system";
  }
}

function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(readTheme);
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
    try {
      localStorage.setItem("laboratory-theme", theme);
    } catch {
      /* storage unavailable: the preference lasts for this page view */
    }
  }, [theme]);
  const next: Record<Theme, Theme> = {
    system: "light",
    light: "dark",
    dark: "system",
  };
  return (
    <button
      className="btn ghost"
      type="button"
      onClick={() => setTheme(next[theme])}
      aria-label={`Theme: ${theme}. Switch to ${next[theme]}`}
    >
      Theme: {theme}
    </button>
  );
}

export function Logo() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden="true"
    >
      <path d="M6 1.5h4M6.8 1.5v4.2L2.6 13a1 1 0 0 0 .9 1.5h9a1 1 0 0 0 .9-1.5L9.2 5.7V1.5M4.4 10h7.2" />
    </svg>
  );
}

export function Layout() {
  const location = useLocation();
  useEffect(() => {
    document.getElementById("main")?.focus({ preventScroll: true });
  }, [location.pathname]);
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="topbar">
        <div className="topbar-inner">
          <div className="topbar-row">
            <NavLink
              to="/overview"
              className="brand"
              aria-label="Laboratory, research reproducibility"
            >
              <span className="brand-mark">
                <Logo />
              </span>
              <span>
                <span className="brand-name">Laboratory</span>
                <br />
                <span className="brand-sub">
                  Research reproducibility
                </span>
              </span>
            </NavLink>
            <span className="deployment">
              Can AI-generated research be reproduced?
            </span>
            <ThemeToggle />
          </div>
          <nav className="tabs" aria-label="Sections">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                className={({ isActive }) => (isActive ? "active" : "")}
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main id="main" className="main" tabIndex={-1}>
        <Outlet />
      </main>
    </>
  );
}
