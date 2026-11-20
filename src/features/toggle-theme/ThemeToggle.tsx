import { Moon, Sun } from "lucide-react";
import { useEffect, useLayoutEffect, useState } from "react";

type Theme = "light" | "dark";
const STORAGE_KEY = "anamnesis-theme";
const SYSTEM_QUERY = "(prefers-color-scheme: dark)";

function savedTheme(): Theme | null {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        return saved === "light" || saved === "dark" ? saved : null;
    } catch {
        return null;
    }
}

export function ThemeToggle() {
    const [preference, setPreference] = useState(savedTheme);
    const [systemDark, setSystemDark] = useState(() => matchMedia(SYSTEM_QUERY).matches);
    const theme = preference ?? (systemDark ? "dark" : "light");

    useEffect(() => {
        const media = matchMedia(SYSTEM_QUERY);
        const update = (event: MediaQueryListEvent) => setSystemDark(event.matches);
        media.addEventListener("change", update);
        return () => media.removeEventListener("change", update);
    }, []);

    useLayoutEffect(() => {
        if (preference) {
            document.documentElement.dataset.theme = preference;
        } else {
            delete document.documentElement.dataset.theme;
        }
    }, [preference]);

    function toggle() {
        const next = theme === "light" ? "dark" : "light";
        try {
            localStorage.setItem(STORAGE_KEY, next);
        } catch {
            // The current page can still use the selected theme.
        }
        setPreference(next);
    }

    const label = theme === "light" ? "Включить тёмную тему" : "Включить светлую тему";
    return (
        <button
            type="button"
            className="icon-button theme-toggle"
            aria-label={label}
            title={label}
            onClick={toggle}
        >
            {theme === "light" ? <Moon size={18} aria-hidden /> : <Sun size={19} aria-hidden />}
        </button>
    );
}
