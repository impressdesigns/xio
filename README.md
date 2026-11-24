# Xio

A command-line data helper for Core.

```powershell
xio api /me                                         # an authenticated GET to Core
xio api /sales-orders/ -X GET -f limit=500 --paginate --jq '.items[].number'
xio api /things/ -f name=Widget -F count=3          # fields with no -X are POSTed as JSON
xio api /things/1 -X PATCH --input changes.json     # a body from a file, or - for stdin

xio run script.py --its-own --options           # a script, in Xio's environment

xio auth login    # sign in through the Azure CLI
xio auth status   # who is signed in, and when the Core token runs out
xio auth token    # print a bearer token
xio doctor        # environment report as JSON
```

`xio api` takes the options of `gh api`: `-X`, `-f`, `-F`, `-H`, `--input`, `--paginate`, `--jq` and
`--include`. Fields are the query string of a GET and the JSON body of anything else. A failed
request prints the response body and exits non-zero.

## Scripts

When a call needs a loop or some logic, write a script with no dependency header and run it with
`xio run`. It runs in Xio's own environment, so it creates none, and it imports a signed-in client:

```python
from xio import core

for order in core.get("/sales-orders/", params={"limit": 500}).json()["items"]:
    print(order["number"])
```

`core` is a `niquests` session with Core's base URL and a token set. A package the script needs is
added to the one environment with
`uv tool install idi-xio --with <package>`.

## Settings

Every setting has a default and is overridden by an environment variable:

| Variable | Default |
| --- | --- |
| `XIO_TENANT` | The Impress Designs directory |
| `XIO_DEFAULT_SERVICE` | `core` |
| `XIO_TIMEOUT_SECONDS` | `60` |
| `XIO_CORE_URL`, `XIO_CORE_SCOPE` | Core and its sign-in scope |

Settings come from the environment only. Xio does not read a `.env` file.

## Install

From a checkout:

```powershell
uv tool install --editable .
```

A release installs with `uv tool install idi-xio`. Requests need the
[Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), signed in with `xio auth login`.

Working on Xio: [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md).

## License

[Apache-2.0](LICENSE).
