# Java playbook (Spring Boot, Quarkus, Micronaut; Kotlin notes at the end)

Patterns are ripgrep regexes for `Grep` (use `type: "java"`). Annotations make Java very greppable: find the annotation with `output_mode: "files_with_matches"`, then read slices. Without the `Grep` and `Glob` tools, run them in Bash: `grep -rnE '<pattern>' --include='*.java' .` to search (`-l` for files only) and `find . -name '<glob>'` for the Glob lists.

**Skip:** `target/`, `build/`, `out/`, `.gradle/`, `generated/`, `generated-sources/`, `*MapperImpl.java` (MapStruct), `Q*.java` (QueryDSL), generated protobuf/Avro/OpenAPI classes. Skip `src/test/**` except acceptance evidence: `*IT.java`, `*AcceptanceTest*.java`, `**/*.feature`, and tests using `@DisplayName` in business language.

## Phase 1 — Topology

Glob
- `pom.xml`, `**/pom.xml`, `settings.gradle*`, `**/build.gradle*` — modules; each module with a `main` class is a deployable
- `**/src/main/java/**/*Application.java` — application roots; sibling packages show the layout
- `**/src/main/resources/application*.{yml,yaml,properties}`, `**/bootstrap*.yml` — config and per-profile behaviour
- `**/db/migration/*.sql` (Flyway), `**/db/changelog/**` (Liquibase) — schema history
- `**/*.proto`, `**/*.avsc`, `**/openapi*.{yml,yaml,json}`, `**/*.bpmn`, `**/*.dmn`, `**/*.drl` — contracts, workflows, rule engines

Grep
- Module list: `<module>` in the root `pom.xml`; `include` in `settings.gradle*`
- Entrypoints: `@SpringBootApplication|@QuarkusMain|public static void main\(`
- Frameworks, in build files: `spring-boot-starter-(web|webflux|data-jpa|data-mongodb|security|amqp|batch|quartz)|spring-kafka|spring-cloud|spring-statemachine|quarkus|micronaut|axon|camunda|flowable|temporal|drools|flyway|liquibase|openfeign|resilience4j|shedlock|togglz|ff4j|unleash|launchdarkly`

Layout: package-by-feature (`com.acme.orders.{api,domain,infra}`) maps packages to products directly; package-by-layer (`controller/service/repository`) needs grouping by class-name prefix; hexagonal (`domain/application/adapter`, `port/in`, `port/out`) keeps rules in `domain` and use cases in `application`.

## Phase 2 — Entities & states

Grep
- Entities: `@Entity|@Document|@Table\(|@Embeddable|@MappedSuperclass|@Aggregate(Root)?\b|@RedisHash|@Node\b`
- Table and collection names: `@Table\(\s*name\s*=\s*"|@Document\((collection\s*=\s*)?"`
- Relationships: `@(OneToMany|ManyToOne|ManyToMany|OneToOne|JoinColumn|DBRef)\b`
- Enums: `^\s*(public\s+)?enum\s+\w+`
- Lifecycle enums: `enum\s+\w*(Status|State|Type|Kind|Phase|Role|Tier|Plan|Reason)\w*`
- Enum-typed columns: `@Enumerated|@Convert\(`
- Value objects and DTOs: `^\s*public record \w+`
- Product variants: `sealed (interface|class)|@Inheritance|@DiscriminatorValue|@JsonSubTypes`
- State machines: `StateMachine|\.withExternal\(\)|\.source\(|\.target\(|canTransition|transitionTo|allowedTransitions|nextStates|EnumMap<\w*(Status|State)`
- Status writes: `\.set(Status|State)\(|this\.(status|state)\s*=[^=]`
- Rules hidden in queries: `@Query\(|findBy\w+(And|Or)\w+\(` — `WHERE status IN (...)` clauses define eligibility

## Phase 3 — Entrypoints & actors

Grep
- REST controllers: `@RestController|@Controller\b` (files), then `@(Request|Get|Post|Put|Patch|Delete)Mapping\(` (content)
- JAX-RS: `@Path\(|@(GET|POST|PUT|PATCH|DELETE)\b`
- Functional routes: `RouterFunction<|route\(\)\s*\.(GET|POST|PUT|DELETE)\(`
- gRPC and GraphQL: `@GrpcService|extends \w+ImplBase|@(Query|Mutation|Schema|Subscription)Mapping|@Dgs(Query|Mutation)`
- Schedulers: `@Scheduled\(|@SchedulerLock|@EnableScheduling|implements (Job|Tasklet)\b|cron\s*=\s*"` — a `${...}` cron resolves in `application*.yml`
- Batch: `@EnableBatchProcessing|JobBuilder|StepBuilder|ItemProcessor<`
- Message consumers: `@KafkaListener\(|@RabbitListener\(|@SqsListener\(|@JmsListener\(|@PubSubListener|@StreamListener|@Incoming\(|Consumer<\w+>\s+\w+\(\)`
- In-process events: `@EventListener|@TransactionalEventListener|@EventHandler|@SagaEventHandler|@CommandHandler`
- Topics and queues: `(topics|topicPattern|queues|destination|groupId)\s*=`; in config files: `(?i)topic|queue|exchange|routing-key`
- Producers: `KafkaTemplate|RabbitTemplate|convertAndSend\(|StreamBridge|ApplicationEventPublisher|publishEvent\(|@Outgoing\(`
- Async and retries: `@Async|CompletableFuture\.(run|supply)Async|@Retryable|@Recover|@CircuitBreaker`
- Method security: `@PreAuthorize\(|@PostAuthorize\(|@Secured\(|@RolesAllowed\(|has(Any)?(Role|Authority)\(|hasPermission\(`
- URL security: `SecurityFilterChain|requestMatchers\(|antMatchers\(|authorizeHttpRequests|permitAll\(\)|PermissionEvaluator|OncePerRequestFilter|HandlerInterceptor`
- Role catalog: `ROLE_[A-Z_]+|enum\s+\w*(Role|Permission|Authority|Scope)\w*`
- Outbound integrations: `@FeignClient\(|RestTemplate|WebClient|RestClient|@HttpExchange|@RegisterRestClient`

## Phase 4 — Business logic & guardrails

Glob
- `**/*{UseCase,Service,ServiceImpl,Handler,Policy,Validator,Specification,Calculator,Strategy,Rule,Rules}.java`

Grep
- Use cases: `@Service|@UseCase|@ApplicationService|@DomainService|@Transactional` — `@Transactional` boundaries mark use-case granularity
- Custom exceptions (the rule index): `class \w+(Exception|Error) extends` — then `throw new \w+Exception\(` with `-B 5` to capture the condition
- HTTP mapping of rejections: `@ExceptionHandler\(|@ControllerAdvice|@ResponseStatus\(|ResponseStatusException|enum\s+\w*Error(Code)?\w*`
- Validation: `@Valid\b|@Validated|@(NotNull|NotBlank|Min|Max|Size|Pattern|Positive|Future|Past|DecimalMin|DecimalMax|AssertTrue)\b|implements ConstraintValidator|Assert\.(isTrue|state|notNull)\(|Preconditions\.check`
- Money math: `BigDecimal|RoundingMode\.|\.setScale\(|\.multiply\(|\.divide\(|MonetaryAmount|Money\.of`
- Money variables: `(?i)\b\w*(fee|price|discount|tax|vat|commission|interest|penalty|refund|surcharge)\w*\s*=[^=]`
- Named constants: `static final \w+(<.+>)? [A-Z][A-Z0-9_]*\s*=`
- Inline magic numbers: `new BigDecimal\("|BigDecimal\.valueOf\(|Duration\.of\w+\(\d+|\.(plus|minus)(Days|Hours|Minutes|Months|Years)\(\d+|[<>]=?\s*\d{2,}`
- Config: `@Value\("\$\{|@ConfigurationProperties\(|getProperty\(|System\.getenv\(`
- Conditional beans: `@ConditionalOnProperty\(|@ConditionalOn(Expression|Bean|MissingBean)|@Profile\(`
- Feature flags: `(?i)feature[-_.]?(flag|toggle)|isEnabled\(|togglz|ff4j|unleash|ldclient|openfeature`; in config files: `(?i)enabled:\s*(true|false)|feature|toggle`
- Legacy paths: `(?i)@deprecated|legacy|todo|fixme|hack|workaround|temporary`, `/v1/|V1(Controller|Service)`

## Tips
- `@Value("${x.y:default}")`: the text after the colon is the effective default. `@ConditionalOnProperty(havingValue, matchIfMissing)` decides whether a whole bean — with its listeners and schedulers — exists at all. Cite both the annotation and the config line.
- Differences between `application-<profile>.yml` files reveal per-environment or per-market behaviour.
- Interface to implementation: Glob `**/*<Name>Impl.java` or grep `implements <Name>\b`.
- Kotlin (`type: "kotlin"`): same annotations; entities are `class`/`data class`, enums `enum class`, variants `sealed (class|interface)`, constants `const val` or inside `companion object`.
