# -*- coding: utf-8 -*-
# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright (c) 2010-2012, GEM Foundation.
#
# OpenQuake is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# OpenQuake is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with OpenQuake.  If not, see <http://www.gnu.org/licenses/>.


"""
Utility functions related to monitoring.
"""


import subprocess

from openquake.db import models


def monitor_compute_nodes(job):
    """Check what compute nodes are running and return the delta (if any).

    :param int job_id: identifier of the job at hand
    :return: a 2-tuple where the first and second element is a list of compute
        nodes that became available and unavailable since the last call.
    """
    from_celery = _get_cnode_status()
    in_db = _get_cnode_status_in_db(job)

    # compute nodes known to celery
    cns = set(node for node, status in from_celery.iteritems()
              if status == "OK")
    # compute nodes stored in the db
    dbns = set(node for node, status in in_db.iteritems() if status == "up")

    # Which nodes stored in the db have gone bad/down?
    for node in dbns - cns:
        status = "error" if node in from_celery else "down"
        ns = models.NodeStats(oq_job=job, node=node, status=status)

def _get_cnode_status():
    """Get compute node status (from celery).

    :return: a dict with compute node status info e.g.
        `{"oqt": "OK", "usc": "ERROR"}`
    """
    csi = subprocess.check_output("cd /usr/openquake; celeryctl status -C",
                                  shell=True)
    csi = csi.splitlines()
    # now we should have data like this:
    # ['gemsun02: OK', 'gemsun01: OK', 'gemsun03: OK', 'gemsun04: OK',
    #  'gemmicro02: OK', 'bigstar04: OK', 'gemmicro01: OK', '',
    #  '7 nodes online.']
    return dict(tuple(cs.split(": ")) for cs in csi if cs.find(":") > -1)


def _get_cnode_status_in_db(job):
    """Get compute node status stored in the database.

    :param int job_id: identifier of the job at hand
    :return: a potentially empty dictionary where the keys are node names
        and the values are either 'up' or 'down' e.g.
        `{"N1": "up", "N2": "down", "N3": "error"}`
    """
    dbi = models.NodeStats.objects.filter(oq_job=job).order_by("updated_at")
    return dict((ns.node, ns.status) for ns in dbi)
