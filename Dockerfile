# StockDesk image (hardened).
# Base: Node.js 22 LTS on Alpine (small, few packages), same major version as
# .nvmrc and CI. A version tag can be moved upstream: pin the digest too.
# TODO verify: replace with node:22-alpine@sha256:<digest> (Docker Hub was not
# reachable from my environment, so I could not look the digest up).
# Dependabot (.github/dependabot.yml) then keeps tag and digest up to date.
FROM node:22-alpine

ENV NODE_ENV=production
WORKDIR /app

# The app has zero dependencies, so the package managers are not needed at
# run time. Removing them shrinks the attack surface (and scanner noise).
# If dependencies are added later: multi-stage build, "npm ci --omit=dev" in
# the first stage, copy node_modules into this one.
# Dedicated user with a UID above 10000 (no overlap with host users).
RUN rm -rf /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/corepack \
           /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack \
           /usr/local/bin/yarn /usr/local/bin/yarnpkg /opt/yarn-* \
 && addgroup -S -g 10001 stockdesk \
 && adduser -S -D -H -u 10001 -G stockdesk stockdesk

# Copy only what the app needs (never .env, .git or k8s/). Files stay owned
# by root and are not writable by the app user: a compromised process cannot
# rewrite its own code.
COPY package.json ./
COPY src/ ./src/

# Numeric UID so that Kubernetes "runAsNonRoot" can verify it.
USER 10001:10001

# Only the API port. No inspector port: --inspect gives code execution to
# anyone who can reach it (see docker-compose.debug.yml for local debugging).
EXPOSE 3000

# Used by docker / compose; Kubernetes uses its own probes (/livez, /health).
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD ["node", "-e", "fetch('http://127.0.0.1:3000/livez').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"]

# Exec form: node is PID 1 and receives SIGTERM directly (handled in server.js).
CMD ["node", "src/server.js"]
