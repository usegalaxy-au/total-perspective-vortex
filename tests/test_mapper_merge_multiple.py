import os
import unittest

from galaxy.jobs.mapper import JobMappingException

from tpv.commands.test import mock_galaxy
from tpv.rules import gateway


class TestMapperMergeMultipleConfigs(unittest.TestCase):

    @staticmethod
    def _map_to_destination(tool, user, datasets, tpv_config_paths):
        galaxy_app = mock_galaxy.App(
            job_conf=os.path.join(os.path.dirname(__file__), "fixtures/job_conf.yml")
        )
        job = mock_galaxy.Job()
        for d in datasets:
            job.add_input_dataset(d)
        gateway.ACTIVE_DESTINATION_MAPPER = None
        return gateway.map_tool_to_destination(
            galaxy_app, job, tool, user, tpv_config_files=tpv_config_paths
        )

    def test_merge_remote_and_local(self):
        tool = mock_galaxy.Tool("bwa")
        user = mock_galaxy.User("ford", "prefect@vortex.org")

        config_first = (
            "https://github.com/galaxyproject/total-perspective-vortex/raw/main/"
            "tests/fixtures/mapping-merge-multiple-remote.yml"
        )
        config_second = os.path.join(
            os.path.dirname(__file__), "fixtures/mapping-merge-multiple-local.yml"
        )

        # a small file size should fail because of remote rule
        datasets = [
            mock_galaxy.DatasetAssociation(
                "test", mock_galaxy.Dataset("test.txt", file_size=1 * 1024**3)
            )
        ]
        with self.assertRaisesRegex(
            JobMappingException, "We don't run piddling datasets"
        ):
            self._map_to_destination(
                tool, user, datasets, tpv_config_paths=[config_first, config_second]
            )

        # a large file size should fail because of local rule
        datasets = [
            mock_galaxy.DatasetAssociation(
                "test", mock_galaxy.Dataset("test.txt", file_size=25 * 1024**3)
            )
        ]
        with self.assertRaisesRegex(
            JobMappingException, "Too much data, shouldn't run"
        ):
            self._map_to_destination(
                tool, user, datasets, tpv_config_paths=[config_first, config_second]
            )

        # an intermediate file size should compute correct values
        datasets = [
            mock_galaxy.DatasetAssociation(
                "test", mock_galaxy.Dataset("test.txt", file_size=7 * 1024**3)
            )
        ]
        destination = self._map_to_destination(
            tool, user, datasets, tpv_config_paths=[config_first, config_second]
        )
        self.assertEqual(destination.id, "k8s_environment")
        self.assertEqual(
            [
                env["value"]
                for env in destination.env
                if env["name"] == "TEST_JOB_SLOTS"
            ],
            ["4"],
        )
        self.assertEqual(destination.params["native_spec"], "--mem 8 --cores 2")
        self.assertEqual(destination.params["custom_context_remote"], "remote var")
        self.assertEqual(destination.params["custom_context_local"], "local var")
        self.assertEqual(
            destination.params["custom_context_override"], "local override"
        )

    def test_merge_local_with_local(self):
        tool = mock_galaxy.Tool("bwa")
        user = mock_galaxy.User("ford", "prefect@vortex.org")

        config_first = os.path.join(
            os.path.dirname(__file__), "fixtures/mapping-merge-multiple-remote.yml"
        )
        config_second = os.path.join(
            os.path.dirname(__file__), "fixtures/mapping-merge-multiple-local.yml"
        )

        # a small file size should fail because of remote rule
        datasets = [
            mock_galaxy.DatasetAssociation(
                "test", mock_galaxy.Dataset("test.txt", file_size=1 * 1024**3)
            )
        ]
        with self.assertRaisesRegex(
            JobMappingException, "We don't run piddling datasets"
        ):
            self._map_to_destination(
                tool, user, datasets, tpv_config_paths=[config_first, config_second]
            )

        # a large file size should fail because of local rule
        datasets = [
            mock_galaxy.DatasetAssociation(
                "test", mock_galaxy.Dataset("test.txt", file_size=25 * 1024**3)
            )
        ]
        with self.assertRaisesRegex(
            JobMappingException, "Too much data, shouldn't run"
        ):
            self._map_to_destination(
                tool, user, datasets, tpv_config_paths=[config_first, config_second]
            )

        # an intermediate file size should compute correct values
        datasets = [
            mock_galaxy.DatasetAssociation(
                "test", mock_galaxy.Dataset("test.txt", file_size=7 * 1024**3)
            )
        ]
        destination = self._map_to_destination(
            tool, user, datasets, tpv_config_paths=[config_first, config_second]
        )
        self.assertEqual(destination.id, "k8s_environment")
        self.assertEqual(
            [
                env["value"]
                for env in destination.env
                if env["name"] == "TEST_JOB_SLOTS"
            ],
            ["4"],
        )
        self.assertEqual(destination.params["native_spec"], "--mem 8 --cores 2")
        self.assertEqual(destination.params["custom_context_remote"], "remote var")
        self.assertEqual(destination.params["custom_context_local"], "local var")
        self.assertEqual(
            destination.params["custom_context_override"], "local override"
        )

    def test_merge_rules(self):
        tool = mock_galaxy.Tool("bwa")
        user = mock_galaxy.User("ford", "prefect@vortex.org")

        config_first = os.path.join(
            os.path.dirname(__file__), "fixtures/mapping-merge-multiple-remote.yml"
        )
        config_second = os.path.join(
            os.path.dirname(__file__), "fixtures/mapping-merge-multiple-local.yml"
        )

        # the highmem rule should take effect
        datasets = [
            mock_galaxy.DatasetAssociation(
                "test", mock_galaxy.Dataset("test.txt", file_size=42 * 1024**3)
            )
        ]
        with self.assertRaisesRegex(JobMappingException, "a different kind of error"):
            self._map_to_destination(
                tool, user, datasets, tpv_config_paths=[config_first]
            )

        # the highmem rule should not take effect for this size, as we've overridden it
        datasets = [
            mock_galaxy.DatasetAssociation(
                "test", mock_galaxy.Dataset("test.txt", file_size=42 * 1024**3)
            )
        ]
        destination = self._map_to_destination(
            tool, user, datasets, tpv_config_paths=[config_first, config_second]
        )
        self.assertEqual(destination.id, "another_k8s_environment")

    def test_merge_rules_with_multiple_matches(self):
        tool = mock_galaxy.Tool("hisat2")
        user = mock_galaxy.User("ford", "prefect@vortex.org")

        config_first = os.path.join(
            os.path.dirname(__file__), "fixtures/mapping-merge-multiple-remote.yml"
        )
        config_second = os.path.join(
            os.path.dirname(__file__), "fixtures/mapping-merge-multiple-local.yml"
        )

        # the highmem rule should take effect, with local override winning
        datasets = [
            mock_galaxy.DatasetAssociation(
                "test", mock_galaxy.Dataset("test.txt", file_size=42 * 1024**3)
            )
        ]
        destination = self._map_to_destination(
            tool, user, datasets, tpv_config_paths=[config_first, config_second]
        )
        self.assertEqual(destination.id, "another_k8s_environment")
        # since the last defined hisat2 contains overridden defaults, those defaults will apply
        self.assertEqual(
            [
                env["value"]
                for env in destination.env
                if env["name"] == "TEST_JOB_SLOTS"
            ],
            ["6"],
        )
        # this var is not overridden by the last defined defaults, and therefore, the remote value of cores*2 applies
        self.assertEqual(
            [
                env["value"]
                for env in destination.env
                if env["name"] == "MORE_JOB_SLOTS"
            ],
            ["12"],
        )
        self.assertEqual(destination.params["native_spec"], "--mem 18 --cores 6")

    def test_merge_rules_local_defaults_do_not_override_remote_tool(self):
        tool = mock_galaxy.Tool("toolshed.g2.bx.psu.edu/repos/iuc/disco/disco/v1.0")
        user = mock_galaxy.User("ford", "prefect@vortex.org")

        config_first = os.path.join(
            os.path.dirname(__file__), "fixtures/mapping-merge-multiple-remote.yml"
        )
        config_second = os.path.join(
            os.path.dirname(__file__), "fixtures/mapping-merge-multiple-local.yml"
        )

        # the disco rules should take effect, with local override winning
        datasets = [
            mock_galaxy.DatasetAssociation(
                "test", mock_galaxy.Dataset("test.txt", file_size=42 * 1024**3)
            )
        ]
        destination = self._map_to_destination(
            tool, user, datasets, tpv_config_paths=[config_first, config_second]
        )
        self.assertEqual(destination.id, "k8s_environment")
        # since the last defined hisat2 contains overridden defaults, those defaults will apply
        self.assertEqual(
            [
                env["value"]
                for env in destination.env
                if env["name"] == "DISCO_MAX_MEMORY"
            ],
            ["24"],
        )
        self.assertEqual(
            [
                env["value"]
                for env in destination.env
                if env["name"] == "DISCO_MORE_PARAMS"
            ],
            ["just another param"],
        )
        # this var is not overridden by the last defined defaults, and therefore, the remote value applies
        self.assertEqual(destination.params["native_spec"], "--mem 24 --cores 8")
