import typing
from dataclasses import dataclass
from enum import Enum
import justpy as jp


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

    def __missing__(self, key):
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
    Compares two list of dicts
    """

    def __init__(
            self,
            left_source_name: str,
            left_record: dict,
            right_source_name: str,
            right_record: dict
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
                    right_value=right_record.get(property_name, None)
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


class SyncDialog(jp.Div):
    """
    dialog widget to synchronize two data records
    """

    def __init__(
            self,
            comparison_record: ComparisonRecord,
            sync_callback: typing.Callable[[SyncRequest], None] = None,
            value_enhancement_callback: typing.Callable[['SyncDialogRow'], None] = None,
            **kwargs):
        """
        constructor
        """
        super(SyncDialog, self).__init__(**kwargs)
        div = jp.Div(a=self, classes="flex flex-col")
        self.comparison_record = comparison_record
        if sync_callback is None:
            sync_callback = self.__fallback_sync_callback
        self.sync_callback = sync_callback
        self.content_div = jp.Table(a=div, classes="table-auto w-full border-x border-b")
        self.header = jp.Tr(a=jp.Thead(a=self.content_div), classes="")
        self.setup_header()
        self.rows = []
        self.table_body = jp.Tbody(a=self.content_div)
        for cd in self.comparison_record.comparison_data.values():
            sdr = SyncDialogRow(cd, a=self.table_body, classes="")
            self.rows.append(sdr)
        self.controls_div = jp.Div(a=div, classes="flex justify-end m-2")
        self.setup_controls()
        self.value_enhancement_callback = value_enhancement_callback
        self.enhance_row_values()


    def setup_header(self):
        """
        setup header column
        """
        jp.Th(a=self.header, text="Property")
        jp.Th(a=self.header, text=self.comparison_record.left_source_name)
        action_header = jp.Th(a=self.header, style="width:60px")
        color = "grey"
        selector = EnumSelector(
                enum=SyncAction,
                exclude=[SyncAction.NOTHING],
                a=action_header,
                value=SyncAction.SYNC.name,
                on_change=self.handle_sync_action_change
        )
        jp.Th(a=self.header, text=self.comparison_record.right_source_name)

    def setup_controls(self):
        div = jp.Div(a=self.controls_div, classes="flex flex-row gap-2 ")
        classes = "bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
        btn_sync_left = jp.Button(
                a=div,
                text=f"update {self.comparison_record.left_source_name}",
                on_click=self.handle_sync_left_click,
                classes=classes
        )
        btn_sync_left = jp.Button(
                a=div,
                text=f"update both",
                on_click=self.handle_sync_click,
                classes=classes
        )
        btn_sync_left = jp.Button(
                a=div,
                text=f"update {self.comparison_record.right_source_name}",
                on_click=self.handle_sync_right_click,
                classes=classes
        )

    def handle_sync_action_change(self, msg):
        """
        Handles change in selected global sync action
        """
        global_action = SyncAction[msg.value]
        for row in self.rows:
            new_action = row.comparison_data.chosen_sync_option
            if global_action in [SyncAction.LEFT_SYNC, SyncAction.RIGHT_SYNC]:
                # apply selected sync action to all rows
                new_action = global_action
            elif global_action is SyncAction.SYNC:
                new_action = row.comparison_data.suggested_sync_action()
            row.comparison_data.chosen_sync_option = new_action
            row.sync_action_selector.value=new_action.name

    def handle_sync_left_click(self, _msg):
        self.handover_sync_callback(SyncAction.LEFT_SYNC)

    def handle_sync_right_click(self, _msg):
        self.handover_sync_callback(SyncAction.RIGHT_SYNC)

    def handle_sync_click(self, _msg):
        self.handover_sync_callback(SyncAction.SYNC)

    def handover_sync_callback(self, action: SyncAction):
        """
        Generates the SyncRequest and hands it over to the defined callback function
        Args:
            action: sync action to apply
        """
        sync_request = SyncRequest(action=action, data=self.comparison_record)
        self.sync_callback(sync_request)

    def __fallback_sync_callback(self, req: SyncRequest):
        """
        Fallback Sync handler
        """
        msg = f"No synchronization callback defined {req}"
        print(msg)

    def enhance_row_values(self):
        """
        Enhance the row values
        """
        for row in self.rows:
            if self.value_enhancement_callback is not None:
                self.value_enhancement_callback(row)


class SyncDialogRow(jp.Tr):
    """
    row in the SyncDialog
    """

    def __init__(self, data: ComparisonData, **kwargs):
        """
        constructor
        Args:
            data: data to compare/sync in this row
        """
        super(SyncDialogRow, self).__init__(**kwargs)
        self.comparison_data = data
        row_color = self.get_row_color()
        cell_classes = f"border border-green-600 mx-2 my-1 p-2 {row_color}"
        self.property_name_div = jp.Td(
                a=self,
                text=self.comparison_data.property_name,
                classes=cell_classes
        )
        self.left_value_div = jp.Td(
                a=self,
                text=self.comparison_data.left_value,
                classes=cell_classes
        )
        self.sync_status_div = jp.Td(
                a=self,
                classes=cell_classes
        )
        self.sync_action_selector = self.setup_sync_action_selector()
        self.right_value_div = jp.Td(
                a=self,
                text=self.comparison_data.right_value,
                classes=cell_classes
        )
        self.enhance_value_display()

    def get_row_color(self):
        """
        defines the row background color based on the sync status
        """
        color = ""
        status = self.comparison_data.get_sync_status()
        if status is SyncStatus.IN_SYNC:
            color = "green"
        elif status is SyncStatus.OUT_SYNC:
            color = "red"
        intensity = 200
        return f"bg-{color}-{intensity}"

    def setup_sync_action_selector(self):
        """
        setup sync action selector and choose default action based on the data
        """
        self.sync_status_div.delete_components()
        div = jp.Div(a=self.sync_status_div, classes="flex justify-end")
        status_div = jp.Div(a=div, text=self.comparison_data.get_sync_status().value)
        color = "grey"
        selector = EnumSelector(
                enum=SyncAction,
                exclude=[SyncAction.SYNC],
                a=div,
                value=self.comparison_data.get_chosen_sync_option().name,
                on_change=self.change_sync_action
        )
        return selector

    def change_sync_action(self, _msg):
        """
        handle change in sync action
        """
        new_action = SyncAction[self.sync_action_selector.value]
        print(f"Changing sync action from {self.comparison_data.chosen_sync_option} to {new_action}")
        self.comparison_data.chosen_sync_option = new_action

    def enhance_value_display(self):
        """
        Enhances the displayed value
        """
        if self.comparison_data.left_value is None:
            self.left_value_div.text = ""
            jp.Div(a=self.left_value_div, classes="text-sm text-gray-500", text="<None>")
        if self.comparison_data.right_value is None:
            self.right_value_div.text = ""
            jp.Div(a=self.right_value_div, classes="text-sm text-gray-500", text="<None>")


class EnumSelector(jp.Select):
    """
    Generates a Selector for an enum
    """

    def __init__(self, enum: typing.Type[Enum], exclude: typing.List[Enum], **kwargs):
        """
        constructor
        Args:
            enum: Enum class to generate the selector for
            exclude: enum values to exclude from the selection
            **kwargs: justpy component arguments
        """
        super(EnumSelector, self).__init__(**kwargs)
        if exclude is None:
            exclude = []
        self.enum = enum
        color = "gray"
        for action in self.enum:
            if action in exclude:
                continue
            option = jp.Option(value=action.name, text=action.value, classes=f'bg-{color}-600')
            self.add(option)

