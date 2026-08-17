import { NestFactory } from '@nestjs/core';
import { ValidationPipe, Logger } from '@nestjs/common';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import helmet from 'helmet';
import { AppModule } from './app.module';

async function bootstrap() {
  const logger = new Logger('Bootstrap');
  const app = await NestFactory.create(AppModule, {
    logger: ['error', 'warn', 'log'],
  });

  app.use(helmet());
  app.enableCors({
    origin: process.env.CORS_ORIGIN?.split(',') ?? ['http://localhost:3000'],
    credentials: true,
  });
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
    }),
  );
  app.setGlobalPrefix('v1', { exclude: ['health', 'health/ready', 'health/live'] });

  const config = new DocumentBuilder()
    .setTitle('API Email')
    .setDescription('Production-grade developer email API')
    .setVersion('1.0')
    .addApiKey({ type: 'apiKey', name: 'Authorization', in: 'header' }, 'api-key')
    .build();
  SwaggerModule.setup('docs', app, SwaggerModule.createDocument(app, config));

  const port = parseInt(process.env.PORT ?? '4000', 10);
  await app.listen(port, '0.0.0.0');
  logger.log(`API listening on port ${port}`);
}

bootstrap();
