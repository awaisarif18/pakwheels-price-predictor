Best Coding Practices & Architectural Decisions to Reuse
Architecture
Separate responsibilities clearly: API, business logic, storage, execution, NLP/ML, configuration, and deployment should live in separate modules.
Use orchestration services such as JobService to coordinate components instead of putting business logic inside API routes.
Program to abstractions/interfaces, not concrete implementations. Use Protocol/abstract classes so storage, executors, and scorers can be swapped later.
Design for extensibility: new NLP tasks implement the same NLPTask interface rather than requiring API changes.
Use a registry/plugin pattern for dynamically selecting implementations such as "sentiment", "themes", etc.
Keep the core API independent of specific ML models.
Async & Background Processing
Never run heavy CPU work directly on the web server's event loop.
Use async I/O for request handling and separate execution mechanisms for CPU-heavy workloads.
For long-running work, use a job-based API:
submit → return job_id → process asynchronously → poll result.
Return 202 Accepted when work has been accepted but not completed.
Maintain explicit job states such as:
QUEUED → PROCESSING → SUCCEEDED / FAILED.
Parallel Processing
Use multiprocessing for CPU-bound ML inference, rather than blocking the application process.
Give each process its own isolated model instance.
Split large workloads into chunks, execute them in parallel, then merge the results.
Prevent CPU oversubscription; e.g. one PyTorch thread per worker when using multiple worker processes.
Do not blindly increase worker count; size workers according to CPU and RAM capacity.
API Design
Keep endpoints thin:
validate → authenticate → call service → return response.
Use strongly typed request/response schemas.
Validate input at system boundaries.
Reject:
empty required fields,
duplicates,
oversized payloads,
unsupported task types.
Use proper HTTP semantics:
202 accepted/background job
401 authentication failure
404 resource not found
413 payload too large
422 validation error
500 unexpected server error.
Data Modeling
Use Pydantic models rather than unstructured dictionaries inside application code.
Give each model a clear responsibility:
request model, internal model, response model.
Do not expose unnecessary internal data in API responses.
Example: JobDetail deliberately excludes original input items.
Configuration
Keep configuration outside source code.
Use environment variables for secrets and environment-specific settings.
Centralize configuration in one typed Settings object.
Access settings through a function such as get_settings() so tests can override them.
Never hardcode production secrets.
Security
Follow least privilege.
Run containers as a non-root user.
Drop unnecessary Linux capabilities.
Use no-new-privileges.
Do not expose application ports publicly when a reverse proxy can provide access.
Keep secrets outside container images.
Use secure/constant-time secret comparison where relevant.
Expose only the endpoints that need to be public.
Reliability
Provide separate:
Liveness check: “Is the process alive?”
Readiness check: “Can it safely receive traffic?”
Do not report readiness until expensive dependencies/models are initialized.
Warm up expensive resources during startup, not on the first customer request.
Gracefully shut down workers and allow active work time to complete where practical.
Deployment
Build immutable artifacts.
Never deploy mutable tags like latest; use commit SHA/versioned images.
Bake required model artifacts into production images where reproducibility matters.
Use a reverse proxy such as Nginx for TLS/public traffic.
Make deployment scripts fail-safe and rollback-capable.
Deploy → wait for readiness → health-check → promote version.
Roll back automatically if the new version fails.
Docker
Use small/minimal base images.
Use multi-stage or cache-efficient builds.
Copy dependency manifests before application source to maximize Docker layer caching.
Pin important tool/dependency versions.
Separate development and production Compose configuration.
Keep production runtime reproducible and immutable.
CI/CD
Split pipelines into logical stages:
Validate → Build → Deploy.
Before building, verify:
code compiles,
application imports,
authentication works,
configuration files parse,
deployment scripts have valid syntax.
Build production images only after validation succeeds.
Protect production deployment with controlled/manual approval where appropriate.
Prevent concurrent production deployments.
Testing
Test behavior without invoking expensive external systems where possible.
Mock model downloads, network calls, and heavyweight dependencies in unit tests.
Design code so dependencies can be replaced during tests.
Keep unit tests fast and deterministic.
Test both the happy path and failure/security paths.
Test configuration and authentication independently from ML inference.
Maintainability
Prefer small, focused modules and classes.
Use type hints consistently.
Keep implementation details behind interfaces.
Avoid unnecessary comments; make structure and naming explain the code.
Keep dependency direction clear:
API → Service → Abstraction → Implementation, not the reverse.
Avoid tightly coupling infrastructure decisions to business logic.
Scalability
Know whether you are scaling:
HTTP concurrency, job concurrency, or CPU computation — they are different problems.
Do not introduce distributed infrastructure before it is required.
Start simple, but create abstraction points that allow replacing:
in-memory store → Redis/PostgreSQL,
local queue → Celery/Redis,
local workers → distributed worker fleet.
Document the architectural constraints of the simple version explicitly.
A strong principle to keep
Choose the simplest architecture that satisfies today's requirements, but place clean abstraction boundaries where tomorrow's requirements are likely to change.
That is one of the strongest recurring design ideas in this project: simple implementation today, replaceable architecture tomorrow.

