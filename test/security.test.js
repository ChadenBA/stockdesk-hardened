// Tests for the hardening changes (liveness route, log redaction, API key
// check, body size limit). The original tests in server.test.js are unchanged.
const { test } = require("node:test");
const assert = require("node:assert");
const { createServer, start, config } = require("../src/server");

function listen(server) {
  return new Promise((resolve) => server.listen(0, "127.0.0.1", () => resolve(server.address().port)));
}

test("GET /livez is 200 even when the database is unreachable", async () => {
  config.dbHost = "127.0.0.1";
  config.dbPort = 1; // nothing listens here
  const server = createServer();
  const port = await listen(server);
  const res = await fetch(`http://127.0.0.1:${port}/livez`);
  assert.strictEqual(res.status, 200);
  server.close();
});

test("the startup log does not contain the password or the API key", async () => {
  config.port = 0;
  config.dbPassword = "example-db-password-for-test";
  config.apiKey = "example-api-key-for-test";
  const lines = [];
  const original = console.log;
  console.log = (...args) => lines.push(args.join(" "));
  let server;
  try {
    server = start();
    await new Promise((r) => server.once("listening", r));
  } finally {
    console.log = original;
  }
  server.close();
  const output = lines.join("\n");
  assert.match(output, /StockDesk starting with config/);
  assert.ok(!output.includes("example-db-password-for-test"), "DB password leaked to the log");
  assert.ok(!output.includes("example-api-key-for-test"), "API key leaked to the log");
  assert.match(output, /"apiKey":"\[set\]"/);
});

test("POST adjust works with the right API key", async () => {
  config.apiKey = "test-key";
  const server = createServer();
  const port = await listen(server);
  const res = await fetch(`http://127.0.0.1:${port}/api/products/NUT-M6/adjust`, {
    method: "POST",
    headers: { "x-api-key": "test-key" },
    body: JSON.stringify({ delta: 5 }),
  });
  assert.strictEqual(res.status, 200);
  assert.strictEqual((await res.json()).sku, "NUT-M6");
  server.close();
});

test("POST adjust is refused with a wrong API key of the same length", async () => {
  config.apiKey = "test-key";
  const server = createServer();
  const port = await listen(server);
  const res = await fetch(`http://127.0.0.1:${port}/api/products/NUT-M6/adjust`, {
    method: "POST",
    headers: { "x-api-key": "test-kez" },
    body: JSON.stringify({ delta: 1 }),
  });
  assert.strictEqual(res.status, 401);
  server.close();
});

test("POST adjust refuses a body larger than 1 KB", async () => {
  config.apiKey = "test-key";
  const server = createServer();
  const port = await listen(server);
  const res = await fetch(`http://127.0.0.1:${port}/api/products/NUT-M6/adjust`, {
    method: "POST",
    headers: { "x-api-key": "test-key" },
    body: JSON.stringify({ delta: 1, padding: "x".repeat(4096) }),
  });
  assert.strictEqual(res.status, 413);
  server.close();
});
