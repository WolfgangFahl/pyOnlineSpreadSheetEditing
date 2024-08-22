"""
Created on 2024-03-18

@author: wf
"""

from onlinespreadsheet.record_sync import ComparisonRecord, SyncAction, SyncStatus


class SyncDialog:
    """
    dialog widget to synchronize two data records
    """

    def __init__(
        self,
        solution: InputWebSolution,
        comparison_record: ComparisonRecord,
        sync_callback: typing.Callable[[SyncRequest], None] = None,
        value_enhancement_callback: typing.Callable[["SyncDialogRow"], None] = None,
    ):
        """
        constructor
        """
        self.solution = (solution,)
        self.comparison_record = comparison_record
        if sync_callback is None:
            sync_callback = self.__fallback_sync_callback
        self.sync_callback = sync_callback
        self.rows = []
        for cd in self.comparison_record.comparison_data.values():
            sdr = SyncDialogRow(cd, a=self.table_body, classes="")
            self.rows.append(sdr)
        self.value_enhancement_callback = value_enhancement_callback
        self.enhance_row_values()

    def setup_ui(self):
        """ """
        self.setup_header()
        self.setup_controls()

    def setup_header(self):
        """
        setup header column
        """
        self.header = ui.html()
        jp.Th(a=self.header, text="Property")
        jp.Th(a=self.header, text=self.comparison_record.left_source_name)
        action_header = jp.Th(a=self.header, style="width:60px")
        color = "grey"
        selector = EnumSelector(
            enum=SyncAction,
            exclude=[SyncAction.NOTHING],
            a=action_header,
            value=SyncAction.SYNC.name,
            on_change=self.handle_sync_action_change,
        )
        jp.Th(a=self.header, text=self.comparison_record.right_source_name)

    def setup_controls(self):
        with ui.row() as self.button_row:
            btn_sync_left = ui.button(
                f"update {self.comparison_record.left_source_name}",
                on_click=self.handle_sync_left_click,
            ).style("btn-primary")

            btn_sync_both = ui.button(
                "update both", on_click=self.handle_sync_click
            ).style("btn-primary")

            btn_sync_right = ui.button(
                f"update {self.comparison_record.right_source_name}",
                on_click=self.handle_sync_right_click,
            ).style("btn-primary")

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
            row.sync_action_selector.value = new_action.name

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


class SyncDialogRow:
    """
    row in the SyncDialog
    """

    def __init__(self, data: ComparisonData):
        """
        constructor
        Args:
            data: data to compare/sync in this row
        """
        self.comparison_data = data
        row_color = self.get_row_color()
        cell_classes = f"border border-green-600 mx-2 my-1 p-2 {row_color}"
        self.property_name_div = jp.Td(
            a=self, text=self.comparison_data.property_name, classes=cell_classes
        )
        self.left_value_div = jp.Td(
            a=self, text=self.comparison_data.left_value, classes=cell_classes
        )
        self.sync_status_div = jp.Td(a=self, classes=cell_classes)
        self.sync_action_selector = self.setup_sync_action_selector()
        self.right_value_div = jp.Td(
            a=self, text=self.comparison_data.right_value, classes=cell_classes
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
        # div = jp.Div(a=self.sync_status_div, classes="flex justify-end")
        # status_div = jp.Div(a=div, text=self.comparison_data.get_sync_status().value)
        # color = "grey"
        # selector = EnumSelector(
        #    enum=SyncAction,
        #    exclude=[SyncAction.SYNC],
        #    a=div,
        #    value=self.comparison_data.get_chosen_sync_option().name,
        #    on_change=self.change_sync_action,
        # )
        selector = None
        return selector

    def change_sync_action(self, _msg):
        """
        handle change in sync action
        """
        new_action = SyncAction[self.sync_action_selector.value]
        print(
            f"Changing sync action from {self.comparison_data.chosen_sync_option} to {new_action}"
        )
        self.comparison_data.chosen_sync_option = new_action

    def enhance_value_display(self):
        """
        Enhances the displayed value
        """
