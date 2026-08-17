export enum EmailStatus {
  QUEUED = 'queued',
  PROCESSING = 'processing',
  SENT = 'sent',
  DELIVERED = 'delivered',
  DEFERRED = 'deferred',
  BOUNCED = 'bounced',
  FAILED = 'failed',
}

export enum EmailEventType {
  QUEUED = 'email.queued',
  PROCESSING = 'email.processing',
  SENT = 'email.sent',
  DELIVERED = 'email.delivered',
  BOUNCED = 'email.bounced',
  FAILED = 'email.failed',
  DEFERRED = 'email.deferred',
}

export interface SendEmailPayload {
  to: string | string[];
  from: string;
  subject: string;
  html?: string;
  text?: string;
  replyTo?: string;
  cc?: string | string[];
  bcc?: string | string[];
  tags?: string[];
  metadata?: Record<string, string>;
}

export interface EmailJobData extends SendEmailPayload {
  emailId: string;
  tenantId: string;
  idempotencyKey?: string;
}

export const EMAIL_QUEUE = 'email-send';
export const APP_NAME = 'api-email';
export const SETUP_STATE_DIR = '/var/lib/yourapp/setup';
export const INFRA_DIR = '/opt/api-email/infrastructure';
