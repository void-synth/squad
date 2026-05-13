import { existsSync, rmSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(fileURLToPath(new URL(".", import.meta.url)), "..");
const viteCache = join(root, "node_modules", ".vite");

if (existsSync(viteCache)) {
  rmSync(viteCache, { recursive: true, force: true });
  console.info("[dev] Cleared node_modules/.vite (avoids 504 Outdated Optimize Dep)");
}
