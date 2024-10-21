import omni.ui as ui
from omni.ui import color as cl
import ul.gemini.services.utils as utils
import os

class Item(ui.AbstractItem):
    def __init__(self, data, entity_type):
        super().__init__()
        self.name_model = ui.SimpleStringModel(data["name"]) # This can be either title or subject
        self._entity_type = entity_type
        self.number_model = ui.SimpleStringModel(data["number"])
        self.id_model = ui.SimpleStringModel(data["id"])

        if self._entity_type == "SUBMITTAL":
            self.spec_model = ui.SimpleStringModel(data["spec"])
            self._type_model = ui.SimpleStringModel(data["type"])
            self._revision_model = ui.SimpleStringModel(data["revision"])


class EntityModel(ui.AbstractItemModel):

    def __init__(self, datas, entity_type):
        super().__init__()
        self._children = [Item(data,entity_type) for data in datas]
        self._entity_type = entity_type

    def get_item_children(self, item):
        if item is not None:
            return []
        return self._children

    def get_item_value_model_count(self, item):
        if self._entity_type == "RFI":
            return 2
        return 5

    def get_item_value_model(self, item, column_id):
        if column_id == 0:
            return item.number_model
        elif column_id == 1:
            return item.name_model

        if self._entity_type == "SUBMITTAL":
            if column_id == 2:
                return item.spec_model
            elif column_id == 3:
                return item._type_model
            elif column_id == 4:
                return item._revision_model

class DelegateModel(ui.AbstractItemDelegate):

    def __init__(self, entity_type,sort_callback,has_clicked_sort:bool,is_asc_or_desc:bool,sort_by:str):
        super().__init__()
        self._entity_type = entity_type
        self._sort_callback = sort_callback
        self._has_clicked_sort = has_clicked_sort
        self._is_asc_or_desc = is_asc_or_desc
        self._sort_by = sort_by

    def build_branch(self, model, item, column_id, level, expanded):
        pass

    def build_widget(self, model:EntityModel, item:ui.AbstractItem, column_id, level, expanded):
        style = {
                "Tooltip": {"color": cl("#ffffff"),"background_color": cl("#4f4e4e"),
                "margin_width": 0.5 ,
                "margin_height": 0.5 , "border_width":0.5, "border_color": cl.white, "padding": 5.0 },
                "Label": {
                    "margin": 8.0
                }
                }
        with ui.HStack():
            value_model = model.get_item_value_model(item, column_id)

            if self._entity_type == "RFI":
                if column_id == 1:
                    name = utils.truncate_path(value_model.as_string,30)
                    ui.Label(name, style=style,tooltip=value_model.as_string)
            else:
                if column_id == 1:
                    name = utils.truncate_path(value_model.as_string,15)
                    ui.Label(name, style=style,tooltip=value_model.as_string)

            if column_id != 1:
                other = utils.truncate_path(value_model.as_string,15)
                ui.Label(other, style=style,alignment=ui.Alignment.CENTER,tooltip=value_model.as_string)

    def build_header(self,column_id):
        icon_path = os.path.join(os.path.dirname(__file__), "data","icons")
        if self._entity_type == "RFI":
            if column_id == 0:
                with ui.HStack():
                    ui.Label("RFI #", height=25,alignment=ui.Alignment.CENTER)
                    if not self._has_clicked_sort:
                        ui.Button(image_url=os.path.join(icon_path, "arrow_default.png"),clicked_fn=lambda entity_type = self._entity_type, sort_by="NUMBER": self._sort_callback(entity_type,sort_by),width=0,  image_width=18, image_height=18)
                    else:
                        if self._sort_by == "NUMBER":
                            if self._is_asc_or_desc:
                                ui.Button(image_url=os.path.join(icon_path, "arrow_down.png"),clicked_fn=lambda entity_type = self._entity_type, sort_by="NUMBER": self._sort_callback(entity_type,sort_by),width=0,  image_width=18, image_height=18)
                            else:
                                ui.Button(image_url=os.path.join(icon_path, "arrow_up.png"),clicked_fn=lambda entity_type = self._entity_type, sort_by="NUMBER": self._sort_callback(entity_type,sort_by),width=0,  image_width=18, image_height=18)
                        else:
                            ui.Button(image_url=os.path.join(icon_path, "arrow_default.png"),clicked_fn=lambda entity_type = self._entity_type, sort_by="NUMBER": self._sort_callback(entity_type,sort_by),width=0,  image_width=18, image_height=18)


        else:
            if column_id == 0:
                with ui.HStack():
                    ui.Label("Submittal #", height=25,alignment=ui.Alignment.CENTER)
                    if not self._has_clicked_sort:
                        ui.Button(image_url=os.path.join(icon_path, "arrow_default.png"),width=0,  image_width=18, image_height=18,clicked_fn=lambda entity_type = self._entity_type, sort_by="NUMBER": self._sort_callback(entity_type,sort_by))
                    else:
                        if self._sort_by == "NUMBER":
                            if self._is_asc_or_desc:
                                ui.Button(image_url=os.path.join(icon_path, "arrow_down.png"),width=0,  image_width=18, image_height=18,clicked_fn=lambda entity_type = self._entity_type, sort_by="NUMBER": self._sort_callback(entity_type,sort_by))
                            else:
                                ui.Button(image_url=os.path.join(icon_path, "arrow_up.png"),width=0,  image_width=18, image_height=18,clicked_fn=lambda entity_type = self._entity_type, sort_by="NUMBER": self._sort_callback(entity_type,sort_by))
                        else:
                            ui.Button(image_url=os.path.join(icon_path, "arrow_default.png"),width=0,  image_width=18, image_height=18,clicked_fn=lambda entity_type = self._entity_type, sort_by="NUMBER": self._sort_callback(entity_type,sort_by))




            elif column_id == 2:
                with ui.HStack():
                    ui.Label("Spec Section", height=25,alignment=ui.Alignment.CENTER)
                    if not self._has_clicked_sort:
                        ui.Button(image_url=os.path.join(icon_path, "arrow_default.png"),width=0,  image_width=18, image_height=18,clicked_fn=lambda entity_type = self._entity_type, sort_by="SPEC": self._sort_callback(entity_type,sort_by))
                    else:
                        if self._sort_by == "SPEC":
                            if self._is_asc_or_desc:
                                ui.Button(image_url=os.path.join(icon_path, "arrow_down.png"),width=0,  image_width=18, image_height=18,clicked_fn=lambda entity_type = self._entity_type, sort_by="SPEC": self._sort_callback(entity_type,sort_by))
                            else:
                                ui.Button(image_url=os.path.join(icon_path, "arrow_up.png"),width=0,  image_width=18, image_height=18,clicked_fn=lambda entity_type = self._entity_type, sort_by="SPEC": self._sort_callback(entity_type,sort_by))
                        else:
                            ui.Button(image_url=os.path.join(icon_path, "arrow_default.png"),width=0,  image_width=18, image_height=18,clicked_fn=lambda entity_type = self._entity_type, sort_by="SPEC": self._sort_callback(entity_type,sort_by))


            elif column_id == 3:
                with ui.HStack():
                    ui.Label("Type", height=25,alignment=ui.Alignment.CENTER)
                    if not self._has_clicked_sort:
                        ui.Button(image_url=os.path.join(icon_path, "arrow_default.png"),width=0,  image_width=18, image_height=18,clicked_fn=lambda entity_type = self._entity_type, sort_by="TYPE": self._sort_callback(entity_type,sort_by))
                    else:
                        if self._sort_by == "TYPE":
                            if self._is_asc_or_desc:
                                ui.Button(image_url=os.path.join(icon_path, "arrow_down.png"),width=0,  image_width=18, image_height=18,clicked_fn=lambda entity_type = self._entity_type, sort_by="TYPE": self._sort_callback(entity_type,sort_by))
                            else:
                                ui.Button(image_url=os.path.join(icon_path, "arrow_up.png"),width=0,  image_width=18, image_height=18,clicked_fn=lambda entity_type = self._entity_type, sort_by="TYPE": self._sort_callback(entity_type,sort_by))
                        else:
                            ui.Button(image_url=os.path.join(icon_path, "arrow_default.png"),width=0,  image_width=18, image_height=18,clicked_fn=lambda entity_type = self._entity_type, sort_by="TYPE": self._sort_callback(entity_type,sort_by))


            elif column_id == 4:
                with ui.HStack():
                    ui.Label("Revision", height=25,alignment=ui.Alignment.CENTER)
                    if not self._has_clicked_sort:
                        ui.Button(image_url=os.path.join(icon_path,"arrow_default.png"),width=0,  image_width=18, image_height=18,clicked_fn=lambda entity_type = self._entity_type, sort_by="REVISION": self._sort_callback(entity_type,sort_by))
                    else:
                        if self._sort_by == "REVISION":
                            if self._is_asc_or_desc:
                                ui.Button(image_url=os.path.join(icon_path,"arrow_down.png"),width=0,  image_width=18, image_height=18,clicked_fn=lambda entity_type = self._entity_type, sort_by="REVISION": self._sort_callback(entity_type,sort_by))
                            else:
                                ui.Button(image_url=os.path.join(icon_path, "arrow_up.png"),width=0,  image_width=18, image_height=18,clicked_fn=lambda entity_type = self._entity_type, sort_by="REVISION": self._sort_callback(entity_type,sort_by))
                        else:
                            ui.Button(image_url=os.path.join(icon_path, "arrow_default.png"),width=0,  image_width=18, image_height=18,clicked_fn=lambda entity_type = self._entity_type, sort_by="REVISION": self._sort_callback(entity_type,sort_by))

        if column_id == 1:
            with ui.HStack():
                ui.Label("Title", height=25,alignment=ui.Alignment.CENTER)
                if not self._has_clicked_sort:
                    ui.Button(image_url=os.path.join(icon_path, "arrow_default.png"),width=0,  image_width=18, image_height=18, clicked_fn=lambda entity_type = self._entity_type, sort_by="TITLE": self._sort_callback(entity_type,sort_by))
                else:
                    if self._sort_by == "TITLE":
                        if self._is_asc_or_desc:
                            ui.Button(image_url=os.path.join(icon_path, "arrow_down.png"),width=0,  image_width=18, image_height=18, clicked_fn=lambda entity_type = self._entity_type, sort_by="TITLE": self._sort_callback(entity_type,sort_by))
                        else:
                            ui.Button(image_url=os.path.join(icon_path, "arrow_up.png"),width=0,  image_width=18, image_height=18, clicked_fn=lambda entity_type = self._entity_type, sort_by="TITLE": self._sort_callback(entity_type,sort_by))
                    else:
                        ui.Button(image_url=os.path.join(icon_path, "arrow_default.png"),width=0,  image_width=18, image_height=18, clicked_fn=lambda entity_type = self._entity_type, sort_by="TITLE": self._sort_callback(entity_type,sort_by))
