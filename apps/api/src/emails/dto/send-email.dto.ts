import { IsEmail, IsOptional, IsString, IsArray, IsObject, MaxLength } from 'class-validator';
import { Transform } from 'class-transformer';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class SendEmailDto {
  @ApiProperty({ example: 'hello@example.com' })
  @IsEmail()
  from!: string;

  @ApiProperty({ oneOf: [{ type: 'string' }, { type: 'array', items: { type: 'string' } }] })
  @Transform(({ value }) => (Array.isArray(value) ? value : [value]))
  @IsArray()
  @IsEmail({}, { each: true })
  to!: string[];

  @ApiProperty({ example: 'Welcome!' })
  @IsString()
  @MaxLength(998)
  subject!: string;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  html?: string;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  text?: string;

  @ApiPropertyOptional()
  @IsOptional()
  @IsEmail()
  replyTo?: string;

  @ApiPropertyOptional()
  @IsOptional()
  cc?: string | string[];

  @ApiPropertyOptional()
  @IsOptional()
  bcc?: string | string[];

  @ApiPropertyOptional({ type: [String] })
  @IsOptional()
  @IsArray()
  @IsString({ each: true })
  tags?: string[];

  @ApiPropertyOptional()
  @IsOptional()
  @IsObject()
  metadata?: Record<string, string>;
}
