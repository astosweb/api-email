# API
FROM node:22-bookworm-slim AS base
RUN corepack enable && corepack prepare pnpm@10.33.3 --activate
WORKDIR /app

FROM base AS deps
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml* ./
COPY apps/api/package.json ./apps/api/
COPY apps/worker/package.json ./apps/worker/
COPY packages/shared/package.json ./packages/shared/
RUN pnpm install --frozen-lockfile || pnpm install

FROM deps AS builder
COPY packages/shared ./packages/shared
COPY apps/api ./apps/api
RUN pnpm --filter @api-email/shared build
RUN pnpm --filter @api-email/api exec prisma generate
RUN pnpm --filter @api-email/api build

FROM node:22-bookworm-slim AS runner
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/apps/api/dist ./apps/api/dist
COPY --from=builder /app/apps/api/package.json ./apps/api/
COPY --from=builder /app/apps/api/prisma ./apps/api/prisma
COPY --from=builder /app/packages/shared/dist ./packages/shared/dist
COPY --from=builder /app/packages/shared/package.json ./packages/shared/
COPY --from=builder /app/package.json ./
COPY --from=builder /app/pnpm-workspace.yaml ./
EXPOSE 4000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:4000/health/live || exit 1
CMD ["node", "apps/api/dist/main.js"]
