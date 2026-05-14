"use client";

import { Suspense } from "react";
import { Spinner } from "@heroui/react";
import LoginForm from "./LoginForm.jsx";

function LoginFallback() {
  return (
    <div className="titan-app-bg flex min-h-dvh items-center justify-center">
      <Spinner color="primary" size="lg" />
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginFallback />}>
      <LoginForm />
    </Suspense>
  );
}
