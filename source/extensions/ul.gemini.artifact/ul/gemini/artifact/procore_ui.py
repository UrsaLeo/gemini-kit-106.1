import omni.ui as ui
import ul.gemini.services.utils as utils
import os

base_path = os.path.join(os.path.dirname(__file__), "data", "icons")

class ProcoreItem(ui.AbstractItem):
    def __init__(self, data):
        super().__init__()
        # Initialize the item with data from the JSON object
        self.name_model = ui.SimpleStringModel(data["name"])
        self.path_model = ui.SimpleStringModel(data["path"])
        # Recursively create children items if any exist in the data
        self.children = [ProcoreItem(child) for child in data.get("children", [])]

class ProcoreModel(ui.AbstractItemModel):
    def __init__(self, procore_data):
        super().__init__()
        # Decode the JSON string into a Python object and create the tree structure
        data_objects = procore_data
        self._children = [ProcoreItem(data) for data in data_objects]

    def get_item_children(self, item):
        return item.children if item else self._children

    def get_item_value_model_count(self, item):
        return 1

    def get_item_value_model(self, item, column_id):
        return item.name_model

    def get_item_path_value_model(self, item, column_id):
        return item.path_model

class ProcoreDelegate(ui.AbstractItemDelegate):

    def __init__(self):
        super().__init__()
        self.last_expanded_folder = ""

    def build_branch(self, model: ui.AbstractItemModel, item: ui.AbstractItem, column_id: int, level: int, expanded: bool):
        selected_folder = model.get_item_value_model(item, level).as_string
        path_model = model.get_item_path_value_model(item, level)
        path_string = path_model.as_string if hasattr(path_model, "as_string") else str(path_model)
        data = utils.get_file_extension(selected_folder)
        text = "   " * (level + 1)

        with ui.HStack():
            ui.Label(text,alignment=ui.Alignment.CENTER)
            if len(data) != 0:
                ui.Label("      ", alignment=ui.Alignment.CENTER)
                ui.Image(os.path.join(base_path, "file.png"), width=15, height=15, alignment=ui.Alignment.CENTER)
            else:
                if expanded:
                    ui.Image(os.path.join(base_path, "minus.png"), width=10, height=17, alignment=ui.Alignment.CENTER)
                else:
                    ui.Image(os.path.join(base_path, "plus.png"), width=15, height=17, alignment=ui.Alignment.CENTER)
                ui.Label("  ", alignment=ui.Alignment.CENTER)
                ui.Image(os.path.join(base_path, "folder.png"), width=15, height=15, alignment=ui.Alignment.CENTER)

            ui.Label(" ", alignment=ui.Alignment.CENTER)

    def build_widget(self, model:ProcoreModel, item: ui.AbstractItem , column_id: int, level: int, expanded: bool):

        selected_folder = model.get_item_value_model(item,level).as_string
        path_model = model.get_item_path_value_model(item, level)
        ui.Label(selected_folder)


##The classes below are for maintaining RFI and Submittals
class CommandItem(ui.AbstractItem):

    def __init__(self, text,id):
        super().__init__()
        self.name_model = ui.SimpleStringModel(text)
        self.id_model = ui.SimpleStringModel(id)

class CommandModel(ui.AbstractItemModel):
    def __init__(self,data:any,entity_type:str):
        super().__init__()
        self._details = []
        print(f"entity_type={entity_type}")
        for item in data:
            if entity_type == "RFI":
                self._details.append(CommandItem(item['subject'],str(item['id'])))
            elif entity_type == "SUBMITTAL":
                self._details.append(CommandItem(item['title'],str(item['id'])))

    def get_item_children(self, item):
        if item is not None:
            return []
        return self._details

    def get_item_value_model_count(self, item):
        return 1

    def get_item_value_model(self, item, column_id):
        return item.name_model

    def get_item_id(self, item):
        return item.id_model
