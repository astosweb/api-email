FROM node:22-bookworm-slim AS base
RUN corepack enable && corepack prepare pnpm@10.33.3 --activate
WORKDIR /app

FROM base AS deps
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml* ./
COPY apps/worker/package.json ./apps/worker/
COPY apps/api/package.json ./apps/api/
COPY packages/shared/package.json ./packages/shared/
RUN pnpm install --frozen-lockfile || pnpm install

FROM deps AS builder
COPY packages/shared ./packages/shared
COPY apps/api/prisma ./apps/api/prisma
COPY apps/worker ./apps/worker
RUN pnpm --filter @api-email/shared build
RUN pnpm --filter @api-email/api exec prisma generate
RUN pnpm --filter @api-email/worker build

FROM node:22-bookworm-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/apps/worker/dist ./apps/worker/dist
COPY --from=builder /app/apps/worker/package.json ./apps/worker/
COPY --from=builder /app/apps/api/prisma ./apps/api/prisma
COPY --from=builder /app/packages/shared/dist ./packages/shared/dist
COPY --from=builder /app/packages/shared/package.json ./packages/shared/
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD node -e "process.exit(0)"
CMD ["node", "apps/worker/dist/main.js"]
