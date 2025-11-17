# pygeoapi-starlette

A starlette application that wraps pygeoapi.

Quickstart for development:

```shell
export PYGEOAPI_ROOT="wherever-you-cloned-pygeoapi-repo"
export PYGEOAPI_STARLETTE__PYGEOAPI_CONFIG_FILE=pygeoapi-config-example.yml
uvicorn \
    --host 0.0.0.0 \
    --port 3001 \
    --log-config uvicorn-log-config-example.yml \
    --reload \
    --factory pygeoapi_starlette.webapp.app:create_app
```

This project is a pygeoapi-powered web application written with starlette. It showcases how to build a starlette web 
application that uses pygeoapi as a library.

Currently pygeoapi tries to offer builtin support for all of starlette, flask and django. This results in a complex 
codebase which tries to be a library and a framework at the same time. This project exists to explore a different 
approach. The vision is:

"Let pygeoapi be a library and focus on geospatial API logic - leave web application stuff for wrapping frameworks"

The main idea behind this project is thus to clearly separate the job of core pygeoapi from whatever framework 
library is wrapping it, which in this case happens to be starlette. This means to let pygeoapi focus on geospatial 
API processing logic and let starlette worry about web application stuff.

What does it mean to let pygeoapi focus solely on the logic of geospatial APIs?

It means:

- pygeoapi core does not need to render HTML, it defers this to starlette. Therefore all of its code and configuration
  that deals with rendering HTML is not used by this project;
- pygeoapi core does not need to have configuration for the web application server because it does not need to launch it
