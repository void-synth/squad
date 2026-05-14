const fs = require("fs");
const path = require("path");

const nextDir = path.join(__dirname, "..", ".next");
fs.rmSync(nextDir, { recursive: true, force: true });
