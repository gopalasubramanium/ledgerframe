import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ThemeProvider } from "./theme/ThemeProvider";
import { DisplayProvider } from "./theme/DisplayProvider";
import App from "./App";
import "./index.css";

const root = document.getElementById("root");
if (!root) throw new Error("#root not found");

createRoot(root).render(
  <StrictMode>
    <ThemeProvider>
      <DisplayProvider>
        <App />
      </DisplayProvider>
    </ThemeProvider>
  </StrictMode>,
);
