import { Controller, Get, Query, Headers, UnauthorizedException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

@Controller('internal')
export class InternalController {
  constructor(private readonly prisma: PrismaService) {}

  @Get('emails')
  async listEmails(
    @Query('limit') limit = '20',
    @Headers('authorization') auth?: string,
  ) {
    const token = process.env.INTERNAL_API_TOKEN;
    if (token && auth !== `Bearer ${token}`) {
      throw new UnauthorizedException();
    }

    const take = Math.min(parseInt(limit, 10) || 20, 100);
    return this.prisma.email.findMany({
      take,
      orderBy: { createdAt: 'desc' },
      select: {
        id: true,
        to: true,
        from: true,
        subject: true,
        status: true,
        queuedAt: true,
        sentAt: true,
        createdAt: true,
      },
    });
  }
}
