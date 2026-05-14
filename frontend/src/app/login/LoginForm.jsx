"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Button, Card, Input, Label, Spinner } from "@heroui/react";
import { useAuth } from "@/context/AuthContext.jsx";

function safeRedirectPath(raw) {
  if (typeof raw !== "string" || !raw.startsWith("/") || raw.startsWith("//")) return "/";
  return raw;
}

export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { mounted, isAuthenticated, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const from = safeRedirectPath(searchParams.get("from") || "/");

  useEffect(() => {
    if (!mounted) return;
    if (isAuthenticated) router.replace(from);
  }, [mounted, isAuthenticated, router, from]);

  function onSubmit(e) {
    e.preventDefault();
    login(email, password);
    router.replace(from);
  }

  if (!mounted) {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <Spinner color="primary" size="lg" />
      </div>
    );
  }

  if (isAuthenticated) {
    return (
      <div className="flex min-h-dvh items-center justify-center">
        <Spinner color="primary" size="lg" />
      </div>
    );
  }

  return (
    <div className="titan-app-bg flex min-h-dvh flex-col items-center justify-center px-4 py-10">
      <Card.Root className="border-default-200/80 bg-content1 w-full max-w-md rounded-2xl border shadow-lg">
        <Card.Header className="flex flex-col gap-1 border-b border-default-200/70 px-6 py-5">
          <Card.Title className="text-default-foreground text-lg font-bold tracking-tight">Sign in</Card.Title>
          <Card.Description className="text-default-500 text-sm leading-relaxed">
            Demo mode — use any email and password. Nothing is sent to a real auth server.
          </Card.Description>
        </Card.Header>
        <Card.Content className="px-6 py-6">
          <form className="flex flex-col gap-5" onSubmit={onSubmit}>
            <div className="flex flex-col gap-2">
              <Label className="text-default-500 text-[0.65rem] font-bold uppercase tracking-wider">Email</Label>
              <Input
                type="email"
                name="email"
                autoComplete="username"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label className="text-default-500 text-[0.65rem] font-bold uppercase tracking-wider">Password</Label>
              <Input
                type="password"
                name="password"
                autoComplete="current-password"
                placeholder="Any value"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <Button type="submit" color="primary" className="mt-1 w-full font-semibold">
              Continue to Titan
            </Button>
          </form>
        </Card.Content>
      </Card.Root>
    </div>
  );
}
