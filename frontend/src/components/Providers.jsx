"use client";

import "@fontsource/jetbrains-mono/latin-400.css";
import "@fontsource/jetbrains-mono/latin-500.css";
import "@fontsource/jetbrains-mono/latin-600.css";
import { AuthProvider } from "@/context/AuthContext.jsx";

export function Providers({ children }) {
  return <AuthProvider>{children}</AuthProvider>;
}
