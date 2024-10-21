import omni.ext
import omni.ui as ui
from pxr import UsdGeom
import asyncio
from omni.ui import color as cl
import ul.gemini.services.artifact_services as artifact_services
import ul.gemini.services.utils as utils
from ul.gemini.artifact.procore_ui import ProcoreModel, ProcoreDelegate, CommandModel
from ul.gemini.artifact.entity_ui import EntityModel,DelegateModel
import os

partner_secure_data =  artifact_services.get_partner_secure_data()

icon_path = os.path.join(os.path.dirname(__file__), "data","icons")

entity_list = None #artifact_services.get_integration_entity_type_list()
procore_data = None #artifact_services.get_procore_document_structure()
submittal_details = None #artifact_services.get_submittals_details()
rfi_details = None #artifact_services.get_rfi_details()

selected_document_to_delete = []
selected_rfi_to_delete = []
selected_submittals_to_delete = []
_selected_to_attach = set()
entity_style = {
            "margin": 5.0,
            "padding": 7.0,
            "alignment": ui.Alignment.LEFT
}

scroll_frame_style = {
    "background_color": cl("#282828")
}

label_style = {
    "Label": {"background_color": cl.transparent},
    "Label:hovered": {"background_color": cl("#b6d3d8")},
}

enabled_detach_style = style={"color": cl.white,"background_color": cl.transparent,
                            "Tooltip": {"color": cl("#ffffff"),"background_color": cl("#4f4e4e"),
                                        "margin_width": 0.5 ,
                                        "margin_height": 0.5 , "border_width":0.5, "border_color": cl.white, "padding": 5.0 }
                            }

disabled_detach_style = style={"color": cl.grey,"background_color": cl.transparent,
                            "Tooltip": {"color": cl("#ffffff"),"background_color": cl("#4f4e4e"),
                                        "margin_width": 0.5 ,
                                        "margin_height": 0.5 , "border_width":0.5, "border_color": cl.white, "padding": 5.0 }
                            }

checkbox_style = {"margin": 7.0, "padding": 5.0,"color": cl("#76D300"),"border_radius": 0, "background_color": cl(0.25)}


# Functions and vars are available to other extension as usual in python: `example.python_ext.some_public_function(x)`
def some_public_function(x: int):
    print(f"[ul.gemini.artifact] some_public_function was called with {x}")
    return x ** x


class MyExtension(omni.ext.IExt):

    def __init__(self):
        super().__init__()
        self._artifacts_window = None
        self._selected_prim_path = None
        self._usd_context = omni.usd.get_context()
        self._selection = self._usd_context.get_selection()
        self._events = self._usd_context.get_stage_event_stream()
        self.stage_event_sub = self._events.create_subscription_to_pop(
            self.on_stage_event, name = "Get Selected prim path"
        )
        self._entity_selection = "SUBMITTAL"
        self._procore_window = None
        self._radio_button_styling = None
        self._entity_view_window = None
        self._search_text = None
        self._already_search_attempted = False
        self._detach_button_enabling = None
        self._search_text_model = None
        self._clear_search_text_btn = None
        self._clear_btn_pressed = True
        self._execute_sort = False
        self._is_asc_sorting = True
        self._title_sort = True
        self._revision_sort = True
        self._type_sort = True
        self._spec_section_sort = True
        self._number_sort = True
        self._sort_by = None

    def on_stage_event(self,event):
        if event.type == int(omni.usd.StageEventType.SELECTION_CHANGED):
            self._on_selection_changed()

    def _on_selection_changed(self):
        selection = self._selection.get_selected_prim_paths()
        stage = self._usd_context.get_stage()
        if(selection and selection[0]):
            self._prim = stage.GetPrimAtPath(selection[0])
            self._selected_prim_path = str(UsdGeom.Imageable(self._prim).GetPath())
            print (self._selected_prim_path)
            if (self._selected_prim_path == "/SectionTools/Section_Tool_Object"):
                return
            if ('Twins/Building/Sensors' in self._selected_prim_path):
                return

            self._artifact_window_builder()

    def _search_value_change(self, label_text:str):
        self._search_text = label_text
        self._search_based_entity(self._search_text, self._entity_selection)

    def _selected_radio_button(self, selected_entity):
        print(f"Selected Entity {selected_entity}")
        self._entity_selection = selected_entity
        print("SELF ENTITY UPDATE = " + self._entity_selection)
        self._artifact_window_builder()

    def _window_builder(self,data,entity_type):
        with ui.VStack():
            if entity_type == "RFI":
                self._rfi_model_builder(data)
            else:
                self._submittables_model_builder(data)
            ui.Button("Download Additional Information",enabled=False, style={"background_color": cl.transparent}, height=10)


    def _rfi_model_builder(self,data):
        global entity_style
        with ui.ScrollingFrame(horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF):
                with ui.VStack(height=0,style=entity_style):
                    with ui.HStack():
                        ui.Label("Status: ", width=200)
                        ui.Label(data['status'])
                    with ui.HStack():
                        ui.Label("Subject: ",width=200)
                        ui.Label(data['subject'])
                    with ui.HStack():
                        ui.Label("Due Date: ",width=200)
                        ui.Label(data['due_date'])
                    with ui.HStack():
                        ui.Label("Responsible Contractor: ",width=200)
                        ui.Label(data['responsible_contractor']['name'])
                    with ui.HStack():
                        ui.Label("Dependent Projects: ",width=200)
                        ui.Label(str(data['project_stage']['dependent_projects']))
                    with ui.HStack():
                        ui.Label("Formatted Name: ",width=200)
                        ui.Label(data['project_stage']['formatted_name'])
                    with ui.HStack():
                        ui.Label("Received From: ",width=200)
                        ui.Label(data['received_from']['name'])
                    with ui.HStack():
                        ui.Label("RFI Manager: ",width=200)
                        if data['rfi_manager'] is not None:
                            value = data['rfi_manager']['name']
                            print(value)
                            ui.Label(str(value))
                        else:
                            ui.Label("No RFI Manager",width=200)
                    with ui.HStack():
                        ui.Label("Assignee: ",width=200)
                        ui.Label(data['assignee']['name'])

    def _submittables_model_builder(self,data):
        global entity_style
        with ui.ScrollingFrame(horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF):
            with ui.VStack(height=0,style=entity_style):
                with ui.HStack():
                    ui.Label("Status: ",width=200)
                    if data['status'] is not None:
                        ui.Label(data['status']['status'])
                    else: ui.Label("Status not found")
                with ui.HStack():
                    ui.Label("Title: ",width=200)
                    ui.Label(data['title'])
                with ui.HStack():
                    ui.Label("Issue Date: ",width=200)
                    ui.Label(data['issue_date'])
                with ui.HStack():
                    ui.Label("Due Date: ",width=200)
                    ui.Label(str(data['due_date']))
                with ui.HStack():
                    ui.Label("Received From: ",width=200)
                    if(data['received_from'] is None):
                        ui.Label("None")
                    else:
                        ui.Label(data['received_from']['name'])
                with ui.HStack():
                        ui.Label("Responsible Contractor: ",width=200)
                        ui.Label(data['responsible_contractor']['name'])
                with ui.HStack():
                    ui.Label("Submittal Manager: ",width=200)
                    if data['submittal_manager'] is not None:
                        ui.Label(data['submittal_manager']['name'])
                    else:
                        ui.Label("No Submittal Manager")

    def _procore_title_bar(self):
        trimmed_prim_path = self._selected_prim_path.split("/World",1)[-1]
        trimmed_prim_path = trimmed_prim_path = utils.truncate_path(trimmed_prim_path,65)
        ui.Label(trimmed_prim_path,alignment=ui.Alignment.CENTER, style={"margin": 5.0}, tooltip=self._selected_prim_path)

    def _attach_according_to_entity_Selection(self,entity_selected):
        global selected_rfi_to_delete
        global selected_document_to_delete
        global selected_submittals_to_delete
        global _selected_to_attach
        global rfi_details
        global submittal_details
        global procore_data
        print("ATTACH SELECTED")
        if entity_selected == "RFI":
            self._attach_rfis(self._selected_prim_path,_selected_to_attach)
        elif entity_selected == "SUBMITTAL":
            self._attach_submittals(self._selected_prim_path,_selected_to_attach)
        else:
            self._attach_a_document(self._selected_prim_path,_selected_to_attach)
        _selected_to_attach = set()
        selected_rfi_to_delete = []
        selected_document_to_delete = []
        selected_submittals_to_delete = []

        if self._already_search_attempted:
            rfi_details = artifact_services.get_rfi_details()
            submittal_details = artifact_services.get_submittals_details()
            procore_data = artifact_services.get_procore_document_structure()

    def _procore_window_buttons(self):
        global _selected_to_attach
        print("Button selcted to attach")
        with ui.HStack():
            ui.Button("Cancel",clicked_fn=self._close_procore_window,style={"color": cl.white, "background_color": cl.transparent,
                                                                            "Tooltip": {"color": cl("#ffffff"),"background_color": cl("#4f4e4e"), "margin_width": 0.5 ,
                                                                                        "margin_height": 0.5 , "border_width":0.5, "border_color": cl.white, "padding": 5.0 }},
                                                                                        tooltip="Cancel")
            ui.Line(name="default", width= 20, alignment=ui.Alignment.H_CENTER, style={"border_width":1, "color": cl.green})
            ui.Button("Attach Selected",style={ "color": cl.white, "background_color": cl.transparent,
                                                            "Tooltip": {"color": cl("#ffffff"),"background_color": cl("#4f4e4e"), "margin_width": 0.5 ,
                                                            "margin_height": 0.5 , "border_width":0.5, "border_color": cl.white, "padding": 5.0 }
                                                        }, clicked_fn=lambda: self._attach_according_to_entity_Selection(self._entity_selection),
                                                    tooltip="Attach Selected")


    def _search_based_entity(self,search_text:str,entity_type):
        global procore_data
        global rfi_details
        global submittal_details
        if entity_type == "DOCUMENT":
            procore_data = artifact_services.search_for_documents(search_text)
        elif entity_type == "SUBMITTAL":
            submittal_details = artifact_services.search_for_submittals_locally(search_text)
        elif entity_type == "RFI":
            rfi_details = artifact_services.search_for_rfis_locally(search_text)
        else:
            print(f"No Entity Type available {entity_type}")

        if self._search_text:
            self._already_search_attempted = True

        self._clear_btn_pressed = True
        self._open_procore_window()

    def _search_with_or_without_text(self, model):
        self._search_text = model.get_value_as_string()
        if len(model.get_value_as_string()) == 0:
            self._search_text = None
            self._search_based_entity("", self._entity_selection)
        else:
            self._search_text_model.add_end_edit_fn(lambda model: self._search_value_change(model.get_value_as_string()))

    def _clear_search_text(self, model):
        self._clear_btn_pressed = True
        self._search_text = None
        model.set_value("")

    def _search_bar(self):
        with ui.HStack():
            self._search_text_model = ui.StringField(style={"margin" : 5.0 }).model
            if self._search_text is not None:
                self._search_text_model.set_value(self._search_text)
            self._search_text_model.add_value_changed_fn(lambda model: self._search_with_or_without_text(model))
            ui.Button(image_url=os.path.join(icon_path,"search.png"), style={"color": cl.white, "margin": 5.0,"Tooltip": {"color": cl("#ffffff"),"background_color": cl("#4f4e4e"), "margin_width": 0.5 ,
                                                            "margin_height": 0.5 , "border_width":0.5, "border_color": cl.white, "padding": 5.0 }}, width=0,  image_width=18, image_height=18, clicked_fn=lambda: self._search_based_entity(self._search_text, self._entity_selection), tooltip="Search")

    def add_basket_to_delete(self, model,value,selected_document_to_delete):
        global enabled_detach_style
        global disabled_detach_style

        if model.get_value_as_bool():
            model.set_value(True)
            print(f"Selected procore file: {value}")
            selected_document_to_delete.append(value)
        else:
            print(f"De-Selected the data: {value}")
            selected_document_to_delete.remove(value)

        if len(selected_document_to_delete) > 0:
            self._detach_button_enabling.enabled = True
            self._detach_button_enabling.style = enabled_detach_style
        else:
            self._detach_button_enabling.enabled = False
            self._detach_button_enabling.style = disabled_detach_style



    async def load_data(self):
        global entity_list, procore_data, submittal_details,rfi_details, partner_secure_data
        if "authToken" not in partner_secure_data:
            return
        entity_list = artifact_services.get_integration_entity_type_list()
        procore_data = artifact_services.get_procore_document_structure()
        submittal_details = artifact_services.get_submittals_details()
        rfi_details = artifact_services.get_rfi_details()




    def _document_selection_changed(self,selected_items):
        global _selected_to_attach
        _selected_to_attach = set() #Resetting the selected items set so that newly unselected will be removed here

        for item in selected_items:
            print(f"Item selected: {item.path_model.as_string}")
            _selected_to_attach.add(item.path_model.as_string)

    def _submittal_or_rfi_selection_change(self,selected_items):
        print(f"Items: {selected_items}")
        global _selected_to_attach

        for item in selected_items:
            _selected_to_attach.add(item.id_model.as_string)

    def _attach_submittals(self,selected_prim_path:str,submittals):
        global _selected_to_attach
        global partner_secure_data
        submittals_list = list(submittals)
        response = artifact_services.attach_submittals(selected_prim_path,submittals_list)
        if response is not None and response.status_code == 200:
            print("Submittals attached successfully")
        else:
            print("Error in attaching Submittals")

        _selected_to_attach = set()
        self._procore_window.visible = False
        self._artifact_window_builder()

    def _attach_rfis(self,selected_prim_path:str,rfis):
        global _selected_to_attach
        global partner_secure_data
        rfis_list = list(rfis)
        response = artifact_services.attach_rfi(selected_prim_path,rfis_list)
        if response is not None and response.status_code == 200:
            print("RFI attached successfully")
        else:
            print("Error in attaching RFI")

        _selected_to_attach = set()
        self._procore_window.visible = False
        self._artifact_window_builder()

    def _attach_a_document(self,selected_prim_path:str,procore_paths):
        global _selected_to_attach
        print(procore_paths)
        procore_paths = list(procore_paths)
        print(f"Attach selected with selected_prim_path={selected_prim_path}, procore_path={procore_paths}")
        attach_paths = []
        selection_of_folders = utils.has_selected_folders(procore_paths)
        if selection_of_folders:
            print("There are folders selected")
            return
        else:
            for path in procore_paths:
                parts = path.split('/', 1)
                new_path = None
                if len(parts) > 1:
                    new_path = '/' + parts[1]
                else:
                    new_path = path
                print(f"New Path: {new_path}")
                attach_paths.append(new_path)

            response = artifact_services.attach_a_document(selected_prim_path,attach_paths)
            if response.status_code == 200:
                print("Successfully added the attachment")
            else:
                print("Failed to add the attachment")
            _selected_to_attach = set()
            attach_paths = []
            self._procore_window.visible = False
            self._artifact_window_builder()

    def _open_document_procore_window(self):
        global procore_data

        with ui.ScrollingFrame(
            height=600,
            horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
            vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_ON,
            style_type_name_override="TreeView",
            style={
                "margin": 5.0,
            }
        ):
            self._model = ProcoreModel(procore_data)
            self._delegate = ProcoreDelegate()
            ui.TreeView(self._model,delegate=self._delegate, root_visible=False,style={"margin": 0.5},selection_changed_fn=self._document_selection_changed)

    def _sort_result(self,entity_type:str,sort_by:str):
        global submittal_details
        global rfi_details
        self._execute_sort = True
        self._sort_by = sort_by
        if entity_type == "SUBMITTAL":
            if sort_by == "TITLE" and self._title_sort:
                sorted_data = artifact_services.sort_data(entity_type,submittal_details['data'],sort_by,self._execute_sort, "ASC")
                submittal_details = sorted_data
                self._title_sort = False
                self._is_asc_sorting = self._title_sort
            elif sort_by == "TITLE" and not self._title_sort:
                sorted_data = artifact_services.sort_data(entity_type,submittal_details['data'],sort_by,self._execute_sort, "DESC")
                submittal_details = sorted_data
                self._title_sort = True
                self._is_asc_sorting = self._title_sort
            elif sort_by == "NUMBER" and self._number_sort:
                sorted_data = artifact_services.sort_data(entity_type,submittal_details['data'],sort_by,self._execute_sort, "ASC")
                submittal_details = sorted_data
                self._number_sort = False
                self._is_asc_sorting = self._number_sort
            elif sort_by == "NUMBER" and not self._number_sort:
                sorted_data = artifact_services.sort_data(entity_type,submittal_details['data'],sort_by,self._execute_sort, "DESC")
                submittal_details = sorted_data
                self._number_sort = True
                self._is_asc_sorting = self._number_sort
            elif sort_by == "SPEC" and self._spec_section_sort:
                sorted_data = artifact_services.sort_data(entity_type,submittal_details['data'],sort_by,self._execute_sort, "ASC")
                submittal_details = sorted_data
                self._spec_section_sort = False
                self._is_asc_sorting = self._spec_section_sort
            elif sort_by == "SPEC" and not self._spec_section_sort:
                sorted_data = artifact_services.sort_data(entity_type,submittal_details['data'],sort_by,self._execute_sort, "DESC")
                submittal_details = sorted_data
                self._spec_section_sort = True
                self._is_asc_sorting = self._spec_section_sort
            elif sort_by == "REVISION" and self._revision_sort:
                sorted_data = artifact_services.sort_data(entity_type,submittal_details['data'],sort_by,self._execute_sort, "ASC")
                submittal_details = sorted_data
                self._revision_sort = False
                self._is_asc_sorting = self._revision_sort
            elif sort_by == "REVISION" and not  self._revision_sort:
                sorted_data = artifact_services.sort_data(entity_type,submittal_details['data'],sort_by,self._execute_sort, "DESC")
                submittal_details = sorted_data
                self._revision_sort = True
                self._is_asc_sorting =  self._revision_sort
            elif sort_by == "TYPE" and self._type_sort:
                sorted_data = artifact_services.sort_data(entity_type,submittal_details['data'],sort_by,self._execute_sort, "ASC")
                submittal_details = sorted_data
                self._type_sort = False
                self._is_asc_sorting = self._type_sort
            elif sort_by == "TYPE" and not  self._type_sort:
                sorted_data = artifact_services.sort_data(entity_type,submittal_details['data'],sort_by,self._execute_sort, "DESC")
                submittal_details = sorted_data
                self._type_sort = True
                self._is_asc_sorting =  self._type_sort
        else:
            if sort_by == "TITLE" and self._title_sort:
                sorted_data = artifact_services.sort_data(entity_type,rfi_details['data'],sort_by,self._execute_sort, "ASC")
                rfi_details = sorted_data
                self._title_sort = False
                self._is_asc_sorting = self._title_sort
            elif sort_by == "TITLE" and not self._title_sort:
                sorted_data = artifact_services.sort_data(entity_type,rfi_details['data'],sort_by,self._execute_sort, "DESC")
                rfi_details = sorted_data
                self._title_sort = True
                self._is_asc_sorting = self._title_sort
            elif sort_by == "NUMBER" and self._number_sort:
                sorted_data = artifact_services.sort_data(entity_type,rfi_details['data'],sort_by,self._execute_sort,  "ASC")
                rfi_details = sorted_data
                self._number_sort = False
                self._is_asc_sorting = self._number_sort
            elif sort_by == "NUMBER" and not self._number_sort:
                sorted_data = artifact_services.sort_data(entity_type,rfi_details['data'],sort_by,self._execute_sort,  "DESC")
                rfi_details = sorted_data
                self._number_sort = True
                self._is_asc_sorting = self._number_sort
        self._open_procore_window()

    def _open_rfi_or_submittal_procore_window(self):
        global rfi_details
        global submittal_details
        #if user data is not there, can't do this
        if "authToken" not in partner_secure_data:
            return
        if self._entity_selection == "RFI":
            rfis = rfi_details['data']
            entity_model_obj = utils.define_entity_item(rfis,"RFI")
            if len(rfis) == 0:
                with ui.ScrollingFrame(
                        height=600,
                        horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        style_type_name_override="TreeView",
                    ):
                        self._entity_model = EntityModel(entity_model_obj,"RFI")
                        self._delegate = DelegateModel("RFI",self._sort_result,self._execute_sort,self._is_asc_sorting,self._sort_by)
                        ui.TreeView(self._entity_model,delegate=self._delegate,root_visible=False,header_visible=True, style={"TreeView.Item": {"margin": 4}},selection_changed_fn=self._submittal_or_rfi_selection_change)
            elif len(rfis) <= 17:
                with ui.ScrollingFrame(
                        height=600,
                        horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        style_type_name_override="TreeView",
                    ):
                        self._entity_model = EntityModel(entity_model_obj,"RFI")
                        self._delegate = DelegateModel("RFI",self._sort_result,self._execute_sort,self._is_asc_sorting,self._sort_by)
                        ui.TreeView(self._entity_model,delegate=self._delegate,root_visible=False,header_visible=True, style={"TreeView.Item": {"margin": 4}},selection_changed_fn=self._submittal_or_rfi_selection_change)
            else:
                with ui.ScrollingFrame(
                        height=600,
                        horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_ON,
                        style_type_name_override="TreeView",
                    ):

                        self._entity_model = EntityModel(entity_model_obj,"RFI")
                        self._delegate = DelegateModel("RFI",self._sort_result,self._execute_sort,self._is_asc_sorting,self._sort_by)
                        ui.TreeView(self._entity_model,delegate=self._delegate,root_visible=False,header_visible=True, style={"TreeView.Item": {"margin": 4}},selection_changed_fn=self._submittal_or_rfi_selection_change)
        else:
            submittals = submittal_details['data']
            entity_model_obj = utils.define_entity_item(submittals, "SUBMITTAL")
            if len(submittals) == 0:
                with ui.ScrollingFrame(
                        height=600,
                        horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        style_type_name_override="TreeView",
                    ):
                        self._entity_model = EntityModel(entity_model_obj,"SUBMITTAL")
                        self._delegate = DelegateModel("SUBMITTAL",self._sort_result,self._execute_sort,self._is_asc_sorting,self._sort_by)
                        ui.TreeView(self._entity_model,delegate=self._delegate,root_visible=False,header_visible=True, style={"TreeView.Item": {"margin": 4}},selection_changed_fn=self._submittal_or_rfi_selection_change)
            elif len(submittals) <= 17:
                with ui.ScrollingFrame(
                        height=600,
                        horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        style_type_name_override="TreeView",
                    ):
                        self._entity_model = EntityModel(entity_model_obj,"SUBMITTAL")
                        self._delegate = DelegateModel("SUBMITTAL",self._sort_result,self._execute_sort,self._is_asc_sorting,self._sort_by)
                        ui.TreeView(self._entity_model,delegate=self._delegate,root_visible=False,header_visible=True, style={"TreeView.Item": {"margin": 4}},selection_changed_fn=self._submittal_or_rfi_selection_change)
            else:
                with ui.ScrollingFrame(
                        height=600,
                        horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_ON,
                        style_type_name_override="TreeView",
                    ):
                        self._entity_model = EntityModel(entity_model_obj,"SUBMITTAL")
                        self._delegate = DelegateModel("SUBMITTAL",self._sort_result,self._execute_sort,self._is_asc_sorting,self._sort_by)
                        ui.TreeView(self._entity_model,delegate=self._delegate,root_visible=False,header_visible=True, style={"TreeView.Item": {"margin": 4}},selection_changed_fn=self._submittal_or_rfi_selection_change)

    def _create_tree_view_new(self):
        global rfi_details, submittal_details, procore_data
        if self._entity_selection == "DOCUMENT":
            self._open_document_procore_window()
        else:
            print(f"Entity_type={self._entity_selection}")

            self._open_rfi_or_submittal_procore_window()

    def _open_procore_window(self):

        def create_procore_window():

            def create_procore_model():
                print("Creating procore window")
                with self._procore_window.frame:
                    with ui.ScrollingFrame(horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF):
                        with ui.VStack(height=0):
                            self._procore_title_bar()
                            self._search_bar()
                            self._create_tree_view_new()
                            self._procore_window_buttons()

            if not self._procore_window:
                window_flags = ui.WINDOW_FLAGS_NO_RESIZE
                window_flags |= ui.WINDOW_FLAGS_NO_SCROLLBAR
                window_flags |= ui.WINDOW_FLAGS_MODAL
                window_flags |= ui.WINDOW_FLAGS_NO_CLOSE
                window_flags |= ui.WINDOW_FLAGS_NO_MOVE
                self._procore_window = ui.Window((f"Attach to:"), width=800, height=720, flags=window_flags)
                create_procore_model()
            else:
                create_procore_model()
            self._procore_window.visible = True
        create_procore_window()

    def _close_procore_window(self):
        global rfi_details
        global submittal_details
        global procore_data
        global _selected_to_attach

        _selected_to_attach = set()
        if self._procore_window:
            self._procore_window.visible = False
        self._search_text = None

        if self._already_search_attempted:
            if self._entity_selection == "RFI":
                rfi_details = artifact_services.get_rfi_details()
            elif self._entity_selection == "SUBMITTAL":
                submittal_details = artifact_services.get_submittals_details()
            elif self._entity_selection == "DOCUMENT":
                procore_data = artifact_services.get_procore_document_structure()
                self._execute_sort = False
        self._is_asc_sorting = True
        self._title_sort = True
        self._revision_sort = True
        self._type_sort = True
        self._spec_section_sort = True
        self._number_sort = True
        self._sort_by = None

    def get_selected_entity_data(self,entity_selected):
        if entity_selected == "RFI":
            return artifact_services.get_rfi_for_selected_prim(self._selected_prim_path)
        elif entity_selected == "DOCUMENT":
            return artifact_services.get_prim_asset_documents(self._selected_prim_path)
        elif entity_selected == "SUBMITTAL":
            return artifact_services.get_prim_path_submittals(self._selected_prim_path)

    def _button_builder(self):
        global entity_list

        style_button = {
            "Button": {
                "background_color": cl.transparent,
                "alignment" : ui.Alignment.CENTER,
                "margin": 0.7,
                "padding": 2.0
            },
            "Button:hovered": {"background_color":cl("#696969")},
            "Button.Label": {"alignment": ui.Alignment.CENTER,"color":cl("#808080")},
            "Tooltip": {"color": cl("#ffffff"),"background_color": cl("#4f4e4e"), "margin_width": 0.5 ,
            "margin_height": 0.5 , "border_width":0.5, "border_color": cl.white, "padding": 5.0 }

        }

        selection_style = {
            "Button": {
                "background_color": cl("#282828"),
                "alignment" : ui.Alignment.CENTER,
                "margin": -0.01,
                "padding": 2.0,

            },
            "Button:hovered": {"background_color":cl("#000000")},
            "Button.Label": {"alignment": ui.Alignment.CENTER},
                        "Tooltip": {"color": cl("#ffffff"),"background_color": cl("#4f4e4e"), "margin_width": 0.5 ,
                                                            "margin_height": 0.5 , "border_width":0.5, "border_color": cl.white, "padding": 5.0 }
        }

        if entity_list is None:
            return

        for entity in entity_list:
            with ui.HStack():
                style = None
                if entity['type'] == self._entity_selection:
                    style = selection_style
                else:
                    style = style_button

                if entity['type'] == "RFI":
                    ui.Button(entity['type'],style=style,height=10,clicked_fn= lambda entity_type=entity['type']: self._selected_radio_button(entity_type),tooltip=entity['type'])
                else:
                    ui.Button(str(entity['type']).capitalize(),style=style,height=10,clicked_fn= lambda entity_type=entity['type']: self._selected_radio_button(entity_type),tooltip=str(entity['type']).capitalize())

    def _get_selected_data_to_delete(self,model,value,entity_type):
        global selected_document_to_delete
        global selected_rfi_to_delete
        global selected_submittals_to_delete
        if entity_type == "DOCUMENT":
            selected_submittals_to_delete = []
            selected_rfi_to_delete = []
            self.add_basket_to_delete(model,value,selected_document_to_delete)
        elif entity_type == "RFI":
            selected_document_to_delete = []
            selected_submittals_to_delete = []
            self.add_basket_to_delete(model,value,selected_rfi_to_delete)
        elif entity_type == "SUBMITTAL":
            selected_document_to_delete = []
            selected_rfi_to_delete = []
            self.add_basket_to_delete(model,value,selected_submittals_to_delete)
        else:
            print("No Entity Type")

    def _rfi_scrollable_frame(self):
        global icon_path
        global scroll_frame_style
        rfis = artifact_services.get_rfi_for_selected_prim(self._selected_prim_path)
        rfi_frame = None
        if len(rfis) == 0:
            rfi_frame = ui.ScrollingFrame(
                        height=210,
                        horizontal_scrollbar_policy = ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        vertical_scrollbar_policy = ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        style=scroll_frame_style
                    )
        elif len(rfis) <= 6:
            rfi_frame = ui.ScrollingFrame(
                        height=210,
                        horizontal_scrollbar_policy = ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        vertical_scrollbar_policy = ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        style=scroll_frame_style
                    )
        else:
            rfi_frame = ui.ScrollingFrame(
                        height=210,
                        horizontal_scrollbar_policy = ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        vertical_scrollbar_policy = ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_ON,
                        style=scroll_frame_style
                    )
        with rfi_frame:
            with ui.VStack(height=0):
                if len(rfis) == 0:
                    ui.Label(
                        "No RFIs have been attached yet.",
                        style={
                            "font_size": 24,
                            "color": cl.grey,
                        },
                        alignment=ui.Alignment.CENTER,
                    )
                else:
                    for rfi in rfis:
                        with ui.HStack(alignment=ui.Alignment.CENTER,width=ui.Fraction(1), name="rfi-stack"):
                            checked_data = ui.CheckBox(width = 10, height=10, style = checkbox_style)
                            rfi_subject = rfi['entityData']['subject']
                            rfi_id = rfi['entityData']['id']
                            rfi_due_date = rfi['entityData']['due_date']
                            subject = utils.truncate_path(rfi_subject,12)
                            selected_item = rfi['integrationEntityId']
                            checked_data.model.add_value_changed_fn(lambda model=checked_data,value=selected_item:self._get_selected_data_to_delete(model,value,self._entity_selection))
                            ui.Label(str(rfi_id))
                            ui.Label(subject,tooltip=rfi_subject,style={"Tooltip": {"color": cl("#ffffff"),"background_color": cl("#4f4e4e"), "margin_width": 0.5 ,
                                                            "margin_height": 0.5 , "border_width":0.5, "border_color": cl.white, "padding": 5.0 }})
                            ui.Label(str(rfi_due_date))
                            ui.Button(image_url=os.path.join(icon_path, "eye.png"),  style={"color": cl.white, "cursor": "pointer","Tooltip": {"color": cl("#ffffff"),"background_color": cl("#4f4e4e"), "margin_width": 0.5 ,
                                                            "margin_height": 0.5 , "border_width":0.5, "border_color": cl.white, "padding": 5.0 }},tooltip="Click to view", width=0,  image_width=18, image_height=18, alignment=ui.Alignment.RIGHT,clicked_fn=lambda entity_data=rfi['entityData']:self._view_entity_details(entity_data,"RFI"), name="view-btn")
                            ui.Button(image_url=os.path.join(icon_path,"downl.png"), style={"color": cl.white, "cursor": "pointer","Tooltip": {"color": cl("#ffffff"),"background_color": cl("#4f4e4e"), "margin_width": 0.5 ,
                                                            "margin_height": 0.5 , "border_width":0.5, "border_color": cl.white, "padding": 5.0 }},tooltip="Click to download", width=0, image_width=15, image_height=15, alignment=ui.Alignment.RIGHT, name="download-btn",
                                      )



    def _create_document_event(self,event_type:str,prim_path:str,procore_path,integration_entity_id:str):
        global partner_secure_data
        file_name = utils.get_file_name(procore_path)
        extension = utils.get_file_extension(file_name)
        procore_id = artifact_services.get_source_id('PROCORE')

        document_event_request = {
            "userId": partner_secure_data['userId'],
            "twinId": partner_secure_data['twinId'],
            "clientId": partner_secure_data['clientId'],
            "twinVersionId": partner_secure_data['twinVersionId'],
            "name": file_name,
            "documentType": "INSTALLATION", # This need to dynamic as well
            "extension": extension,
            "eventType": event_type,
            "filePath": prim_path,
            "path": procore_path,
            "integrationEntityId": integration_entity_id,
            "integrationSourceId": procore_id
        }

        print("Create document event")
        print(document_event_request)

        document_event_response = artifact_services.create_document_event("/api/document-event/create", document_event_request)
        print(document_event_response)
        if document_event_response.status_code == 200:
            print(f"Successfully created the document event: {document_event_response}")
        else:
            print("Error creating the document event")

    def _document_scrollable_frame(self):
        global scroll_frame_style
        documents = artifact_services.get_prim_asset_documents(self._selected_prim_path)

        document_frame = None
        if len(documents) == 0:
            document_frame = ui.ScrollingFrame(
                    height=210,
                    horizontal_scrollbar_policy = ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                    vertical_scrollbar_policy = ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                    style=scroll_frame_style
                )
        elif len(documents) <= 6:
            document_frame = ui.ScrollingFrame(
                    height=210,
                    horizontal_scrollbar_policy = ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                    vertical_scrollbar_policy = ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                    style=scroll_frame_style
                )
        else:
            document_frame = ui.ScrollingFrame(
                    height=210,
                    horizontal_scrollbar_policy = ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                    vertical_scrollbar_policy = ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_ON,
                    style=scroll_frame_style
                )

        with document_frame:
            with ui.VStack(height=0):
                if len(documents) == 0:
                    ui.Label(
                        "No documents have been attached yet.",
                        style={
                            "font_size": 24,
                            "color": cl.grey,
                        },
                        alignment=ui.Alignment.CENTER,
                    )
                else:
                    for asset_data in documents:
                        with ui.HStack(alignment=ui.Alignment.CENTER,width= ui.Fraction(1), name="document-stack"):
                            checked_data = ui.CheckBox(width = 10, height=10, style = checkbox_style)
                            document_name = asset_data['externalId'].split("/")[-1]
                            selected_item = asset_data['integrationEntityId']
                            checked_data.model.add_value_changed_fn(lambda model=checked_data,value=selected_item:self._get_selected_data_to_delete(model,value,self._entity_selection))
                            ui.Label(document_name,tooltip=document_name, tooltip_offset_y=22, tooltip_offset_x=80)
                            ui.Button(image_url=os.path.join(icon_path, "eye.png"),  style={"color": cl.white, "cursor": "pointer","Tooltip": {"color": cl("#ffffff"),"background_color": cl("#4f4e4e"), "margin_width": 0.5 ,
                                                            "margin_height": 0.5 , "border_width":0.5, "border_color": cl.white, "padding": 5.0 }},tooltip="Click to view", width=0,  image_width=18, image_height=18, alignment=ui.Alignment.RIGHT, name="view-btn", clicked_fn=lambda assetId=asset_data['assetId'],path=asset_data['externalId'], integration_entity_id=asset_data['integrationEntityId']:self._create_document_event("VIEW",assetId,path,integration_entity_id))
                            ui.Button(image_url=os.path.join(icon_path, "downl.png"), style={"color": cl.white, "cursor": "pointer","Tooltip": {"color": cl("#ffffff"),"background_color": cl("#4f4e4e"), "margin_width": 0.5 ,
                                                            "margin_height": 0.5 , "border_width":0.5, "border_color": cl.white, "padding": 5.0 }},tooltip="Click to download", width=0, image_width=15, image_height=15, alignment=ui.Alignment.RIGHT, name="download-btn",clicked_fn=lambda assetId=asset_data['assetId'],path=asset_data['externalId'],integration_entity_id=asset_data['integrationEntityId']:self._create_document_event("DOWNLOAD",assetId,path,integration_entity_id))


    def _view_entity_details(self,entity_data,entity_type):
        window_flags = ui.WINDOW_FLAGS_NO_RESIZE
        window_flags |= ui.WINDOW_FLAGS_NO_SCROLLBAR
        window_flags |= ui.WINDOW_FLAGS_MODAL
        # window_flags |= ui.WINDOW_FLAGS_NO_CLOSE
        if entity_type == "RFI":
            self._entity_view_window = ui.Window("RFI Entity", height=500,width=500,flags=window_flags)
            with self._entity_view_window.frame:
                self._window_builder(entity_data,entity_type)
        else:
            self._entity_view_window = ui.Window("SUBMITTAL Entity", height=500,width=500,flags=window_flags)
            with self._entity_view_window.frame:
                self._window_builder(entity_data,entity_type)



    def _submitals_scrollable_frame(self):
        global scroll_frame_style
        global label_style
        submittals = artifact_services.get_prim_path_submittals(self._selected_prim_path)

        submittal_frame = None
        if len(submittals) == 0:
            submittal_frame = ui.ScrollingFrame(
                        height=210,
                        horizontal_scrollbar_policy = ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        vertical_scrollbar_policy = ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        style=scroll_frame_style
                    )
        elif len(submittals) <= 6:
            submittal_frame = ui.ScrollingFrame(
                        height=210,
                        horizontal_scrollbar_policy = ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        vertical_scrollbar_policy = ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        style=scroll_frame_style
                    )
        else:
            submittal_frame = ui.ScrollingFrame(
                        height=210,
                        horizontal_scrollbar_policy = ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                        vertical_scrollbar_policy = ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_ON,
                        style=scroll_frame_style
                    )

        with submittal_frame:
            with ui.VStack(height=0):
                if len(submittals) == 0:
                    ui.Label(
                        "No submittals have been attached yet.",
                        style={
                            "font_size": 24,
                            "color": cl.grey,
                        },
                        alignment=ui.Alignment.CENTER,
                    )
                else:
                    for submittal in submittals:
                        with ui.HStack(alignment=ui.Alignment.CENTER,width=ui.Fraction(1), name="submittal-stack"):
                            checked_data = ui.CheckBox(width = 10, height=10, style = checkbox_style)
                            submittal_title = submittal['entityData']['title']
                            submittal_id = submittal['entityData']['id']
                            submittal_issue_date = submittal['entityData']['issue_date']
                            print(f"title {submittal_title}, id={submittal_id}, issue_date={submittal_issue_date}")
                            title = utils.truncate_path(submittal_title,12)
                            selected_item = submittal['integrationEntityId']
                            checked_data.model.add_value_changed_fn(lambda model=checked_data,value=selected_item:self._get_selected_data_to_delete(model,value,self._entity_selection))
                            ui.Label(str(submittal_id))
                            ui.Label(title,tooltip=submittal_title,style={"Tooltip": {"color": cl("#ffffff"),"background_color": cl("#4f4e4e"), "margin_width": 0.5 ,
                                                            "margin_height": 0.5 , "border_width":0.5, "border_color": cl.white, "padding": 5.0 }})
                            ui.Label(str(submittal_issue_date))
                            ui.Button(image_url=os.path.join(icon_path, "eye.png"),  style={"color": cl.white, "cursor": "pointer","Tooltip": {"color": cl("#ffffff"),"background_color": cl("#4f4e4e"), "margin_width": 0.5 ,
                                                            "margin_height": 0.5 , "border_width":0.5, "border_color": cl.white, "padding": 5.0 }},tooltip="Click to view", width=0,  image_width=18, image_height=18, alignment=ui.Alignment.RIGHT,clicked_fn=lambda entity_data=submittal['entityData']:self._view_entity_details(entity_data,"SUBMITTAL"), name="view-btn")
                            ui.Button(image_url=os.path.join(icon_path, "downl.png"), style={"color": cl.white, "cursor": "pointer","Tooltip": {"color": cl("#ffffff"),"background_color": cl("#4f4e4e"), "margin_width": 0.5 ,
                                                            "margin_height": 0.5 , "border_width":0.5, "border_color": cl.white, "padding": 5.0 }},tooltip="Click to download", width=0, image_width=15, image_height=15, alignment=ui.Alignment.RIGHT, name="download-btn")



    def _initial_no_selection_screen(self):
        with ui.VStack(style={"background_color": cl("#00000")}):
            ui.Label("Please Select an Entity above")

    def _load_entity_data_window(self):
            with ui.VStack():
                if self._entity_selection == "DOCUMENT":
                    self._document_scrollable_frame()
                elif self._entity_selection == "SUBMITTAL":
                    self._submitals_scrollable_frame()
                elif self._entity_selection == "RFI":
                    self._rfi_scrollable_frame()
                else:
                    self._initial_no_selection_screen()

    def _on_attach_new(self):
        print("_on_attach_new")
        self._open_procore_window()

    def _on_detach(self,entity_type,prim_path):
        global selected_document_to_delete
        global selected_rfi_to_delete
        global selected_submittals_to_delete

        if len(selected_document_to_delete) == 0 and len(selected_rfi_to_delete) == 0 and len(selected_submittals_to_delete) == 0:
            print("No entity selected to delete")
            return

        if entity_type == "DOCUMENT":
            if len(selected_document_to_delete) == 1:
                artifact_services.delete_integration_entity(prim_path,selected_document_to_delete[0],None)
            else:
               artifact_services.delete_integration_entity(prim_path,None,selected_document_to_delete)
        elif entity_type == "RFI":
            if len(selected_rfi_to_delete) == 1:
                artifact_services.delete_integration_entity(prim_path,selected_rfi_to_delete[0],None)
            else:
               artifact_services.delete_integration_entity(prim_path,None,selected_rfi_to_delete)
        elif entity_type == "SUBMITTAL":
            if len(selected_submittals_to_delete) == 1:
                artifact_services.delete_integration_entity(prim_path,selected_submittals_to_delete[0],None)
            else:
               artifact_services.delete_integration_entity(prim_path,None,selected_submittals_to_delete)
        else:
            print("No Entity type support")

        selected_document_to_delete=[]
        selected_rfi_to_delete = []
        selected_submittals_to_delete = []
        self._artifact_window_builder()

    def _button_main(self):
        global disabled_detach_style
        with ui.HStack(height=0, alignment=ui.Alignment.CENTER, style = {"margin": 5.0}):
            self._detach_button_enabling = ui.Button("Detach Selected",clicked_fn= lambda: self._on_detach(self._entity_selection,self._selected_prim_path),style=disabled_detach_style, enabled=False)

            ui.Line(name="default", width= 20, alignment=ui.Alignment.H_CENTER, style={"border_width":1, "color": cl("#76D300")})
            btn = ui.Button("Attach New", style={ "color": cl.white,  "background_color": cl.transparent,"Tooltip": {"color": cl("#ffffff"),"background_color": cl("#4f4e4e"), "margin_width": 0.5 ,
                                                            "margin_height": 0.5 , "border_width":0.5, "border_color": cl.white, "padding": 5.0 }},clicked_fn=self._on_attach_new,tooltip="Attach New")
            if "authToken" not in partner_secure_data:
                btn.enabled = False
                btn.style = disabled_detach_style

    def _artifact_window_builder(self):
        def window_context():
            def create_window_model():
                with self._artifacts_window.frame:
                    with ui.VStack(height=0):
                        if self._selected_prim_path is None:
                            print("Initial Loading of prim")
                            ui.Label("Select equipment to view attachments", height=0, style={"margin": 5.0, "padding": 5.0})
                        else:
                            print("Prim Path Selected")
                            trimmed_prim_path = self._selected_prim_path.split("/World",1)[-1]
                            trimmed_prim_path = utils.truncate_path(trimmed_prim_path,65)
                            print(f"Trimmed path: {trimmed_prim_path}")
                            ui.Label(f"Attach document to this prim: '{trimmed_prim_path}'",tooltip=self._selected_prim_path, height=0, style={"margin": 5.0, "padding": 5.0})
                            with ui.VStack():
                                with ui.HStack(height=0):
                                    self._button_builder()
                                ui.Spacer()
                                with ui.VStack(height=210, style={"background_color": cl("#00000")}):
                                    self._load_entity_data_window()
                                if self._entity_selection is not None:
                                    self._button_main()

            if self._artifacts_window is None:
                window_flags = ui.WINDOW_FLAGS_NO_RESIZE
                self._artifacts_window = ui.Window("Attachment", width=320, height=280,flags=window_flags)
                create_window_model()
            else:
                create_window_model()
            self._artifacts_window.visible = True
        window_context()

    def on_startup(self, ext_id):
        print("[ul.gemini.artifacts] MyExtension startup")
        asyncio.ensure_future(self.load_data())
        self._artifact_window_builder()
        print("[ul.gemini.artifacts] MyExtension finished startup")


    def on_shutdown(self):
        print("[ul.gemini.artifacts] MyExtension shutdown")
