import os
import time
import tempfile
import pathlib
import responses
import shutil
import unittest
from galaxy.jobs.mapper import JobMappingException
from tpv.rules import gateway
from tpv.commands.test import mock_galaxy

class TestScenarios(unittest.TestCase):

    @staticmethod
    def _map_to_destination(tool, user, datasets=[], tpv_config_path=None, job_conf=None, app=None):
        if job_conf:
            galaxy_app = mock_galaxy.App(job_conf=os.path.join(os.path.dirname(__file__), job_conf))
        elif app:
            galaxy_app = app
        else:
            galaxy_app = mock_galaxy.App(job_conf=os.path.join(os.path.dirname(__file__), 'fixtures/job_conf.yml'))
        job = mock_galaxy.Job()
        for d in datasets:
            job.add_input_dataset(d)
        tpv_config = tpv_config_path or os.path.join(os.path.dirname(__file__), 'fixtures/mapping-rules.yml')
        gateway.ACTIVE_DESTINATION_MAPPER = None
        print(job_conf,tpv_config)
        return gateway.map_tool_to_destination(galaxy_app, job, tool, user, tpv_config_files=[tpv_config])

    def test_scenario_esg_group_user(self):
        """
        pulsar-hm2-user is a user to specifically run jobs on hm2 with a minimum spec. Regardless of anything else.
        Each endpoint will have a user that does this.
        """
        # responses.add(
        #     method=responses.GET,
        #     url="http://stats.genome.edu.au:8086/query",
        #     body=pathlib.Path(
        #         os.path.join(os.path.dirname(__file__), 'fixtures/response-admin-group-user.yml')).read_text(),
        #     match_querystring=False,
        # )
        tool = mock_galaxy.Tool('trinity')
        user = mock_galaxy.User('pulsar-hm2-user', 'pulsar-hm2-user@unimelb.edu.au', roles=["ga_admins"])
        datasets = [mock_galaxy.DatasetAssociation("input", mock_galaxy.Dataset("input.fastq",
                                                                                file_size=1000*1024**3))]
        rules_file = os.path.join(os.path.dirname(__file__), 'fixtures/scenario-locations.yml')
        # destination = _map_to_destination(tool, user, datasets, tpv_config_path=rules_file)
        destination = self._map_to_destination(tool, user, datasets=datasets, tpv_config_path=rules_file,
                                                job_conf='fixtures/job_conf_scenario_locations.yml')
        self.assertEqual(destination.id, "pulsar_australia")

# def main():
        
#     tool = mock_galaxy.Tool('fastp')
#     user = mock_galaxy.User('jenkinsbot', 'jenkinsbot@unimelb.edu.au')
#     datasets = [mock_galaxy.DatasetAssociation("input", mock_galaxy.Dataset("input.fastq",
#                                                                             file_size=1000*1024**3))]
#     rules_file = os.path.join(os.path.dirname(__file__), 'fixtures/scenario-locations.yml')
#     # destination = _map_to_destination(tool, user, datasets, tpv_config_path=rules_file)
#     destination = _map_to_destination(tool, user, datasets=datasets, tpv_config_path=rules_file,
#                                             job_conf='fixtures/job_conf.yml')
#     print("destination: ",destination)
    # t = {'test':1}
    # v = t.values()
    # v0 = v[0]
    # v0.matches()

# main()