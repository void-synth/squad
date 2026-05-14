import { io } from "socket.io-client";

const url = process.env.NEXT_PUBLIC_SOCKET_URL || "";

export function createDashboardSocket() {
  return io(url, {
    autoConnect: false,
    transports: ["websocket", "polling"],
  });
}
