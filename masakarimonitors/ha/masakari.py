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

import eventlet
from keystoneauth1.identity.generic import password as ks_password
from keystoneauth1 import session as ks_session
from openstack import connection
from openstack import exceptions
from oslo_log import log as oslo_logging

import masakarimonitors.conf

LOG = oslo_logging.getLogger(__name__)
CONF = masakarimonitors.conf.CONF


class SendNotification(object):

    def _make_client(self):
        auth = ks_password.Password(
            auth_url=CONF.api.auth_url,
            username=CONF.api.username,
            password=CONF.api.password,
            user_domain_id=CONF.api.user_domain_id,
            project_name=CONF.api.project_name,
            project_domain_id=CONF.api.project_domain_id)
        session = ks_session.Session(auth=auth)
        conn = connection.Connection(session=session)

        return conn.instance_ha

    def send_notification(self, api_retry_max, api_retry_interval, event):
        """Send a notification.

        This method sends a notification to the masakari-api.

        :param api_retry_max: Number of retries when the notification
            processing is error.
        :param api_retry_interval: Trial interval of time of the notification
            processing is error.
        :param event: dictionary of event that included in notification.
        """

        LOG.info("Send a notification. %s", event)

        # Get client.
        client = self._make_client()

        # Send a notification.
        retry_count = 0
        while True:
            try:
                response = client.create_notification(
                    type=event['notification']['type'],
                    hostname=event['notification']['hostname'],
                    generated_time=event['notification']['generated_time'],
                    payload=event['notification']['payload'])

                LOG.info("Response: %s", response)
                break

            except Exception as e:
                if isinstance(e, exceptions.HttpException):

                    # TODO(samP): Remove attribute check and else case if
                    # openstacksdk is bumped up from '>=0.9.19' to '>=0.10.0'
                    # in global-requirements.
                    if hasattr(e, 'status_code'):
                        is_status_409 = e.status_code == 409
                    else:
                        is_status_409 = e.http_status == 409

                    if is_status_409:
                        msg = ("Stop retrying to send a notification because "
                               "same notification have been already sent.")
                        LOG.info("%s", msg)
                        break

                if retry_count < api_retry_max:
                    LOG.warning("Retry sending a notification. (%s)", e)
                    retry_count = retry_count + 1
                    eventlet.greenthread.sleep(api_retry_interval)
                else:
                    LOG.exception("Exception caught: %s", e)
                    break
