// Tiny static file server for the demo harness (dev only, binds to localhost).
import { createReadStream, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize, resolve } from "node:path";

const root = resolve(import.meta.dirname, "../..");
const types = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".json": "application/json" };
const port = Number(process.env.PORT ?? 4173);

createServer((req, res) => {
  const url = new URL(req.url ?? "/", "http://localhost");
  let path = normalize(join(root, decodeURIComponent(url.pathname)));
  if (!path.startsWith(root)) {
    res.writeHead(403).end();
    return;
  }
  try {
    if (statSync(path).isDirectory()) path = join(path, "index.html");
    res.writeHead(200, { "content-type": types[extname(path)] ?? "application/octet-stream" });
    createReadStream(path).pipe(res);
  } catch {
    res.writeHead(404).end();
  }
}).listen(port, "127.0.0.1");
