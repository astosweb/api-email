import { Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bullmq';
import { TerminusModule } from '@nestjs/terminus';
import { EMAIL_QUEUE } from '@api-email/shared';
import { PrismaModule } from '../prisma/prisma.module';
import { HealthController } from './health.controller';

@Module({
  imports: [
    TerminusModule,
    PrismaModule,
    BullModule.registerQueue({ name: EMAIL_QUEUE }),
  ],
  controllers: [HealthController],
})
export class HealthModule {}
