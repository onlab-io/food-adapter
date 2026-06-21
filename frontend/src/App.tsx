import { useState } from "react";
import Formati from "./pages/Formati";
import Batch from "./pages/Batch";

type View = "batch" | "formati";

export default function App() {
  const [view, setView] = useState<View>("batch");

  return (
    <>
      <header className="app-header">
        <span className="brand">📸 Photo Adapter</span>
        <span className="badge">Fase 1 crop · Fase 2 template AI</span>
        <nav className="nav">
          <button className={view === "batch" ? "active" : ""} onClick={() => setView("batch")}>
            Elabora batch
          </button>
          <button className={view === "formati" ? "active" : ""} onClick={() => setView("formati")}>
            Impostazioni
          </button>
        </nav>
        <span className="spacer" />
      </header>
      <main className="container">{view === "batch" ? <Batch /> : <Formati />}</main>
    </>
  );
}
