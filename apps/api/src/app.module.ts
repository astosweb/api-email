import { Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bullmq';
import { TerminusModule } from '@nestjs/terminus';
import { EMAIL_QUEUE } from '@api-email/shared';
import { PrismaModule } from './prisma/prisma.module';
import { EmailsModule } from './emails/emails.module';
import { HealthModule } from './health/health.module';
import { AuthModule } from './auth/auth.module';
import { InternalModule } from './internal/internal.module';

@Module({
  imports: [
    PrismaModule,
    AuthModule,
    EmailsModule,
    InternalModule,
    HealthModule,
    TerminusModule,
    BullModule.forRoot({
      connection: {
        host: process.env.REDIS_HOST ?? 'localhost',
        port: parseInt(process.env.REDIS_PORT ?? '6379', 10),
        password: process.env.REDIS_PASSWORD || undefined,
      },
    }),
    BullModule.registerQueue({ name: EMAIL_QUEUE }),
  ],
})
export class AppModule {}
