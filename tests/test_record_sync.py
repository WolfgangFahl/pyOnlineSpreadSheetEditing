from ngwidgets.basetest import Basetest

from onlinespreadsheet.record_sync import (
    ComparisonData,
    ComparisonRecord,
    SyncAction,
    SyncStatus,
)


class TestRecordSync(Basetest):
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

    def test_comparison_record_sync(self):
        """
        Test to verify the correct suggestion of synchronization actions for differing records and
        ensure the update records reflect the suggested actions accurately.
        """

        left_record = {"name": "Alice", "email": "alice@example.com"}
        right_record = {"name": "Alice", "email": None}

        comparison_record = ComparisonRecord(
            left_source_name="Left",
            left_record=left_record,
            right_source_name="Right",
            right_record=right_record,
        )

        # Test sync suggestion
        for comp_data in comparison_record.comparison_data.values():
            if comp_data.property_name == "email":
                self.assertEqual(
                    SyncAction.RIGHT_SYNC, comp_data.suggested_sync_action()
                )

        # Test update records
        update_left, update_right = comparison_record.get_update_records()
        self.assertEqual({"email": "alice@example.com"}, update_right)

    def tests_get_update_records(self):
        """
        tests get_update_records
        """
        test_params = [  # (input_left, input_right, update_left, update_right)
            (
                {"A": "1", "C": "3", "D": "4"},
                {"B": "2", "D": "4"},
                {"B": "2"},
                {"A": "1", "C": "3"},
            ),
            ({"B": "2"}, None, dict(), {"B": "2"}),
        ]
        for test_param in test_params:
            with self.subTest(test_param=test_param):
                (
                    input_left,
                    input_right,
                    expected_update_left,
                    expected_update_right,
                ) = test_param
                comparison_record = ComparisonRecord(
                    "left", input_left, "right", input_right
                )
                update_left, update_right = comparison_record.get_update_records()
                self.assertDictEqual(expected_update_left, update_left)
                self.assertDictEqual(expected_update_right, update_right)
