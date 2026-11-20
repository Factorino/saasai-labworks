import "@fontsource-variable/inter";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "./app/styles/theme.css";
import "./app/styles/base.css";
import { App } from "./app/App";

const root = document.getElementById("root");
if (!root) {
    throw new Error("Missing application root");
}

createRoot(root).render(
    <StrictMode>
        <App />
    </StrictMode>,
);
