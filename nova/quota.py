# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Quotas for instances, volumes, and floating ips."""

from nova import db
from nova import exception
from nova import flags


FLAGS = flags.FLAGS
flags.DEFINE_integer('quota_instances', 10,
                     'number of instances allowed per project')
flags.DEFINE_integer('quota_cores', 20,
                     'number of instance cores allowed per project')
flags.DEFINE_integer('quota_ram', 50 * 1024,
                     'megabytes of instance ram allowed per project')
flags.DEFINE_integer('quota_volumes', 10,
                     'number of volumes allowed per project')
flags.DEFINE_integer('quota_gigabytes', 1000,
                     'number of volume gigabytes allowed per project')
flags.DEFINE_integer('quota_floating_ips', 10,
                     'number of floating ips allowed per project')
flags.DEFINE_integer('quota_metadata_items', 128,
                     'number of metadata items allowed per instance')
flags.DEFINE_integer('quota_max_injected_files', 5,
                     'number of injected files allowed')
flags.DEFINE_integer('quota_max_injected_file_content_bytes', 10 * 1024,
                     'number of bytes allowed per injected file')
flags.DEFINE_integer('quota_max_injected_file_path_bytes', 255,
                     'number of bytes allowed per injected file path')


def get_quota(context, project_id):
    rval = {
        'instances': FLAGS.quota_instances,
        'cores': FLAGS.quota_cores,
        'ram': FLAGS.quota_ram,
        'volumes': FLAGS.quota_volumes,
        'gigabytes': FLAGS.quota_gigabytes,
        'floating_ips': FLAGS.quota_floating_ips,
        'metadata_items': FLAGS.quota_metadata_items,
    }

    quota = db.quota_get_all_by_project(context, project_id)
    for key in rval.keys():
        if key in quota:
            rval[key] = quota[key]
    return rval


def _get_request_allotment(requested, used, quota):
    if quota is None:
        return requested
    return quota - used


def allowed_instances(context, num_instances, instance_type):
    """Check quota and return min(num_instances, allowed_instances)."""
    project_id = context.project_id
    context = context.elevated()
    num_cores = num_instances * instance_type['vcpus']
    num_ram = num_instances * instance_type['memory_mb']
    usage = db.instance_data_get_for_project(context, project_id)
    used_instances, used_cores, used_ram = usage
    quota = get_quota(context, project_id)
    allowed_instances = _get_request_allotment(num_instances, used_instances,
                                               quota['instances'])
    allowed_cores = _get_request_allotment(num_cores, used_cores,
                                           quota['cores'])
    allowed_ram = _get_request_allotment(num_ram, used_ram, quota['ram'])
    allowed_instances = min(allowed_instances,
                            allowed_cores // instance_type['vcpus'],
                            allowed_ram // instance_type['memory_mb'])
    return min(num_instances, allowed_instances)


def allowed_volumes(context, num_volumes, size):
    """Check quota and return min(num_volumes, allowed_volumes)."""
    project_id = context.project_id
    context = context.elevated()
    size = int(size)
    num_gigabytes = num_volumes * size
    used_volumes, used_gigabytes = db.volume_data_get_for_project(context,
                                                                  project_id)
    quota = get_quota(context, project_id)
    allowed_volumes = _get_request_allotment(num_volumes, used_volumes,
                                             quota['volumes'])
    allowed_gigabytes = _get_request_allotment(num_gigabytes, used_gigabytes,
                                               quota['gigabytes'])
    allowed_volumes = min(allowed_volumes,
                          int(allowed_gigabytes // size))
    return min(num_volumes, allowed_volumes)


def allowed_floating_ips(context, num_floating_ips):
    """Check quota and return min(num_floating_ips, allowed_floating_ips)."""
    project_id = context.project_id
    context = context.elevated()
    used_floating_ips = db.floating_ip_count_by_project(context, project_id)
    quota = get_quota(context, project_id)
    allowed_floating_ips = _get_request_allotment(num_floating_ips,
                                                  used_floating_ips,
                                                  quota['floating_ips'])
    return min(num_floating_ips, allowed_floating_ips)


def allowed_metadata_items(context, num_metadata_items):
    """Check quota; return min(num_metadata_items,allowed_metadata_items)."""
    project_id = context.project_id
    context = context.elevated()
    quota = get_quota(context, project_id)
    allowed_metadata_items = _get_request_allotment(num_metadata_items, 0,
                                                    quota['metadata_items'])
    return min(num_metadata_items, allowed_metadata_items)


def allowed_injected_files(context):
    """Return the number of injected files allowed."""
    return FLAGS.quota_max_injected_files


def allowed_injected_file_content_bytes(context):
    """Return the number of bytes allowed per injected file content."""
    return FLAGS.quota_max_injected_file_content_bytes


def allowed_injected_file_path_bytes(context):
    """Return the number of bytes allowed in an injected file path."""
    return FLAGS.quota_max_injected_file_path_bytes


class QuotaError(exception.ApiError):
    """Quota Exceeeded."""
    pass
