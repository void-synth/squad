import { io } from "socket.io-client";

const url = import.meta.env.VITE_SOCKET_URL || "";

export function createDashboardSocket() {
  return io(url, {
    autoConnect: false,
    transports: ["websocket", "polling"],
  });
}
