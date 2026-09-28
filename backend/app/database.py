from prisma import Prisma

# One Prisma client per application process so routers share lifecycle management.
db = Prisma()
