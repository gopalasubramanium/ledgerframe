import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HashRouter, Route, Routes } from "react-router-dom";
import { ThemeProvider } from "./theme/ThemeProvider";
import { DisplayProvider } from "./theme/DisplayProvider";
import { ToastProvider } from "./components/ui";
import { RefdataProvider } from "./refdata/RefdataProvider";
import App from "./App";
import { KitchenSink } from "./routes/KitchenSink";
import { Holdings } from "./routes/Holdings";
import "./index.css";

const root = document.getElementById("root");
if (!root) throw new Error("#root not found");

createRoot(root).render(
  <StrictMode>
    <ThemeProvider>
      <DisplayProvider>
        <ToastProvider>
          <RefdataProvider>
            <HashRouter>
              <Routes>
                <Route path="/" element={<App />} />
                <Route path="/holdings" element={<Holdings />} />
                <Route path="/kitchen-sink" element={<KitchenSink />} />
              </Routes>
            </HashRouter>
          </RefdataProvider>
        </ToastProvider>
      </DisplayProvider>
    </ThemeProvider>
  </StrictMode>,
);
