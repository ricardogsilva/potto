# Potto - the pygeoapi primate
Pygeoapi logic, Starlette performance


A starlette application that wraps pygeoapi.

Quickstart for development:

```shell
# set some env variables
export PYGEOAPI_ROOT="wherever-you-cloned-pygeoapi-repo"
export POTTO__PYGEOAPI_CONFIG_FILE=pygeoapi-config-example.yml
export POTTO__LOG_CONFIG_FILE=uvicorn-log-config-example.yml
export POTTO__DEBUG=true
export POTTO__RELOAD_DIRS=$(pwd -P)

# start the server
uv run pygeoapi-starlette run-server
```

This project is a pygeoapi-powered web application written with starlette. It showcases how to build a starlette web 
application that uses pygeoapi as a library.

Currently, pygeoapi tries to offer builtin support for all of starlette, flask and django. This results in a complex 
codebase which tries to be a library and a framework at the same time. This project exists to explore a different 
approach. The vision is:

> "Let pygeoapi be a library and focus on geospatial API logic - leave web application stuff for wrapping frameworks"

The main idea behind this project is thus to clearly separate the job of core pygeoapi from whatever framework 
library is wrapping it, which in this case happens to be starlette. This means to let pygeoapi focus on geospatial 
API processing logic and let starlette worry about web application stuff.

What does it mean to let pygeoapi focus solely on the logic of geospatial APIs?

It means:

- pygeoapi core does not need to render HTML, it defers this to starlette. Therefore all of its code and configuration
  that deals with rendering HTML is not used by this project;
- pygeoapi does not need to gzip responses - this is handled by the web application framework
- pygeoapi core does not need to have configuration for the web application server because it does not need to launch it

It also means that there are additional features not currently offered by pygeoapi core which this project can 
implement in the future, like:

- User authentication
- Role-based authorization
- Allowing changes to pygeoapi configuration dynamically without needing to restart the server
- Improving async support
- etc.

Additionally, this project aims to provide a blueprint application that can be adapted for different needs.


### Name inspiration

This project's name is a hommage to the cute [potto mammal](https://en.wikipedia.org/wiki/Potto), which inhabits the
rainforests of tropical Africa. May the name serve to inspire this project to move as deliberately as a Potto in its
goal to wrap pygeoapi's core feature-set with web-related features provided by starlette.