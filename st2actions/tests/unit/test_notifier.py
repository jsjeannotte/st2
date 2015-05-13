# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import mock
import unittest2

import st2tests.config as tests_config
tests_config.parse_args()

from st2actions.notifier import Notifier
from st2common.constants.triggers import INTERNAL_TRIGGER_TYPES
from st2common.models.db.action import LiveActionDB, NotificationSchema
from st2common.models.db.action import NotificationSubSchema
from st2common.persistence.action import Action
from st2common.models.system.common import ResourceReference

ACTION_TRIGGER_TYPE = INTERNAL_TRIGGER_TYPES['action'][0]
NOTIFY_TRIGGER_TYPE = INTERNAL_TRIGGER_TYPES['action'][1]
MOCK_EXECUTION_ID = '287r8383t5BDSVBNVDNBVD'


class NotifierTestCase(unittest2.TestCase):

    class MockDispatcher(object):
        def __init__(self, tester):
            self.tester = tester
            self.notify_trigger = ResourceReference.to_string_reference(
                pack=NOTIFY_TRIGGER_TYPE['pack'],
                name=NOTIFY_TRIGGER_TYPE['name'])
            self.action_trigger = ResourceReference.to_string_reference(
                pack=ACTION_TRIGGER_TYPE['pack'],
                name=ACTION_TRIGGER_TYPE['name'])

        def dispatch(self, *args, **kwargs):
            try:
                self.tester.assertEqual(len(args), 1)
                self.tester.assertTrue('payload' in kwargs)
                payload = kwargs['payload']

                if args[0] == self.notify_trigger:
                    self.tester.assertEqual(payload['status'], 'succeeded')
                    self.tester.assertTrue('execution_id' in payload)
                    self.tester.assertEqual(payload['execution_id'], MOCK_EXECUTION_ID)
                    self.tester.assertTrue('start_timestamp' in payload)
                    self.tester.assertTrue('end_timestamp' in payload)
                    self.tester.assertEqual('core.local', payload['action_ref'])
                    self.tester.assertEqual('Action succeeded.', payload['message'])
                    self.tester.assertTrue('data' in payload)
                    self.tester.assertTrue('run-local-cmd', payload['runner_ref'])

                if args[0] == self.action_trigger:
                    self.tester.assertEqual(payload['status'], 'succeeded')
                    self.tester.assertTrue('execution_id' in payload)
                    self.tester.assertEqual(payload['execution_id'], MOCK_EXECUTION_ID)
                    self.tester.assertTrue('start_timestamp' in payload)
                    self.tester.assertEqual('core.local', payload['action_name'])
                    self.tester.assertEqual('core.local', payload['action_ref'])
                    self.tester.assertTrue('result' in payload)
                    self.tester.assertTrue('parameters' in payload)
                    self.tester.assertTrue('run-local-cmd', payload['runner_ref'])

            except Exception:
                self.tester.fail('Test failed')

    @mock.patch.object(Action, 'get_by_ref', mock.MagicMock(
        return_value={'runner_type': {'name': 'run-local-cmd'}}))
    @mock.patch.object(Notifier, '_get_execution_id', mock.MagicMock(
        return_value=MOCK_EXECUTION_ID))
    def test_notify_triggers(self):
        liveaction = LiveActionDB(action='core.local')
        liveaction.description = ''
        liveaction.status = 'succeeded'
        liveaction.parameters = {}
        on_success = NotificationSubSchema(message='Action succeeded.')
        on_failure = NotificationSubSchema(message='Action failed.')
        liveaction.notify = NotificationSchema(on_success=on_success,
                                               on_failure=on_failure)
        liveaction.start_timestamp = datetime.datetime.utcnow()

        dispatcher = NotifierTestCase.MockDispatcher(self)
        notifier = Notifier(connection=None, queues=[], trigger_dispatcher=dispatcher)
        notifier.process(liveaction)
