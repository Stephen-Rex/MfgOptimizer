// src/main.tsx

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { setFrameHeight } from "./bridge/streamlitBridge";
import "./styles/app.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

setFrameHeight(800);
