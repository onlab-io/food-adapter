import { useEffect, useState } from "react";

/** Carica un'immagine protetta (via fetch autenticato) e la mostra come blob URL. */
export default function AuthImg({
  loader,
  depKey,
  alt = "",
  className,
  style,
  onClick,
}: {
  loader: () => Promise<string>;
  depKey: string;
  alt?: string;
  className?: string;
  style?: React.CSSProperties;
  onClick?: () => void;
}) {
  const [url, setUrl] = useState<string | null>(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    let active = true;
    let made: string | null = null;
    setUrl(null);
    setErr(false);
    loader()
      .then((u) => {
        if (active) {
          made = u;
          setUrl(u);
        } else {
          URL.revokeObjectURL(u);
        }
      })
      .catch(() => active && setErr(true));
    return () => {
      active = false;
      if (made) URL.revokeObjectURL(made);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [depKey]);

  if (err) return <div className={className} style={{ ...style, display: "grid", placeItems: "center", color: "#aaa" }}>—</div>;
  if (!url) return <div className={className} style={{ ...style, background: "#eef0f3" }} />;
  return <img src={url} alt={alt} className={className} style={style} onClick={onClick} />;
}
