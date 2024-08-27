import os
import unittest

from tpv.commands.test import mock_galaxy
from tpv.rules import gateway


class TestMapperSample(unittest.TestCase):

    @staticmethod
    def _map_to_destination(tool):
        galaxy_app = mock_galaxy.App(
            job_conf=os.path.join(os.path.dirname(__file__), "fixtures/job_conf.yml")
        )
        job = mock_galaxy.Job()
        user = mock_galaxy.User("gargravarr", "fairycake@vortex.org")
        tpv_config = os.path.join(
            os.path.dirname(__file__), "fixtures/mapping-sample.yml"
        )
        gateway.ACTIVE_DESTINATION_MAPPER = None
        return gateway.map_tool_to_destination(
            galaxy_app, job, tool, user, tpv_config_files=[tpv_config]
        )

    def test_map_sample_tool(self):
        tool = mock_galaxy.Tool("sometool")
        destination = self._map_to_destination(tool)
        self.assertEqual(destination.id, "local")
        self.assertEqual(destination.params["local_slots"], "2")
