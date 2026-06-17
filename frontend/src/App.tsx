import { useEffect, useState } from "react";
import { getToken, clearToken } from "./api";
import Login from "./pages/Login";
import Formati from "./pages/Formati";
import Batch from "./pages/Batch";

type View = "batch" | "formati";

export default function App() {
  const [authed, setAuthed] = useState<boolean>(!!getToken());
  const [view, setView] = useState<View>("batch");

  useEffect(() => {
    const onUnauth = () => setAuthed(false);
    window.addEventListener("fia-unauthorized", onUnauth);
    return () => window.removeEventListener("fia-unauthorized", onUnauth);
  }, []);

  if (!authed) return <Login onLogin={() => setAuthed(true)} />;

  return (
    <>
      <header className="app-header">
        <span className="brand">🍽️ Food Image Adapter</span>
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
        <button
          className="small"
          onClick={() => {
            clearToken();
            setAuthed(false);
          }}
        >
          Esci
        </button>
      </header>
      <main className="container">{view === "batch" ? <Batch /> : <Formati />}</main>
    </>
  );
}
