import { Controller, Get } from '@nestjs/common';
import { HealthCheck, HealthCheckService, PrismaHealthIndicator } from '@nestjs/terminus';
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';
import Redis from 'ioredis';
import { EMAIL_QUEUE } from '@api-email/shared';
import { PrismaService } from '../prisma/prisma.service';

@Controller('health')
export class HealthController {
  private redis: Redis;

  constructor(
    private health: HealthCheckService,
    private prismaHealth: PrismaHealthIndicator,
    private prisma: PrismaService,
    @InjectQueue(EMAIL_QUEUE) private emailQueue: Queue,
  ) {
    this.redis = new Redis({
      host: process.env.REDIS_HOST ?? 'localhost',
      port: parseInt(process.env.REDIS_PORT ?? '6379', 10),
      password: process.env.REDIS_PASSWORD || undefined,
      maxRetriesPerRequest: 1,
      lazyConnect: true,
    });
  }

  @Get()
  @HealthCheck()
  check() {
    return this.health.check([
      () => this.prismaHealth.pingCheck('database', this.prisma),
      async () => {
        await this.redis.connect();
        const pong = await this.redis.ping();
        await this.redis.disconnect();
        return { redis: { status: pong === 'PONG' ? 'up' : 'down' } };
      },
      async () => {
        const counts = await this.emailQueue.getJobCounts();
        return {
          queue: {
            status: 'up',
            waiting: counts.waiting,
            active: counts.active,
            failed: counts.failed,
          },
        };
      },
    ]);
  }

  @Get('live')
  live() {
    return { status: 'ok' };
  }

  @Get('ready')
  async ready() {
    await this.prisma.$queryRaw`SELECT 1`;
    return { status: 'ready' };
  }
}
