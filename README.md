# fabric-gce-tools - Tools to integrate Fabric with Google Compute Engine (GCE)

Tools to integrate Fabric with Google Compute Engine (GCE).

- Automagically assign all your servers roles in Fabric based on the tags assigned to each instance in GCE.
- Caches the result of `gcloud compute instances list` so you won't have to hit the API every time
- Helper functions such as:
    - *get_instance_name_by_ip* - get instance name by IP address (when using roles and fabric uses the IP and you want to get the current instance name based on the IP of the currently executing host)
    - *get_instance_zone_by_ip* - get the instance zone by it's IP adddress - useful for command that requires sending the instance zone since newer versions of `gcloud` do not perform a name lookup in all zones.
    - *get_instance_zone_by_name* - get the instance zone by the instance name
    - *target_pool_add_instance* - add an instance to a target pool
    - *target_pool_remove_instance* - remove an instance from a target pool

Feel free to send pull requests with additional helpers that you wrote and use with Fabric and GCE.

## Installation
* `pip install fabric-gce-tools`

## Example fabfile
```python
from fabric.api import *
from fabric_gce_tools import *

def take_server_out_of_lb():
    instance_name = get_instance_name_by_ip(env["host_string"])
    instance_zone = get_instance_zone_by_ip(env["host_string"])
    target_pool_remove_instance("my-target-pool", instance_name, instance_zone)

def take_server_into_lb():
    instance_name = get_instance_name_by_ip(env["host_string"])
    instance_zone = get_instance_zone_by_ip(env["host_string"])
    target_pool_add_instance("my-target-pool", instance_name, instance_zone)

@task
@roles("webserver")
def deploy_server():
    take_server_out_of_lb()
    run("do something")
    take_server_into_lb()

# Runs every time you run "fab something".
# Add it at the end of the file to make sure it runs each time.
update_roles_gce()
```
