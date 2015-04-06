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

def _build_instances_index():
    global INSTANCES_NAME_INDEX
    global INSTANCES_IP_INDEX
    INSTANCES_NAME_INDEX = {}
    INSTANCES_IP_INDEX= {}

    for instance in INSTANCES_CACHE:
        if not instance["name"] in INSTANCES_NAME_INDEX:
            INSTANCES_NAME_INDEX[instance["name"]] = instance

        ip = instance["networkInterfaces"][0]["accessConfigs"][0]["natIP"]
        if not ip in INSTANCES_IP_INDEX:
            INSTANCES_IP_INDEX[ip] = instance

def _get_data(use_cache, cache_expiration):
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

        raw_data = subprocess.check_output("gcloud compute instances list --format=json", shell=True)
        data = json.loads(raw_data)

        if use_cache and not loaded_cache:
            f = open(cache_file_path, "w")
            try:
                f.write(raw_data)
            finally:
                f.close()

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

                address = i["networkInterfaces"][0]["accessConfigs"][0]["natIP"]
                if not address in roles[role]:
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

def target_pool_add_instance(target_pool_name, instance_name, instance_zone):
    raw_data = subprocess.check_output("gcloud compute target-pools add-instances {target_pool} --instances {instance_name} --zone {zone} --format json".format(target_pool=target_pool_name, instance_name=instance_name, zone=instance_zone), shell=True)

def target_pool_remove_instance(target_pool_name, instance_name, instance_zone):
    raw_data = subprocess.check_output("gcloud compute target-pools remove-instances {target_pool} --instances {instance_name} --zone {zone} --format json".format(target_pool=target_pool_name, instance_name=instance_name, zone=instance_zone), shell=True)

def update_roles_gce(use_cache=True, cache_expiration=86400, cache_path="~/.gcetools/instances"):
    """
    Dynamically update fabric's roles by using assigning the tags associated with
    each machine in Google Compute Engine.

    use_cache - will store a local cache in ~/.gcetools/
    cache_expiration - cache expiration in seconds (default: 1 day)
    cache_path - the path to store instances data (default: ~/.gcetools/instances)

    How to use:
    - Call 'update_roles_gce' at the end of your fabfile.py (it will run each
      time you run fabric).
    - On each function use the regular @roles decorator and set the role to the name
      of one of the tags associated with the instances you wish to work with
    """
    data = _get_data(use_cache, cache_expiration)
    roles = _get_roles(data)
    env.roledefs.update(roles)

    _data_loaded = True


__all__ = [
    "update_roles_gce",
    "get_instance_by_ip",
    "get_instance_by_name",
    "get_instance_name_by_ip",
    "get_instance_zone_by_ip",
    "get_instance_zone_by_name",
    "target_pool_add_instance",
    "target_pool_remove_instance"
]
