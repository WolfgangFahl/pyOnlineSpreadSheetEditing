"""
Created on 2021-12-31

@author: wf
"""
import unittest

from onlinespreadsheet.editconfig import EditConfig, EditConfigManager
from ngwidgets.basetest import Basetest


class TestEditConfig(Basetest):
    """
    test handling edit configurations
    """

    def setUp(self, debug=False, profile=True):
        Basetest.setUp(self, debug=debug, profile=profile)

    def testLoadEditConfiguration(self):
        """
        test loading an edit configuration
        """
        ecm = EditConfigManager(path="/tmp/ec")
        ec = EditConfig(name="test")
        ec.sourceWikiId = "test"
        ec.targetWikiId = "test2"
        ecm.add(ec)
        ecm.save()
        ecm2 = EditConfigManager(path="/tmp/ec")
        ecm2.load()
        self.assertEqual(len(ecm.editConfigs), len(ecm2.editConfigs))
        for ec in ecm.editConfigs.values():
            self.assertTrue(ec.name in ecm2.editConfigs)
            ec2 = ecm2.editConfigs[ec.name]
            self.assertEqual(ec.__dict__, ec2.__dict__)
        pass


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
