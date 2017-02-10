# The MIT License (MIT)
#
# Copyright (c) 2015 Eran Sandler
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import absolute_import
import subprocess
import os.path
import time
from os.path import expanduser
try:
    import simplejson as json
except ImportError:
    import json

from fabric.api import env

_gcloud_exists = None
_data_loaded = False
_gcloud_version = None

INSTANCES_CACHE = None
INSTANCES_NAME_INDEX = {}
INSTANCES_IP_INDEX = {}

def _check_gcloud():
    gcloud_version = None
    try:
        gcloud_version = subprocess.check_output("gcloud version", shell=True)
    except subprocess.CalledProcessError:
        raise Exception("Failed to run 'gcloud version'. That means you don't have gcloud installed or it's not part of the path.\nTo install gcutil see https://cloud.google.com/sdk/\nPrevious versions of fabric_gce_tools used gcutil which is about to be deprecated.")

    _gcloud_exists = (gcloud_version != None)

    if _gcloud_exists:
        _gcloud_version = int(gcloud_version.split("\n")[0].split(" ")[-1].split(".")[0])

def _get_zone_flag_name():
    global _gcloud_version
    if _gcloud_version < 138:
        return "--zone"

    return "--instances-zone"


def _build_instances_index():
    global INSTANCES_NAME_INDEX
    global INSTANCES_IP_INDEX
    INSTANCES_NAME_INDEX = {}
    INSTANCES_IP_INDEX= {}

    for instance in INSTANCES_CACHE:
        if instance.get("name") != None and not instance["name"] in INSTANCES_NAME_INDEX:
            INSTANCES_NAME_INDEX[instance["name"]] = instance
            instanceData = instance
        elif instance.get("instance") != None:
            ## need to retrieve the instance itself, we're coming from an instance group
            raw_instance_data = subprocess.check_output("gcloud compute instances describe %s --format=json" % instance["instance"].split("/")[-1], shell=True)
            instanceData = json.loads(raw_instance_data)

        ip = instanceData.get("networkInterfaces", [{}])[0].get("accessConfigs", [{}])[0].get("natIP", None)
        if ip and not ip in INSTANCES_IP_INDEX:
            INSTANCES_IP_INDEX[ip] = instanceData

def _get_data(use_cache, cache_expiration, group_name=None, region=None, zone=None):
    global INSTANCES_CACHE

    loaded_cache = False
    execute_command = True
    data = None

    cache_path = os.path.join(expanduser("~"), ".gcetools")
    cache_file_path = os.path.join(cache_path, "instances")

    if use_cache:
        if not os.path.exists(cache_path):
            os.makedirs(cache_path)

        if os.path.exists(cache_file_path):
            created_timestamp = os.path.getctime(cache_file_path)
            if created_timestamp + cache_expiration > time.time():
                f = open(cache_file_path, "r")
                try:
                    raw_data = f.read()
                    data = json.loads(raw_data)
                    execute_command = False
                    loaded_cache = True
                finally:
                    f.close()

    if execute_command:
        global _gcloud_exists

        if _gcloud_exists is None:
            _check_gcloud()
        else:
            if not _gcloud_exists:
                raise Exception("Can't find 'gcloud'. That means you don't have gcutil installed or it's not part of the path.\nTo install gcutil see https://cloud.google.com/sdk/")

        if group_name != None:
            if region is not None:
                region_or_zone =  " --region=%s" % region
            elif zone is not None:
                region_or_zone = " --zone=%s" % zone
            else:
                region_or_zone = ""
            raw_data = subprocess.check_output("gcloud compute instance-groups managed list-instances %s%s --format=json" % (group_name, region_or_zone), shell=True)
            data = json.loads(raw_data)
        else:
            raw_data = subprocess.check_output("gcloud compute instances list --format=json", shell=True)
            data = json.loads(raw_data)

    INSTANCES_CACHE = data
    _build_instances_index()
    return data

def _get_roles(data):
    roles = {}
    for i in data:
        if "tags" in i and i["tags"] and "items" in i["tags"]:
            for t in i["tags"]["items"]:
                role = t
                if not role in roles:
                    roles[role] = []

                address = i.get("networkInterfaces", [{}])[0].get("accessConfigs", [{}])[0].get("natIP", None)
                if address and not address in roles[role]:
                    roles[role].append(address)

    return roles

def get_instance_by_name(name):
    if not _data_loaded:
        update_roles_gce()

    if name in INSTANCES_NAME_INDEX:
        return INSTANCES_NAME_INDEX[name]

    return None

def get_instance_by_ip(ip):
    if not _data_loaded:
        update_roles_gce()

    if ip in INSTANCES_IP_INDEX:
        return INSTANCES_IP_INDEX[ip]

    return None

def get_instance_name_by_ip(ip):
    instance = get_instance_by_ip(ip)
    if instance:
        return instance["name"]

    return None

def get_instance_zone_by_name(name):
    instance = get_instance_by_name(name)
    if instance:
        return instance["zone"]

    return None

def get_instance_zone_by_ip(ip):
    instance = get_instance_by_ip(ip)
    if instance:
        return instance["zone"]

    return None

def get_instances_by_group(group, region, zone):
    return update_roles_gce(group_name=group, region=region, zone=zone)

def target_pool_add_instance(target_pool_name, instance_name, instance_zone):
    raw_data = subprocess.check_output("gcloud compute target-pools add-instances {target_pool} --instances {instance_name} {zone_flag} {zone} --format json".format(target_pool=target_pool_name, instance_name=instance_name, zone_flag=_get_zone_flag_name(), zone=instance_zone), shell=True)

def target_pool_remove_instance(target_pool_name, instance_name, instance_zone):
    raw_data = subprocess.check_output("gcloud compute target-pools remove-instances {target_pool} --instances {instance_name} {zone_flag} {zone} --format json".format(target_pool=target_pool_name, instance_name=instance_name, zone_flag=_get_zone_flag_name(), zone=instance_zone), shell=True)
    
def update_roles_gce(use_cache=True, cache_expiration=86400, cache_path="~/.gcetools/instances", group_name=None, region=None, zone=None):
    """
    Dynamically update fabric's roles by using assigning the tags associated with
    each machine in Google Compute Engine.

    use_cache - will store a local cache in ~/.gcetools/
    cache_expiration - cache expiration in seconds (default: 1 day)
    cache_path - the path to store instances data (default: ~/.gcetools/instances)
    group_name - optional managed instance group to use instead of the global instance pool
    region - gce region name (such as `us-central1`) for a regional managed instance group
    zone - gce zone name (such as `us-central1-a`) for a zone managed instance group

    How to use:
    - Call 'update_roles_gce' at the end of your fabfile.py (it will run each
      time you run fabric).
    - On each function use the regular @roles decorator and set the role to the name
      of one of the tags associated with the instances you wish to work with
    """
    data = _get_data(use_cache, cache_expiration, group_name=group_name, region=region, zone=zone)
    roles = _get_roles(data)
    env.roledefs.update(roles)

    _data_loaded = True
    return INSTANCES_CACHE


__all__ = [
    "update_roles_gce",
    "get_instance_by_ip",
    "get_instance_by_name",
    "get_instance_name_by_ip",
    "get_instance_zone_by_ip",
    "get_instance_zone_by_name",
    "get_instances_by_group",
    "target_pool_add_instance",
    "target_pool_remove_instance"
]
