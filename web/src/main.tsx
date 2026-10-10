import "@fontsource/geist-sans/400.css";
import "@fontsource/geist-sans/500.css";
import "@fontsource/geist-sans/600.css";
import "@fontsource/geist-mono/400.css";
import "@fontsource/geist-mono/500.css";
import "./styles.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Artifact } from "./pages/Artifact";
import { Artifacts } from "./pages/Artifacts";
import { Experiments } from "./pages/Experiments";
import { Method } from "./pages/Method";
import { NotFound } from "./pages/NotFound";
import { Overview } from "./pages/Overview";

const root = document.getElementById("root");
if (!root) throw new Error("missing #root element");

createRoot(root).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/overview" replace />} />
          <Route path="overview" element={<Overview />} />
          <Route path="artifacts" element={<Artifacts />} />
          <Route path="artifacts/:id" element={<Artifact />} />
          <Route path="experiments" element={<Experiments />} />
          <Route path="experiments/:exp" element={<Experiments />} />
          <Route path="method" element={<Method />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
