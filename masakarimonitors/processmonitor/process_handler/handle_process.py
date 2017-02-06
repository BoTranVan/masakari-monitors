# Copyright(c) 2016 Nippon Telegraph and Telephone Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_log import log as oslo_logging

import masakarimonitors.conf
from masakarimonitors.i18n import _LE
from masakarimonitors.i18n import _LI
from masakarimonitors.i18n import _LW
from masakarimonitors import utils

LOG = oslo_logging.getLogger(__name__)
CONF = masakarimonitors.conf.CONF


class HandleProcess(object):
    """Handle process."""

    def __init__(self):
        self.process_list = None

    def set_process_list(self, process_list):
        """Set process list object.

        :param process_list: process list object
        """
        self.process_list = process_list

    def _execute_cmd(self, cmd_str, run_as_root):

        # Split command string and delete empty elements.
        command = cmd_str.split(' ')
        command = filter(lambda x: x != '', command)

        try:
            # Execute start command.
            out, err = utils.execute(*command,
                                     run_as_root=run_as_root)

            if out:
                msg = ("CMD '%s' output stdout: %s") % (cmd_str, out)
                LOG.info(_LI("%s"), msg)

            if err:
                msg = ("CMD '%s' output stderr: %s") % (cmd_str, err)
                LOG.warning(_LW("%s"), msg)
                return 1

        except Exception as e:
            msg = ("CMD '%s' raised exception: %s") % (cmd_str, e)
            LOG.error(_LE("%s"), e)
            return 1

        return 0

    def start_processes(self):
        """Initial start of processes.

        This method starts the processes using start command written in the
        process list.
        """
        for process in self.process_list:
            cmd_str = process['start_command']

            # Execute start command.
            LOG.info(
                _LI("Start of process with executing command: %s"), cmd_str)
            self._execute_cmd(cmd_str, process['run_as_root'])
