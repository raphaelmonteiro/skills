# Node / TypeScript playbook (NestJS, Express, Fastify, Next.js)

Patterns are ripgrep regexes for `Grep` (use `type: "ts"`, or `glob: "*.{ts,tsx,js,mjs,cjs}"` for mixed codebases). Without the `Grep` and `Glob` tools, run them in Bash: `grep -rnE '<pattern>' --include='*.ts' --include='*.js' .` to search (`-l` for files only) and `find . -name '<glob>'` for the Glob lists.

**Skip:** `node_modules/`, `dist/`, `build/`, `out/`, `.next/`, `.nuxt/`, `.turbo/`, `coverage/`, `*.d.ts`, `*.min.js`, `*.map`, lockfiles, `generated/`, `__generated__/`, `*.generated.ts`, generated ORM/GraphQL clients. Skip `*.spec.ts` / `*.test.ts` unit tests; keep `e2e/`, `*.e2e-spec.ts`, `**/*.feature`, and Playwright/Cypress specs named in business language.

## Phase 1 — Topology

Read the root `package.json` first (`workspaces`, `scripts`, dependencies). Scripts such as `start`, `worker`, `cron`, `consume` and `migrate` name the deployables.

Glob
- `pnpm-workspace.yaml`, `turbo.json`, `nx.json`, `lerna.json`, `rush.json`, `{apps,packages,services,libs}/*/package.json` — monorepo members; each app/service is a fan-out unit
- `**/src/{main,index,server,app,worker}.{ts,js}`, `**/app.module.ts`, `serverless.{yml,ts}`, `**/Dockerfile`, `Procfile`, `vercel.json` — entrypoints and deploy units
- `**/*.module.ts` — NestJS modules, usually one per product area

Grep
- Stack, in `package.json` files: `"(@nestjs/core|express|fastify|next|koa|hono|@trpc/server|@apollo/server|graphql|@prisma/client|typeorm|mongoose|drizzle-orm|sequelize|knex|zod|joi|bullmq|bull|kafkajs|amqplib|@aws-sdk/client-sqs|@temporalio/\w+|inngest|node-cron|@nestjs/schedule|agenda|xstate|@casl/ability|stripe|launchdarkly-[\w-]+|unleash-client|@growthbook/\w+|posthog-node)"`

## Phase 2 — Entities & states

Glob
- `**/schema.prisma`, `**/prisma/schema/*.prisma`, `**/*.entity.ts`, `**/*.schema.ts`, `**/*.model.{ts,js}`, `**/models/**`
- `**/drizzle.config.*`, `**/db/schema*`, `**/db/schema/**`, `**/migrations/**`, `**/*.dto.ts`, `**/*.{graphql,gql}`

Grep
- Prisma (in `*.prisma`): `^(model|enum|type|view) \w+`, then `@relation\(|@default\(|@@(unique|index|map)`
- TypeORM: `@Entity\(|@(Column|OneToMany|ManyToOne|ManyToMany|OneToOne|JoinColumn)\(|@ChildEntity|new EntitySchema\(`
- Mongoose: `new (mongoose\.)?Schema\(|@Schema\(|@Prop\(|mongoose\.model\(|SchemaFactory\.createForClass`
- Drizzle: `(pg|mysql|sqlite)Table\(|(pg|mysql)Enum\(|relations\(`
- Sequelize, Knex, MikroORM: `sequelize\.define\(|extends Model\b|@Table\(|knex\.schema\.(create|alter)Table|table\.enum?\(`
- Zod and other validators: `z\.(object|enum|nativeEnum|discriminatedUnion)\(|\.(refine|superRefine)\(|Joi\.object\(|yup\.object\(|@Is[A-Z]\w+\(`
- TypeScript enums: `^\s*(export\s+)?(declare\s+)?(const\s+)?enum\s+\w+`
- `as const` catalogs: `[}\]]\s*as const`
- Lifecycle catalogs: `\w*(STATUS|Status|STATE|State|ROLE|Role|PLAN|Plan|TIER|Tier|KIND|Kind)\w*\s*=\s*[{\[]`
- Union types: `type \w*(Status|State|Role|Kind|Plan|Tier)\w*\s*=\s*\|?\s*['"]`
- State machines: `createMachine\(|xstate|(allowed|valid)_?transitions|canTransition|nextStatus(es)?|switch\s*\(\w+(\.\w+)*\.(status|state)\)`
- Status writes: `\.(status|state)\s*=[^=]|\b(status|state):\s*\w+(Status|State)\.\w+|\b(status|state):\s*['"]`
- GraphQL: `^(type|enum|input|interface) \w+|@(ObjectType|InputType|Resolver)\(`

## Phase 3 — Entrypoints & actors

Glob
- `**/*.controller.ts`, `**/*.resolver.ts`, `**/routes/**`, `**/*.{routes,router}.{ts,js}`
- Next.js: `**/app/**/route.{ts,js}`, `**/pages/api/**/*.{ts,js}`, `**/middleware.{ts,js}`, `**/app/**/actions.{ts,js}`
- `**/*.{processor,consumer,worker,job,cron,listener,subscriber,guard,middleware}.{ts,js}`, `**/{jobs,workers,queues,consumers,cron}/**`

Grep
- NestJS HTTP: `@Controller\(` (files), then `@(Get|Post|Put|Patch|Delete|All)\(` (content)
- NestJS GraphQL and microservices: `@(Query|Mutation|Subscription|ResolveField)\(|@(MessagePattern|EventPattern|GrpcMethod|SubscribeMessage)\(`
- Express, Koa, Hono, Fastify: `\b(app|router|server|fastify|api|routes?)\.(get|post|put|patch|delete|all|use|route|register)\(|express\.Router\(|new (Router|Hono)\(|fastify\.route\(`
- Next.js handlers and server actions: `export (async )?function (GET|POST|PUT|PATCH|DELETE)\b|['"]use server['"]`
- tRPC: `\.(query|mutation|subscription)\(|(public|protected|admin)Procedure|createTRPCRouter`
- Serverless: `export const handler|^\s*(events|schedule|sqs|http|httpApi):`
- BullMQ / Bull: `new (Worker|Queue|FlowProducer)\(|@Processor\(|@Process\(|extends WorkerHost|@InjectQueue\(|registerQueue|\.add\(\s*['"]|repeat:\s*\{`
- Kafka, RabbitMQ, SQS, Pub/Sub consumers: `\.consumer\(\{|consumer\.(subscribe|run)\(|each(Message|Batch)|channel\.(consume|assertQueue)\(|@Rabbit(Subscribe|RPC)\(|ReceiveMessageCommand|Consumer\.create\(|@SqsMessageHandler|subscription\.on\(\s*['"]message`
- Producers: `producer\.send\(|\.emit\(\s*['"]|\.publish\(|SendMessageCommand|\.sendToQueue\(`
- Crons and timers: `@(Cron|Interval|Timeout)\(|CronExpression\.|cron\.schedule\(|new CronJob\(|scheduleJob\(|agenda\.(define|every)\(|setInterval\(|"crons"`
- Workflows and events: `proxyActivities|inngest\.createFunction\(|step\.run\(|@OnEvent\(|@(Events|Command|Query)Handler\(|@Saga\(|eventEmitter\.(emit|on)\(`
- Webhooks: `(?i)webhook|constructEvent\(|x-[\w-]+-signature`
- Guards and RBAC (NestJS): `@UseGuards\(|implements CanActivate|@(Roles|Permissions?|Public|Scopes)\(|SetMetadata\(|AbilityBuilder|defineAbility|@CheckPolicies|AuthGuard\(`
- Middleware and RBAC (Express, Next.js): `(require|ensure|check|is|has|verify|authorize)(Auth|Admin|Role|Permission|Scope|Owner)\w*\(|\.(role|roles|permissions|scopes)\b\s*(===?|!==?|\.includes)|passport\.authenticate|getServerSession|\bauth\(\)`
- Role catalog: `enum \w*(Role|Permission|Scope)\w*|\bROLES?\b\s*=\s*[{\[]|['"](admin|owner|superadmin|staff|manager|member)['"]`
- Outbound integrations: `axios\.(create|get|post)|HttpService|new Stripe\(|@sendgrid|twilio|baseURL|new \w+Client\(\{`

## Phase 4 — Business logic & guardrails

Glob
- `**/*.service.ts`, `**/*.{usecase,use-case,handler,policy,rules,calculator,validator,strategy}.ts`, `**/{services,usecases,use-cases,domain,core}/**`
- `**/{constants,config,limits,settings,flags,features}*.{ts,js}`, `**/constants/**`, `**/config/**`

Grep
- Custom errors (the rule index): `class \w+(Error|Exception) extends` — then `throw new \w+(Error|Exception)\(` with `-B 5` to capture the condition
- HTTP rejections: `new (BadRequest|Forbidden|Conflict|UnprocessableEntity|PaymentRequired|PreconditionFailed|TooManyRequests)Exception\(|TRPCError\(|res\.status\(4\d\d\)|reply\.code\(4\d\d\)|createError\(4\d\d`
- Error-code catalogs: `(ERROR|ERR)_?CODES?\b|enum \w*ErrorCode|code:\s*['"][A-Z][A-Z_]{3,}['"]`
- Guard functions: `function (can|is|has|validate|check|ensure|assert)[A-Z]\w*\(|\b(assert|invariant)\(|if\s*\(!\w+(\.\w+)*\.(is|can|has)[A-Z]\w*`
- Money variables: `(?i)\b\w*(fee|price|amount|discount|tax|vat|commission|interest|penalty|refund|surcharge|subtotal|margin)\w*\s*[-+*/]?=[^=>]`
- Money math: `Math\.(round|ceil|floor|max|min)\(|\.toFixed\(|new (Decimal|Big|BigNumber)\(|[dD]inero\(|\*\s*0\.\d+|/\s*100\b|unit_amount|\bcents\b`
- Named constants: `^\s*(export\s+)?const [A-Z][A-Z0-9_]+\s*(:\s*[\w<>\[\]]+\s*)?=`
- Inline magic numbers: `[<>]=?\s*\d{2,}|\d+\s*\*\s*(24|60|1000|1024)\b|\b(days|hours|minutes|ttl|expires\w*|timeout|limit|max\w*|min\w*):\s*\d|(add|sub)(Days|Hours|Minutes|Months)\(`
- Config: `process\.env\.\w+|process\.env\[|import\.meta\.env\.|configService\.get(OrThrow)?\b|registerAs\(|createEnv\(|convict\(`
- Config fallbacks (the effective value when unset): `process\.env\.\w+\s*(\|\||\?\?)`
- Feature flags (SDKs and helpers): `(?i)feature[_-]?(flag|toggle)s?|isFeatureEnabled|isEnabled\(\s*['"]|\.(bool)?variation\(|useFlags?\(|useFeatureFlag|getFeatureFlag|launchdarkly|unleash|growthbook|flagsmith|posthog|statsig|configcat|openfeature`
- Feature flags (env toggles): `process\.env\.(NEXT_PUBLIC_)?(ENABLE|DISABLE|FEATURE|FF)_\w+|process\.env\.\w+_(ENABLED|DISABLED)`
- Tenant, market and plan special cases: `\b\w*(country|tenant|market|region|plan|tier|currency)\w*\s*(===?|!==?)\s*['"]|allow_?list|block_?list|whitelist|blacklist|\b(ALLOWED|BETA|INTERNAL)_\w+`
- Legacy paths: `(?i)@deprecated|legacy|todo|fixme|hack|workaround|temporary`, `/v1/|\bV1\b|\.old\.|_old\b`

## Tips
- `schema.prisma` is usually the single highest-signal file in the repository: grep `^(model|enum)` for the index, then read models in slices.
- NestJS dependency injection: `constructor(private readonly x: XService)` leads to Glob `**/x.service.ts`. Barrel `index.ts` files hide paths — grep the definition `(class|function|const|enum) <Symbol>\b` instead of following imports.
- Untyped JavaScript: the validators (Joi, Zod, Mongoose schemas) are the entity definitions.
- Next.js: the `matcher` in `middleware.ts` shows the protected areas, and server actions are entrypoints just like route handlers.
- A cron expression or queue name is often a constant or env var — resolve it and cite both the decorator and the value.
