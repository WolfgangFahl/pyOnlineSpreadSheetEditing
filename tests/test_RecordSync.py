import unittest

from tests.basetest import BaseTest
from wd.RecordSync import ComparisonData, ComparisonRecord, SyncDialog, SyncStatus


class TestComparisonData(BaseTest):
    """
    tests RecordSync
    """

    def test_get_sync_status(self):
        """
        tests get_sync_status
        """
        test_params = [
            (SyncStatus.IN_SYNC, "world", "world"),
            (SyncStatus.SYNC_POSSIBLE, None, "world"),
            (SyncStatus.SYNC_POSSIBLE, "world", None),
            (SyncStatus.IN_SYNC, None, None),
            (SyncStatus.OUT_SYNC, "world", "Hello"),
        ]
        for test_param in test_params:
            with self.subTest(test_param=test_param):
                expected, left_value, right_value = test_param
                cd = ComparisonData("label", left_value, right_value)
                self.assertEqual(expected, cd.get_sync_status())


class TestComparisonRecord(BaseTest):
    """
    tests ComparisonRecord
    """

    def tests_get_update_records(self):
        """
        tests get_update_records
        """
        test_params = [  # (input_left, input_right, update_left, update_right)
            ({"A": "1", "C": "3", "D": "4"}, {"B": "2", "D": "4"}, {"B": "2"}, {"A": "1", "C": "3"}),
            ({"B": "2"}, None, dict(), {"B": "2"})
        ]
        for test_param in test_params:
            with self.subTest(test_param=test_param):
                input_left, input_right, expected_update_left, expected_update_right = test_param
                comparison_record = ComparisonRecord("left", input_left, "right", input_right)
                update_left, update_right = comparison_record.get_update_records()
                self.assertDictEqual(expected_update_left, update_left)
                self.assertDictEqual(expected_update_right, update_right)


class TestSyncDialog(BaseTest):
    """
    tests SyncDialog
    """

    @staticmethod
    def sync_dialog_page():
        """
        Returns SyncDialog as webpage
        """
        import justpy as jp
        wp = jp.WebPage()  # head_html='<script src="https://cdn.tailwindcss.com"></script>')
        div = jp.Div(a=wp, classes="container mx-auto")
        cr = ComparisonRecord(
                left_source_name="dblp",
                left_record={"A": "1", "C": "3", "D": "Test value for long entries"},
                right_source_name="wikidata",
                right_record={"B": "2", "D": "4",  "C": 5}
        )
        SyncDialog(comparison_record=cr, a=div)
        return wp

    @unittest.skip("For manual debugging")
    def test_interface(self):
        import justpy as jp
        jp.justpy(self.sync_dialog_page, host="localhost", port=8442)

