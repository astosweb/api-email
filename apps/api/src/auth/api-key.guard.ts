import { Injectable, CanActivate, ExecutionContext, UnauthorizedException } from '@nestjs/common';
import { createHash, timingSafeEqual } from 'crypto';
import { PrismaService } from '../prisma/prisma.service';

@Injectable()
export class ApiKeyGuard implements CanActivate {
  constructor(private readonly prisma: PrismaService) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const request = context.switchToHttp().getRequest();
    const authHeader = request.headers['authorization'] as string | undefined;
    if (!authHeader?.startsWith('Bearer ')) {
      throw new UnauthorizedException('Missing API key');
    }

    const apiKey = authHeader.slice(7);
    const keyHash = createHash('sha256').update(apiKey).digest('hex');

    const record = await this.prisma.apiKey.findFirst({
      where: { keyHash, revoked: false },
      include: { tenant: true },
    });

    if (!record) {
      throw new UnauthorizedException('Invalid API key');
    }

    const stored = Buffer.from(record.keyHash, 'hex');
    const provided = Buffer.from(keyHash, 'hex');
    if (stored.length !== provided.length || !timingSafeEqual(stored, provided)) {
      throw new UnauthorizedException('Invalid API key');
    }

    await this.prisma.apiKey.update({
      where: { id: record.id },
      data: { lastUsed: new Date() },
    });

    request.tenant = record.tenant;
    request.apiKey = record;
    return true;
  }
}
