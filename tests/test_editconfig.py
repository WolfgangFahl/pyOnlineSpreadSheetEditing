"""
Created on 2021-12-31

@author: wf
"""

from onlinespreadsheet.editconfig import EditConfig, EditConfigs
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
        path="/tmp/ec/editConfigs.yaml"
        ecm = EditConfigs()
        ec = EditConfig(name="test")
        ec.sourceWikiId = "test"
        ec.targetWikiId = "test2"
        ecm.add(ec)
        ecm.save(path)
        ecm2=EditConfigs.load(path)
        self.assertEqual(len(ecm.editConfigs), len(ecm2.editConfigs))
        for ec in ecm.editConfigs.values():
            self.assertTrue(ec.name in ecm2.editConfigs)
            ec2 = ecm2.editConfigs[ec.name]
            self.assertEqual(ec.__dict__, ec2.__dict__)
        pass