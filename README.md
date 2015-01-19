# fabric-gce-tools - Tools to integrate Fabric with Google Compute Engine (GCE)

Tools to integrate Fabric with Google Compute Engine (GCE).

- Automagically assign all your servers roles in Fabric based on the tags assigned to each instance in GCE.
- Feel free to send pull requests with additional helpers that you wrote and use with Fabric and GCE.

## Installation
* `pip install fabric-gce-tools`

## Example fabfile
```python
from fabric.api import *
from fabric_gce_tools import *

@roles("webserver")
def deploy_server():
    run("do something")

# Runs every time you run "fab something".
# Add it at the end of the file to make sure it runs each time.
update_roles_gce()
```
