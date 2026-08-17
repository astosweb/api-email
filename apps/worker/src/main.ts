import { PrismaClient } from '@prisma/client';
import { Worker, Job } from 'bullmq';
import nodemailer from 'nodemailer';
import pino from 'pino';
import { EMAIL_QUEUE, EmailJobData, EmailStatus } from '@api-email/shared';

const logger = pino({ name: 'email-worker' });
const prisma = new PrismaClient();

const smtpHost = process.env.SMTP_HOST ?? 'localhost';
const smtpPort = parseInt(process.env.SMTP_PORT ?? '25', 10);

const transporter = nodemailer.createTransport({
  host: smtpHost,
  port: smtpPort,
  secure: smtpPort === 465,
  tls: { rejectUnauthorized: process.env.SMTP_TLS_VERIFY !== 'false' },
  connectionTimeout: 30000,
});

async function processEmail(job: Job<EmailJobData>) {
  const data = job.data;
  logger.info({ emailId: data.emailId, jobId: job.id }, 'Processing email');

  await prisma.email.update({
    where: { id: data.emailId },
    data: {
      status: EmailStatus.PROCESSING,
      events: {
        create: { type: 'email.processing', message: 'Worker processing email' },
      },
    },
  });

  const to = Array.isArray(data.to) ? data.to : [data.to];

  try {
    const info = await transporter.sendMail({
      from: data.from,
      to: to.join(', '),
      cc: data.cc ? (Array.isArray(data.cc) ? data.cc.join(', ') : data.cc) : undefined,
      bcc: data.bcc ? (Array.isArray(data.bcc) ? data.bcc.join(', ') : data.bcc) : undefined,
      subject: data.subject,
      html: data.html,
      text: data.text,
      replyTo: data.replyTo,
      headers: data.metadata
        ? Object.fromEntries(Object.entries(data.metadata).map(([k, v]) => [`X-Metadata-${k}`, v]))
        : undefined,
    });

    await prisma.email.update({
      where: { id: data.emailId },
      data: {
        status: EmailStatus.SENT,
        smtpMessageId: info.messageId,
        sentAt: new Date(),
        events: {
          create: {
            type: 'email.sent',
            message: 'Email accepted by SMTP server',
            metadata: { messageId: info.messageId, response: info.response },
          },
        },
      },
    });

    logger.info({ emailId: data.emailId, messageId: info.messageId }, 'Email sent');
    return { messageId: info.messageId };
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Unknown SMTP error';
    const isPermanent = /550|551|552|553|554|invalid|not found|does not exist/i.test(message);

    await prisma.email.update({
      where: { id: data.emailId },
      data: {
        status: isPermanent ? EmailStatus.BOUNCED : EmailStatus.FAILED,
        errorMessage: message,
        failedAt: new Date(),
        events: {
          create: {
            type: isPermanent ? 'email.bounced' : 'email.failed',
            message,
            metadata: { permanent: isPermanent },
          },
        },
      },
    });

    logger.error({ emailId: data.emailId, err: message }, 'Email delivery failed');
    if (isPermanent) {
      return { failed: true, permanent: true };
    }
    throw err;
  }
}

const worker = new Worker<EmailJobData>(EMAIL_QUEUE, processEmail, {
  connection: {
    host: process.env.REDIS_HOST ?? 'localhost',
    port: parseInt(process.env.REDIS_PORT ?? '6379', 10),
    password: process.env.REDIS_PASSWORD || undefined,
  },
  concurrency: parseInt(process.env.WORKER_CONCURRENCY ?? '10', 10),
});

worker.on('completed', (job) => {
  logger.info({ jobId: job.id }, 'Job completed');
});

worker.on('failed', (job, err) => {
  logger.error({ jobId: job?.id, err: err.message }, 'Job failed');
});

logger.info({ smtpHost, smtpPort }, 'Email worker started');

process.on('SIGTERM', async () => {
  logger.info('Shutting down worker');
  await worker.close();
  await prisma.$disconnect();
  process.exit(0);
});
