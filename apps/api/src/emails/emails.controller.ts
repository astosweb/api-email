import {
  Controller,
  Post,
  Get,
  Body,
  Param,
  Headers,
  UseGuards,
  ConflictException,
  BadRequestException,
  Req,
} from '@nestjs/common';
import { ApiTags, ApiBearerAuth, ApiHeader } from '@nestjs/swagger';
import { InjectQueue } from '@nestjs/bullmq';
import { Queue } from 'bullmq';
import { EMAIL_QUEUE, EmailJobData, EmailStatus } from '@api-email/shared';
import { ApiKeyGuard } from '../auth/api-key.guard';
import { PrismaService } from '../prisma/prisma.service';
import { SendEmailDto } from './dto/send-email.dto';

@ApiTags('emails')
@ApiBearerAuth('api-key')
@UseGuards(ApiKeyGuard)
@Controller('emails')
export class EmailsController {
  constructor(
    private readonly prisma: PrismaService,
    @InjectQueue(EMAIL_QUEUE) private readonly emailQueue: Queue<EmailJobData>,
  ) {}

  @Post()
  @ApiHeader({ name: 'Idempotency-Key', required: false })
  async send(
    @Body() dto: SendEmailDto,
    @Headers('idempotency-key') idempotencyKey: string | undefined,
    @Req() req: { tenant: { id: string } },
  ) {
    const tenant = req.tenant;
    const to = dto.to;
    const cc = dto.cc ? (Array.isArray(dto.cc) ? dto.cc : [dto.cc]) : [];
    const bcc = dto.bcc ? (Array.isArray(dto.bcc) ? dto.bcc : [dto.bcc]) : [];

    if (!dto.html && !dto.text) {
      throw new BadRequestException('Either html or text body is required');
    }

    if (idempotencyKey) {
      const existing = await this.prisma.email.findUnique({
        where: { tenantId_idempotencyKey: { tenantId: tenant.id, idempotencyKey } },
      });
      if (existing) {
        return { id: existing.id, status: existing.status, duplicate: true };
      }
    }

    const email = await this.prisma.email.create({
      data: {
        tenantId: tenant.id,
        idempotencyKey: idempotencyKey ?? null,
        from: dto.from,
        to,
        cc,
        bcc,
        subject: dto.subject,
        html: dto.html,
        text: dto.text,
        replyTo: dto.replyTo,
        tags: dto.tags ?? [],
        metadata: dto.metadata ?? {},
        status: EmailStatus.QUEUED,
        events: {
          create: { type: 'email.queued', message: 'Email queued for delivery' },
        },
      },
    });

    const jobData: EmailJobData = {
      emailId: email.id,
      tenantId: tenant.id,
      idempotencyKey,
      from: dto.from,
      to,
      cc,
      bcc,
      subject: dto.subject,
      html: dto.html,
      text: dto.text,
      replyTo: dto.replyTo,
      tags: dto.tags,
      metadata: dto.metadata,
    };

    await this.emailQueue.add('send', jobData, {
      jobId: email.id,
      attempts: 5,
      backoff: { type: 'exponential', delay: 5000 },
      removeOnComplete: 1000,
      removeOnFail: 5000,
    });

    return { id: email.id, status: email.status };
  }

  @Get(':id')
  async get(@Param('id') id: string, @Req() req: { tenant: { id: string } }) {
    const email = await this.prisma.email.findFirst({
      where: { id, tenantId: req.tenant.id },
      include: { events: { orderBy: { createdAt: 'asc' } } },
    });
    if (!email) {
      throw new ConflictException('Email not found');
    }
    return email;
  }
}
