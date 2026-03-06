# Potto - the pygeoapi primate
An opinionated starlette+fastapi application that wraps pygeoapi.

Quickstart for development:

```shell
# start the docker compose stack
docker compose -f docker/compose.dev.yaml up -d --force-recreate

# set some env variables
export PYGEOAPI_ROOT="wherever-you-cloned-pygeoapi-repo"
POTTO__DATABASE_DSN="postgresql+psycopg://potto:pottopass@localhost:55432/potto"
export POTTO__DEBUG=true
export POTTO__PYGEOAPI_CONFIG_FILE=pygeoapi-config-example.yml
export POTTO__RELOAD_DIRS=$(pwd -P)
export POTTO__UVICORN_LOG_CONFIG_FILE=uvicorn-log-config-example.yml

# start the server
uv run potto run-server
```

This project is a pygeoapi-powered web application written with starlette and FastAPI. It showcases how to use 
pygeoapi as a library and makes some very opinionated choices along the way.

Currently, pygeoapi offers builtin support for all of starlette, flask and django. This results in a complex 
codebase which tries to be a library and a framework at the same time. This project exists to explore a different 
approach. The idea is to clearly separate the job of core pygeoapi from whatever framework library is wrapping it, 
which in this case happens to be starlette and fastapi. This means to let pygeoapi focus on geospatial API processing 
logic exclusively.

What does it mean to let pygeoapi focus solely on the logic of geospatial APIs?

It means that there is a split responsibility between pygeoapi and the wrapping framework with regard to implementing
the more 'webby' features of OGC APIs, like rendering HTML, generating links and openapi schemas, etc.

In Potto, this translates to:

- pygeoapi core does not render HTML, it defers this to starlette. Therefore, all of its code and configuration
  that deals with rendering HTML is not used by this project. Potto includes all its templates and renders them. This 
  also has the advantage that the templates can take full advantage of the template processing library which they are
  targeting (which in Potto's case is [Jinja]), instead of having to try to support multiple templating libraries, as
  is the case with vanilla pygeoapi

- pygeoapi core does not generate links - this is handled by the web application framework
- pygeoapi core does not gzip responses - this is handled by the web application framework
- pygeoapi core does not have configuration for the web application server because it does not need to launch it
- pygeoapi core does not need to generate an OpenAPI document, this is a job for the web framework

It also means that there are additional features not currently offered by pygeoapi core which this project can 
implement in the future, like:

- Allowing changes to pygeoapi configuration dynamically without needing to restart the server
- User authentication
- Role-based authorization
- Improving async support
- etc.


### OGC API compliance notes

Potto presents a single OGC API compliant landing page under `/api/` with the main media type of responses being of the
JSON family. It also has a web UI under `/` - the web UI is intentionally not OGC API compliant. The reason being 
that the author is of the opinion that replicating all OGC API path operations in a UI results in an overly 
complicated user experience.


### Name inspiration

This project's name is a hommage to the cute [potto mammal](https://en.wikipedia.org/wiki/Potto), which inhabits the
rainforests of tropical Africa. May the name serve to inspire this project to move as deliberately as a potto in its
goal to wrap pygeoapi's core feature-set with web-related features provided by starlette and fastapi.