import { PrismaClient } from '@prisma/client';
import { createHash, randomBytes } from 'crypto';

const prisma = new PrismaClient();

async function main() {
  const tenant = await prisma.tenant.upsert({
    where: { id: 'default-tenant' },
    update: {},
    create: { id: 'default-tenant', name: 'Default Tenant' },
  });

  const rawKey = `ae_${randomBytes(24).toString('hex')}`;
  const keyHash = createHash('sha256').update(rawKey).digest('hex');

  const existing = await prisma.apiKey.findFirst({ where: { tenantId: tenant.id, name: 'Default' } });
  if (!existing) {
    await prisma.apiKey.create({
      data: {
        tenantId: tenant.id,
        name: 'Default',
        keyHash,
        prefix: rawKey.slice(0, 8),
      },
    });
    console.log('Default API key created. Store securely:');
    console.log(rawKey);
  } else {
    console.log('Default API key already exists (not reprinted).');
  }
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
