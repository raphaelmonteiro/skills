# PHP playbook (Laravel, Symfony, Doctrine)

Patterns are ripgrep regexes for `Grep` (use `type: "php"`). Without the `Grep` and `Glob` tools, run them in Bash: `grep -rnE '<pattern>' --include='*.php' .` to search (`-l` for files only) and `find . -name '<glob>'` for the Glob lists. An `artisan` file at the root means Laravel; `bin/console` plus `config/bundles.php` means Symfony.

**Skip:** `vendor/`, `node_modules/`, `storage/`, `bootstrap/cache/`, `var/`, `public/build/`, `_ide_helper*.php`, compiled views. Skip `tests/Unit/**`; keep `tests/Feature/**`, Behat `features/**/*.feature`, and Pest/PHPUnit tests named in business language.

## Phase 1 — Topology

Read `composer.json` first (it is short): `autoload.psr-4` maps namespaces to directories (`App\\` → `app/`, `Domain\\` → `src/Domain/`), which is the map of where business code lives; `require` lists the framework and integrations.

Glob
- `{Modules,modules,packages}/*/{composer,module}.json`, `{src,app/Domain,app/Modules}/*/*` — bounded contexts of a modular monolith
- `config/*.php`, `config/packages/*.yaml`, `config/services.yaml`, `.env.example` — config and toggles
- `database/migrations/*.php`, `migrations/*.php` — schema history
- `database/seeders/*.php` — reference data: roles, plans, statuses

Grep
- Stack, in `composer.json`: `laravel/(framework|horizon|cashier|sanctum|passport|pennant|nova|octane)|symfony/(framework-bundle|messenger|workflow|scheduler|security-bundle)|doctrine/orm|api-platform|spatie/laravel-(permission|model-states|activitylog)|filament|livewire|stripe|php-amqplib|rdkafka`
- Hidden wiring, in `app/Providers/*.php` and `bootstrap/app.php`: `bind\(|singleton\(|Event::listen\(|Gate::define\(|Route::bind\(|::observe\(`

## Phase 2 — Entities & states

Glob
- `app/Models/**/*.php`, `app/**/Models/*.php`, `src/Entity/**/*.php`, `src/**/Domain/**/*.php`
- `app/Enums/**/*.php`, `src/**/Enum/**/*.php`, `config/packages/workflow.yaml`

Grep
- Eloquent models: `extends (Model|Authenticatable|Pivot)\b`
- Model shape: `protected \$(table|fillable|guarded|casts|attributes)\b|function casts\(\)`
- Relationships: `(hasMany|hasOne|belongsTo|belongsToMany|hasManyThrough|morphTo|morphMany|morphToMany)\(`
- Named business filters: `function scope[A-Z]\w+\(|#\[Scope\]|addGlobalScope\(`
- Doctrine entities: `#\[ORM\\(Entity|Table|Embeddable|MappedSuperclass)|@ORM\\(Entity|Table)|#\[ODM\\Document`
- Doctrine relationships: `ORM\\(OneToMany|ManyToOne|ManyToMany|OneToOne)`
- Schema: `Schema::(create|table)\(|\benum\(\s*'|foreignId\(|CREATE TABLE`
- Enums (PHP 8.1+): `^\s*enum \w+(\s*:\s*(string|int))?`, and their cases: `^\s*case \w+(\s*=.+)?;`
- Status constants: `const \w*(STATUS|STATE|TYPE|ROLE)\w*\s*=`
- Enum casts: `=>\s*\w+(Status|State|Type|Kind)::class`
- State machines: `extends State\b|allowTransition\(|transitionTo\(|canTransitionTo\(|WorkflowInterface|workflow\.\w+\.(guard|transition|completed)|#\[AsGuardListener`
- Status writes: `(->|::\$)(status|state)\s*=[^=]|'(status|state)'\s*=>|setStatus\(|markAs[A-Z]\w+\(`

## Phase 3 — Entrypoints & actors

Glob
- `routes/**/*.php`, `{Modules,modules}/*/{routes,Routes}/*.php`, `config/routes.yaml`, `config/routes/*.yaml`
- `app/Http/{Controllers,Requests,Middleware}/**/*.php`, `src/Controller/**/*.php`
- `app/{Jobs,Listeners,Events,Observers,Notifications,Mail}/**/*.php`, `src/{MessageHandler,EventSubscriber,EventListener}/**/*.php`
- `app/Console/Commands/**/*.php`, `app/Console/Kernel.php`, `routes/console.php`, `src/Command/**/*.php`
- `app/Policies/**/*.php`, `src/Security/**/*.php`, `config/packages/{security,messenger}.yaml`
- `app/{Livewire,Filament,Nova}/**/*.php` — back-office screens: operator roles and manual actions

Grep
- Laravel routes: `Route::(get|post|put|patch|delete|any|match|resource|apiResource|group|prefix|middleware|controller)\(`
- Symfony and API Platform routes: `#\[Route\(|@Route\(|#\[ApiResource|#\[(Get|GetCollection|Post|Put|Patch|Delete)\(`
- Request validation: `function (rules|authorize)\(\)|validate\(\[|Validator::make\(|#\[Assert\\`
- Queued jobs: `implements ShouldQueue|ShouldBeUnique|::dispatch(Sync|If|Unless|AfterResponse)?\(|dispatch\(new |Bus::(chain|batch)\(|onQueue\(`
- Events and listeners: `protected \$listen|Event::listen\(|event\(new |::observe\(|#\[ObservedBy|#\[AsEventListener|getSubscribedEvents`
- Model hooks (hidden side effects): `function (creating|created|updating|updated|saving|saved|deleting|deleted)\(|static::(creating|created|saving|saved|updating|updated|deleting)\(`
- Console schedules: `Schedule::(command|job|call)\(|\$schedule->(command|job|call|exec)\(|\b(cron|daily\w*|hourly\w*|everyMinute|every\w+Minutes|weekly\w*|monthly\w*)\(`
- Commands: `protected \$signature|#\[AsCommand\(`
- Symfony Messenger and Scheduler: `#\[AsMessageHandler|MessageHandlerInterface|#\[As(Schedule|PeriodicTask|CronTask)`
- Webhooks: `(?i)webhook`
- Laravel policies and gates: `Gate::(define|allows|denies|authorize|before)\(|authorize\(|\bcan(not|any)?\(|@can\b|middleware\(\[?'(auth|can|role|permission|abilities|scope)|has(Any)?Role\(|hasPermissionTo\(|tokenCan\(`
- Symfony security: `#\[IsGranted\(|isGranted\(|denyAccessUnlessGranted\(|extends Voter|ROLE_[A-Z_]+`; in `security.yaml`: `access_control|role_hierarchy`
- Outbound integrations: `Http::(get|post|put|patch|delete|withToken|baseUrl)|GuzzleHttp|HttpClientInterface|Stripe\\|Twilio|Mail::|Notification::`

## Phase 4 — Business logic & guardrails

Glob
- `app/{Services,Actions,Domain,Support,Rules,Exceptions,Features}/**/*.php`, `src/{Service,Domain,Application,Exception}/**/*.php`
- `**/*{Service,Action,Handler,UseCase,Calculator,Policy,Rule,Validator,Specification}.php`
- `config/{features,pennant}.php`

Grep
- Use-case methods: `function (handle|execute|__invoke)\(`
- Custom exceptions (the rule index): `class \w+(Exception|Error) extends` — then `throw new \w+` with `-B 5` to capture the condition
- Other rejections: `abort\(\s*\d{3}|abort_(if|unless)\(|throw_(if|unless)\(|ValidationException::withMessages|Response::deny|\$fail\(`
- Validation rules: `implements (ValidationRule|Rule)\b|Rule::(in|exists|unique|requiredIf|when)\(`
- Rules hidden in queries: `where(In|NotIn|Between|Date|Null|NotNull|Has|DoesntHave)?\(|andWhere\(|createQueryBuilder\(` (scope to Services, Repositories and model scopes)
- Money variables: `(?i)\$\w*(fee|price|amount|discount|tax|vat|commission|interest|penalty|refund|surcharge|subtotal|total)\w*\s*[-+*/]?=[^=>]`
- Money math: `bc(mul|div|add|sub)\(|\b(round|ceil|floor|number_format)\(|Money::|new Money\(|multipliedBy\(|\*\s*0\.\d+|/\s*100\b`
- Magic numbers: `const \w+\s*=\s*[\d'"]|(private|protected|public) (static )?(int|float|string) \$\w+\s*=\s*[\d'"]|[<>]=?\s*\d{2,}|(add|sub)(Days|Hours|Minutes|Months|Years)\(\d+`
- Config: `config\(['"][\w.-]+['"]|env\(['"]\w+['"]|Config::get\(|getenv\(|\$_ENV|%env\(|#\[Autowire\(|getParameter\(`
- Feature flags (Pennant): `Feature::(active|inactive|define|for|when|unless|value|allAreActive|someAreActive)\(|@feature\b|EnsureFeaturesAreActive`
- Feature flags (other): `(?i)feature[_-]?flags?|\w+_ENABLED|ENABLE_\w+|launchdarkly|unleash|growthbook|flagception`
- Legacy paths: `(?i)@deprecated|#\[Deprecated|legacy|todo|fixme|hack|workaround|temporary`, `/v1/|\\V1\\`

## Tips
- Laravel hides flow behind facades, observers, model events, global scopes, accessors/mutators (`Attribute::make\(|function (get|set)\w+Attribute\(`) and middleware aliases. When a trace seems to skip a step, check the service providers and the model's `boot`/`booted` methods.
- `env('X', default)` and `config('a.b', default)`: the second argument is the effective value when the variable is unset. Follow `config()` keys into `config/*.php` and cite the real default there.
- Controller to route: grep the controller class name in `routes/`. `Route::resource` expands into seven actions; `apiResource` into five.
- Symfony autowiring hides wiring in `config/services.yaml` and attributes (`#[AsMessageHandler]`, `#[AsEventListener]`); `messenger.yaml` `routing` shows which messages are async.
