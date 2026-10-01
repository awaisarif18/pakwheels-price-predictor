# Framework and deployment research

Verified against official documentation on 1 October 2026. This note supports the project plan. Framework capabilities below are documented facts; the choice and operating defaults are engineering recommendations for this project. No performance benchmark, cloud deployment, or model load test has been performed.

## Recommendation

Choose FastAPI with Pydantic request and response schemas, Jinja templates, and small amounts of JavaScript for the first user interface. Run the web process with Uvicorn in a Linux container. Keep collection, data preparation, training, and inference in importable Python modules, with command line entry points for the offline work.

The main reason is that the application needs two explicit prediction contracts and a reliable way to keep browser inputs, API documentation, and request validation aligned. FastAPI supplies those facilities together. It also leaves the model service independent of HTTP, which fits a modular Python application. This is a project-specific judgment, not a claim that Flask cannot support production software.

Start with one deployed web process and separate scheduled collection commands. Add a durable job queue only when job volume, retries, or concurrent operators require one. Do not train models in a request handler.

## Framework facts and their fit

| Option | Documented capabilities | Project-specific assessment |
|---|---|---|
| Flask | WSGI framework with Jinja integration; its core deliberately leaves database integration and form validation to other libraries. Application factories support isolated construction. [Design documentation](https://flask.palletsprojects.com/en/stable/design/) | Strong choice for a small traditional website. We would select and integrate validation, API schema, and dependency composition separately. That is reasonable, but adds choices already covered by FastAPI for the two-model API. |
| FastAPI | Uses Python type declarations and Pydantic for validation; generates OpenAPI and JSON Schema, supplies interactive API documentation and dependency injection. [Features documentation](https://fastapi.tiangolo.com/features/) | Best fit for a prediction service with distinct car and motorcycle schemas, constrained inputs, API consumers, and tests that substitute model services. These facilities do not validate model quality or provide a complete account-management system. |
| Django | Includes an ORM, migrations, templates, and an automatically generated admin for registered models. Its authentication framework supplies users, groups, permissions, and sessions. [Overview](https://docs.djangoproject.com/en/5.2/intro/overview/), [Authentication](https://docs.djangoproject.com/en/5.2/topics/auth/) | Prefer Django if the initial product becomes a staff-operated listing database with catalogue approval screens, account management, saved vehicles, and extensive CRUD. That is a different workload from the current public estimator plus offline review reports. |

Flask production deployment requires a dedicated WSGI server or hosting platform; its development server is unsuitable even for a privately deployed demo. Django supports both WSGI and ASGI. FastAPI documents Uvicorn deployment and optional worker processes. None of these frameworks removes the need for operational controls. [Flask production deployment](https://flask.palletsprojects.com/en/stable/deploying/), [Django deployment](https://docs.djangoproject.com/en/5.2/howto/deployment/), [FastAPI workers](https://fastapi.tiangolo.com/deployment/server-workers/).

FastAPI can render Jinja templates through `Jinja2Templates` and serve static files, so choosing it does not require a separate React application. A single deployment can supply the form and prediction API. [FastAPI templates](https://fastapi.tiangolo.com/advanced/templates/).

## Serving the prediction workload

FastAPI runs ordinary `def` route handlers and dependencies in an external thread pool. A synchronous utility function called directly by an `async def` route runs directly; FastAPI does not automatically move that call into a thread pool. Therefore, declaring an inference route asynchronous does not make blocking inference asynchronous. [FastAPI concurrency documentation](https://fastapi.tiangolo.com/async/).

Starlette documents a shared default thread pool capacity of 40 tokens. Synchronous endpoints and other synchronous work can consume the same capacity. This is a framework default, not a justified inference concurrency limit for this application's CPU allocation. [Starlette thread pool](https://starlette.dev/threadpool/).

CatBoost's `predict` accepts `thread_count`; its default `-1` uses as many threads as processor cores. It expects the features used in training and normally matching feature order, although matching feature names can replace positional matching when supplied in training and inference. [CatBoost prediction reference](https://catboost.ai/docs/en/concepts/python-reference_catboostregressor_predict).

Recommended first serving design:

- Use a normal `def` prediction route for the synchronous model service. Keep preprocessing, support checks, prediction, and response construction in the service, outside the handler.
- Begin with one Uvicorn process and `thread_count=1` per CatBoost prediction. Explicitly bound concurrent inference admission; return a controlled busy response when the chosen capacity is exceeded. Select the actual limit through load testing.
- Measure request latency, inference latency, resident memory, CPU saturation, and error rate under mixed car and motorcycle requests before adding processes or model threads.
- Keep loaded model objects read-only. Check concurrent prediction behavior for the selected library version through the integration and load tests. Do not mutate or train a shared model while requests use it.
- If measured inference becomes expensive, move it behind a bounded process pool or dedicated serving process. Processes and model copies have a memory cost; the framework alone does not improve CPU capacity.

FastAPI recommends `lifespan` for startup and shutdown resources and demonstrates loading a machine learning model before accepting requests. Worker processes normally maintain separate memory, so loading both bundles in each worker increases total RAM use. [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/), [Deployment memory discussion](https://fastapi.tiangolo.com/deployment/concepts/).

Load and validate each bundle during lifespan, including its manifest, hash, preprocessing version, feature schema, supported catalogue, and a known prediction case. Mark readiness only after the advertised models pass these checks. Expose only the vehicle types actually loaded and qualified for release. The default should fail startup when a configured required model is missing or incompatible.

FastAPI's `BackgroundTasks` runs work after a response; its documentation suggests larger tools for heavy computation distributed across processes or servers. Use separate collector and training commands for this project's durable work, with persistent run state and resumable checkpoints. [Background task guidance](https://fastapi.tiangolo.com/tutorial/background-tasks/).

## Initial hosting option and constraints

Render is a reasonable first managed host to evaluate. It supports building a Dockerfile or deploying an existing image. Its web services support environment variables, health check paths, private networking, managed TLS, scaling, and rollback. Services bind to `0.0.0.0`; the documentation recommends the port supplied by `PORT`. These are provider capabilities, not a guarantee that a particular compute tier can hold both model bundles. [Render Docker](https://render.com/docs/docker), [Render web services](https://render.com/docs/web-services).

For the private demonstration, protect access with authentication or a suitable access proxy. A web service URL is reachable from the public internet by default. An unpublished URL alone does not satisfy private access.

Render filesystems are ephemeral by default. An attached persistent disk is available to one service instance, cannot be shared with another service, prevents multiple-instance scaling, and disables zero-downtime deployment. It is unsuitable as the shared production store between a collector, training jobs, and the web service. [Render persistent disks](https://render.com/docs/disks).

Render cron jobs use UTC schedules, cannot provision or access persistent disks, and stop after 12 hours. Render allows at most one active execution of a given cron job; another scheduled execution waits, while manually triggering a run cancels the active run. The guarantee applies to one cron job, so application-level coordination is still needed when separate jobs or manual commands share a dataset. [Render cron jobs](https://render.com/docs/cronjobs).

Recommended deployment arrangement:

- One stateless web container, external object storage for versioned model bundles and datasets, and managed PostgreSQL when collection run state and snapshots need shared persistence.
- A separately scheduled collection command that stores checkpoints outside its container and exits within a bounded runtime. Split large crawls into resumable runs before using provider cron.
- A separate training command on compute selected for the training workload. Successful training produces a candidate bundle; evaluation and approval promote it into a release manifest.
- Configure the hosting health check to a readiness endpoint that verifies the release is loaded. Preserve a separate liveness endpoint for operational diagnosis. Render supports HTTP health checks. [Render health checks](https://render.com/docs/health-checks).
- Deploy an immutable code and model version pair. Keep the preceding release available for rollback. Test recovery from an empty local filesystem.

The exact provider, region, compute allocation, and scheduled collection frequency should be confirmed at the deployment milestone against measured model RAM, load-test results, Pakistan user latency, and the agreed collection volume. This plan makes those replaceable infrastructure choices rather than application assumptions.
