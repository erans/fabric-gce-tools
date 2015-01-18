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
try:
    import simplejson as json
except ImportError:
    import json

from fabric.api import env

_gcutil_exists = None

def _check_gcutil():
    gcutil_version = None
    try:
        gcutil_version = subprocess.check_output("gcutil version", shell=True)
    except subprocess.CalledProcessError:
        raise Exception("Failed to run 'gcutil version'. That means you don't have gcutil installed or it's not part of the path.\nTo install gcutil see https://cloud.google.com/sdk/")

    _gcutil_exists = (gcutil_version != None)

def update_roles_gce():
    """
    Dynamically update fabric's roles by using assigning the tags associated with
    each machine in Google Compute Engine.

    How to use:
    - Call 'update_roles_gce' at the end of your Fabfile (it will run each time you run fabric).
    - On each function use the regular @roles decorator and set the role to the name
      of one of the tags associated with the instances you wish to work with
    """
    global _gcutil_exists

    if _gcutil_exists is None:
        _check_gcutil()
    else:
        if not _gcutil_exists:
            raise Exception("Can't find 'gcutil'. That means you don't have gcutil installed or it's not part of the path.\nTo install gcutil see https://cloud.google.com/sdk/")

    roles = {}

    raw_data = subprocess.check_output("gcutil listinstances --format=json", shell=True)
    data = json.loads(raw_data)

    for z in data["items"]:
        if "instances" in data["items"][z]:
            for i in data["items"][z]["instances"]:
                if "tags" in i and i["tags"] and "items" in i["tags"]:
                    for t in i["tags"]["items"]:
                        role = t
                        if not role in roles:
                            roles[role] = []

                        address = i["networkInterfaces"][0]["accessConfigs"][0]["natIP"]
                        if not address in roles[role]:
                            roles[role].append(address)

    env.roledefs.update(roles)

__all__ = ["update_roles_gce"]
