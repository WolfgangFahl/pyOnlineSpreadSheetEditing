"""
Created on 2024-03-18

separating ui and functional concerns
@author: wf
"""

import typing
from dataclasses import dataclass
from enum import Enum


class SyncStatus(Enum):
    """
    synchronization status
    """
    IN_SYNC = "✓"
    SYNC_POSSIBLE = ""
    OUT_SYNC = "❌"


class SyncAction(Enum):
    """
    synchronization action
    """
    LEFT_SYNC = "←"
    RIGHT_SYNC = "→"
    NOTHING = ""
    SYNC = "⇆"

    def __missing__(self, _key):
        return self.NOTHING


@dataclass
class ComparisonData:
    """
    Stores the property name and the values to compare
    """
    property_name: str
    left_value: typing.Any
    right_value: typing.Any
    chosen_sync_option: SyncAction = None

    def get_sync_status(self):
        """
        compare the left and right value and return their sync status
        """
        status = None
        if str(self.left_value) == str(self.right_value):
            status = SyncStatus.IN_SYNC
        elif self.left_value is None or self.right_value is None:
            status = SyncStatus.SYNC_POSSIBLE
        else:
            status = SyncStatus.OUT_SYNC
        return status

    def get_chosen_sync_option(self) -> SyncAction:
        """
        chosen sync action to apply to the compared property values
        Returns:
            SyncAction: section to apply
        """
        if self.chosen_sync_option is not None:
            action = self.chosen_sync_option
        else:
            action = self.suggested_sync_action()
        return action

    def suggested_sync_action(self) -> SyncAction:
        """
        Evaluates the data difference and suggests a Sync Action
        """
        status = self.get_sync_status()
        if status is SyncStatus.SYNC_POSSIBLE:
            if self.left_value is None:
                action = SyncAction.LEFT_SYNC
            else:
                action = SyncAction.RIGHT_SYNC
        else:
            action = SyncAction.NOTHING
        return action


class ComparisonRecord:
    """
    Compares two dicts
    """

    def __init__(
        self,
        left_source_name: str,
        left_record: dict,
        right_source_name: str,
        right_record: dict,
    ):
        """
        constructor
        Args:
            left_record: record to compare
            right_record: record to compare
        """
        self.left_source_name = left_source_name
        self.right_source_name = right_source_name
        if left_record is None:
            left_record = dict()
        if right_record is None:
            right_record = dict()
        self.comparison_data = dict()
        property_names = []
        for p in list(left_record.keys()) + list(right_record.keys()):
            if p not in property_names:
                property_names.append(p)
        for property_name in property_names:
            cd = ComparisonData(
                property_name=property_name,
                left_value=left_record.get(property_name, None),
                right_value=right_record.get(property_name, None),
            )
            self.comparison_data[property_name] = cd

    def get_update_records(self) -> typing.Tuple[dict, dict]:
        """
        Get the update records for both sides

        Returns:
            (dict, dict): updates that should be applied to both sides
        """
        update_left = dict()
        update_right = dict()
        for cd in self.comparison_data.values():
            action = cd.get_chosen_sync_option()
            if action is SyncAction.LEFT_SYNC:
                # right to left
                update_left[cd.property_name] = cd.right_value
            elif action is SyncAction.RIGHT_SYNC:
                # left to right
                update_right[cd.property_name] = cd.left_value
        return update_left, update_right

    def get_update_record_of(self, source_name: str) -> dict:
        """
        Get the update record for the given source name
        Args:
            source_name: name of one of the sources

        Returns:
            dict: update for the given source
        """
        update_rec_left, update_rec_right = self.get_update_records()
        update_record = dict()
        if source_name == self.left_source_name:
            update_record = update_rec_left
        elif source_name == self.right_source_name:
            update_record = update_rec_right
        return update_record


@dataclass
class SyncRequest:
    """
    Synchronization request containing the sync action to apply and the corresponding data
    """
    action: SyncAction
    data: ComparisonRecord
