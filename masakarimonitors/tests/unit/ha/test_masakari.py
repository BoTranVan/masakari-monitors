# Copyright(c) 2017 Nippon Telegraph and Telephone Corporation
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

import mock
import testtools
import uuid

import eventlet
from keystoneauth1.identity.generic import password as ks_password
from keystoneauth1 import session as ks_session
from openstack import connection
from openstack import exceptions
from openstack import service_description
from oslo_utils import timeutils

from masakarimonitors.ha import masakari
from masakarimonitors.objects import event_constants as ec

PROFILE_TYPE = "ha"
PROFILE_NAME = "masakari"


class FakeResponse(object):

    def __init__(self, status_code=200, headers=None):
        self.status_code = status_code
        self.headers = {
            'content-type': 'application/json',
            'x-openstack-request-id': uuid.uuid4().hex,
        }


class TestSendNotification(testtools.TestCase):

    def setUp(self):
        super(TestSendNotification, self).setUp()
        self.api_retry_max = 3
        self.api_retry_interval = 1
        self.event = {
            'notification': {
                'type': ec.EventConstants.TYPE_COMPUTE_HOST,
                'hostname': 'compute-node1',
                'generated_time': timeutils.utcnow(),
                'payload': {
                    'event': ec.EventConstants.EVENT_STOPPED,
                    'cluster_status': 'OFFLINE',
                    'host_status': ec.EventConstants.HOST_STATUS_NORMAL
                }
            }
        }

    @mock.patch.object(connection, 'Connection')
    @mock.patch.object(service_description, 'ServiceDescription')
    @mock.patch.object(ks_session, 'Session')
    @mock.patch.object(ks_password, 'Password')
    def test_send_notification(self, mock_password, mock_session,
        mock_service_description, mock_connection):

        mock_conn = mock.Mock()
        mock_client = mock.Mock()
        mock_conn.ha.proxy_class.return_value = mock_client
        mock_connection.return_value = mock_conn

        notifier = masakari.SendNotification()
        notifier.send_notification(
            self.api_retry_max, self.api_retry_interval, self.event)

        mock_client.create_notification.assert_called_once_with(
            type=self.event['notification']['type'],
            hostname=self.event['notification']['hostname'],
            generated_time=self.event['notification']['generated_time'],
            payload=self.event['notification']['payload'])

    @mock.patch.object(connection, 'Connection')
    @mock.patch.object(service_description, 'ServiceDescription')
    @mock.patch.object(ks_session, 'Session')
    @mock.patch.object(ks_password, 'Password')
    def test_send_notification_409_error(self, mock_password, mock_session,
        mock_service_description, mock_connection):

        mock_conn = mock.Mock()
        mock_client = mock.Mock()
        mock_conn.ha.proxy_class.return_value = mock_client
        mock_connection.return_value = mock_conn

        # TODO(samP): Remove attribute check and else case if
        # openstacksdk is bumped up from '>=0.9.19' to '>=0.10.0'
        # in global-requirements.
        if hasattr(exceptions.HttpException(), 'status_code'):
            response = FakeResponse(status_code=409)
            status_ex = exceptions.HttpException(response=response)
        else:
            status_ex = exceptions.HttpException(http_status=409)

        mock_client.create_notification.side_effect = status_ex
        notifier = masakari.SendNotification()
        notifier.send_notification(
            self.api_retry_max, self.api_retry_interval, self.event)

        mock_client.create_notification.assert_called_once_with(
            type=self.event['notification']['type'],
            hostname=self.event['notification']['hostname'],
            generated_time=self.event['notification']['generated_time'],
            payload=self.event['notification']['payload'])

    @mock.patch.object(eventlet.greenthread, 'sleep')
    @mock.patch.object(connection, 'Connection')
    @mock.patch.object(service_description, 'ServiceDescription')
    @mock.patch.object(ks_session, 'Session')
    @mock.patch.object(ks_password, 'Password')
    def test_send_notification_500_error(self, mock_password, mock_session,
        mock_service_description, mock_connection, mock_sleep):

        mock_conn = mock.Mock()
        mock_client = mock.Mock()
        mock_conn.ha.proxy_class.return_value = mock_client
        mock_connection.return_value = mock_conn

        # TODO(samP): Remove attribute check and else case if
        # openstacksdk is bumped up from '>=0.9.19' to '>=0.10.0'
        # in global-requirements.
        if hasattr(exceptions.HttpException(), 'status_code'):
            response = FakeResponse(status_code=500)
            status_ex = exceptions.HttpException(response=response)
        else:
            status_ex = exceptions.HttpException(http_status=500)

        mock_client.create_notification.side_effect = status_ex
        mock_sleep.return_value = None

        notifier = masakari.SendNotification()
        notifier.send_notification(
            self.api_retry_max, self.api_retry_interval, self.event)

        mock_client.create_notification.assert_called_with(
            type=self.event['notification']['type'],
            hostname=self.event['notification']['hostname'],
            generated_time=self.event['notification']['generated_time'],
            payload=self.event['notification']['payload'])
        self.assertEqual(self.api_retry_max + 1,
                         mock_client.create_notification.call_count)
