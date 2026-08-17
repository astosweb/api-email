import { Module } from '@nestjs/common';
import { BullModule } from '@nestjs/bullmq';
import { EMAIL_QUEUE } from '@api-email/shared';
import { EmailsController } from './emails.controller';

@Module({
  imports: [BullModule.registerQueue({ name: EMAIL_QUEUE })],
  controllers: [EmailsController],
})
export class EmailsModule {}
