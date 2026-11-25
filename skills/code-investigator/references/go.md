# Go playbook

Patterns are ripgrep regexes for `Grep` (use `type: "go"`). Size a pattern with `output_mode: "count"` before reading its matches. Without the `Grep` and `Glob` tools, run them in Bash: `grep -rnE '<pattern>' --include='*.go' .` to search (`-c` to size, `-l` for files only) and `find . -name '<glob>'` for the Glob lists.

**Skip:** `vendor/`, `*.pb.go`, `*.pb.gw.go`, `*_gen.go`, `*.gen.go`, `zz_generated*`, `mock_*.go`, `mocks/`, and any file whose header says `Code generated ... DO NOT EDIT`. Skip `*_test.go` (`glob: "!*_test.go"`) unless a table-driven test documents the pricing or eligibility function being traced.

## Phase 1 — Topology

Glob
- `go.work`, `**/go.mod` — modules; several `go.mod` files mean several services
- `cmd/**/main.go`, `**/main.go` — one deployable per `main` (api, worker, cron, migrator, CLI)
- `internal/*/*.go` — private business code; package names under `internal/` usually read as the product catalog
- `pkg/**/*.go`, `api/**`, `**/*.proto`, `**/openapi*.{yml,yaml,json}` — shared libraries and API contracts
- `**/migrations/*.sql`, `**/schema*.sql`, `**/sqlc.yaml`, `**/ent/schema/*.go` — schema

Grep
- Frameworks, in `go.mod`: `gin-gonic|labstack/echo|go-chi|gofiber|gorilla/mux|google.golang.org/grpc|gqlgen|gorm|sqlx|sqlc|entgo|pgx|sarama|kafka-go|confluent-kafka|amqp|nats|asynq|riverqueue|temporal|robfig/cron|gocron|viper|envconfig|cobra`
- Wiring, in `cmd/**/main.go`: `New\w+\(|\.Run\(|ListenAndServe|\.Serve\(` — `main` names every dependency and background loop
- Ports (use cases and integrations): `^type \w+(Service|Repository|Store|Client|Gateway|Publisher|Provider) interface`

Layout: domain-first (`internal/<domain>/{handler,service,repository}.go`) maps packages to products directly; layer-first (`internal/{handler,service,repository}/<domain>.go`) needs grouping by file name.

## Phase 2 — Entities & states

Glob
- `internal/**/{domain,model,models,entity,entities,types}/**/*.go`

Grep
- Structs: `^type \w+ struct` (scope to domain/model directories first; repo-wide it is noisy)
- Persisted structs: `(gorm|db|bson|dynamodbav|pg):"`
- Tables: `func \(\w*\s*\*?\w+\) TableName\(\)`, and `CREATE TABLE` in `*.sql`
- Custom status types: `^type \w*(Status|State|Type|Kind|Phase|Role|Tier|Plan|Reason)\w* (string|u?int\d*)`
- `iota` enums: `\biota\b` with `-B 2 -A 10` to capture the whole block
- String-valued enums: `^\s+\w*(Status|State|Type|Role)\w+\s+(\w+\s+)?=\s*"`
- Transitions: `\.(Status|State)\s*=[^=]`, `switch\s+\w+(\.\w+)*\.(Status|State)`, `func \(.+\) (Can|Transition|MoveTo|Mark|Set(Status|State))\w*\(`, `looplab/fsm|qmuntal/stateless`
- Contracts, in `*.proto`: `^\s*(service|rpc|message|enum) \w+`

## Phase 3 — Entrypoints & actors

Glob
- `**/*.graphqls`, `**/gqlgen.yml` — GraphQL schema

Grep
- net/http, chi, gorilla, fiber routes: `\.(HandleFunc|Handle|Get|Post|Put|Patch|Delete|Method|Route|Mount|Group)\(`
- gin, echo routes: `\.(GET|POST|PUT|PATCH|DELETE|Any|Group)\(`
- Go 1.22 method patterns: `"(GET|POST|PUT|PATCH|DELETE) /`
- gRPC and gateway: `Register\w+Server\(|Unimplemented\w+Server|Register\w+Handler(FromEndpoint)?\(`
- CLI commands: `cobra\.Command\{|Use:\s+"`
- Tickers and crons: `time\.NewTicker\(|time\.Tick\(|time\.AfterFunc\(|cron\.New\(|\.AddFunc\(|gocron\.|\.Every\(`
- Consumers: `\.Subscribe\(|\.QueueSubscribe\(|\.Consume\(|ConsumeClaim\(|\.ReadMessage\(|\.FetchMessage\(|ReceiveMessage\(|\.Receive\(ctx|asynq\.NewServeMux|river\.AddWorker|RegisterWorkflow|RegisterActivity`
- Producers: `\.Publish\(|\.Produce\(|\.WriteMessages\(|SendMessage\(|\.Enqueue\(|asynq\.NewTask\(`
- Goroutines: `\bgo func\(|\bgo \w+(\.\w+)*\(|errgroup\.` (scope to `cmd/` and service packages)
- Background loops: `for \{|case <-\w+\.C:|<-ctx\.Done\(\)`
- Middleware and auth: `\.Use\(|func \w*(Auth|Require|Permission|Role|Admin|RBAC|Scope)\w*\(|(Unary|Stream)Interceptor|casbin|jwt\.Parse|\.HasRole\(|\.HasPermission\(|IsAdmin`
- Role catalog: `Role\w*\s+(\w+\s+)?=\s*"|"(admin|owner|superadmin|operator|merchant)"`
- Outbound integrations: `http\.NewRequest|resty\.New|\w+\.NewClient\(|stripe\.|twilio|sendgrid|aws-sdk-go`

## Phase 4 — Business logic & guardrails

Grep
- Sentinel errors (the rule index): `Err[A-Z]\w*\s*=\s*(errors\.New|fmt\.Errorf)\(` — then grep each `ErrXxx` name to find the guard that returns it
- Typed errors: `^type \w+Error struct|func \(\w+ \*?\w+\) Error\(\) string`
- Rejection codes: `codes\.(FailedPrecondition|PermissionDenied|InvalidArgument|ResourceExhausted|AlreadyExists)|http\.Status(Forbidden|Conflict|UnprocessableEntity|PaymentRequired|TooManyRequests)`
- Guard functions: `func (\(.+\) )?(Can|Is|Has|Validate|Check|Ensure|Allow|Eligible)\w*\(`
- Money variables: `(?i)\b\w*(fee|price|amount|discount|tax|vat|commission|interest|penalty|refund|surcharge|margin)\w*\s*(:=|=|\*=|\+=)`
- Money math: `decimal\.New\w*\(|\.Mul\(|\.Div\(|\.Round(Bank|Up|Down)?\(|math\.(Round|Ceil|Floor)\(|big\.NewRat`
- Named limits: `^\s*(const\s+)?\w*(Max|Min|Limit|Threshold|Default|Timeout|TTL|Days|Hours|Percent|Rate|Fee|Cap|Quota)\w*\s*(\w+\s*)?=\s*[\d"]`
- Inline magic numbers: `\d+\s*\*\s*time\.(Hour|Minute|Second)|[<>]=?\s*\d{2,}`
- Config: `os\.(Getenv|LookupEnv)\(|viper\.(Get\w*|SetDefault|BindEnv)\(|envconfig\.Process|env:"\w+|envDefault:"|mapstructure:"|flag\.(String|Bool|Int|Duration)\(`
- Feature flags: `(?i)feature_?flags?|\bFF_\w+|ENABLE_\w+|\w+_ENABLED|launchdarkly|ldclient|unleash|flagsmith|growthbook|openfeature|flipt|BoolVariation\(|IsEnabled\(`
- Legacy paths: `(?i)deprecated|legacy|todo|fixme|hack|workaround|temporary`, `/v1/|\bv1\.`

## Tips
- `viper.SetDefault` and `envDefault:"` hold the effective production value whenever the variable is unset — cite the default, not only the variable name.
- Errors get wrapped (`fmt.Errorf("...: %w", ErrX)`): grep the sentinel's name, not its message, to find every site that enforces the rule.
- Interface to implementation: grep `func \(\w+ \*?\w+\) <MethodName>\(` to land on the concrete method.
- Each `cmd/*/main.go` wires exactly what that binary runs — the fastest way to tell which consumers and tickers are live.
