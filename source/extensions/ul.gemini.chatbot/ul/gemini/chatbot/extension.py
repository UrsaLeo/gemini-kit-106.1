import omni.ext
import omni.ui as ui
import asyncio
import aiohttp
from omni.ui import color as cl
import os
from .utils import open_windows
from .styles import response_style_welcome,bot_bubble_style_welcome,send_button_style
import ul.gemini.services.artifact_services as artifact_services

class ChatBotWindow(ui.Window):
    def __init__(self, title: str, **kwargs) -> None:
        super().__init__(title, **kwargs)
        self.frame.set_build_fn(self._build_fn)
        self.font_size = 16
        self.partner_secure_data =  artifact_services.get_partner_secure_data()

    def _build_fn(self):
        welcome_bot_message_bubble = ui.ZStack()
        base_path = os.path.join(os.path.dirname(__file__), "data" ,"icons")
        image_url = os.path.join(base_path,"Bot.jpg")
        welcome_message="Hello, how may i assist you today ?"
        with welcome_bot_message_bubble:
                    with ui.VStack():
                        with ui.HStack():
                            self.chat_image=ui.Image(image_url,alignment=ui.Alignment.LEFT,height=ui.Pixel(30),width=ui.Pixel(30))
                            with ui.ZStack():
                                ui.Rectangle(style=bot_bubble_style_welcome, width=ui.Percent(80), alignment=ui.Alignment.LEFT)
                                with ui.VStack():
                                    ui.Label(f"{welcome_message}  ", word_wrap=True, style=response_style_welcome,width=ui.Percent(80))

        with self.frame:
            base_path = os.path.join(os.path.dirname(__file__), "data" ,"icons")
            image_url = os.path.join(base_path,"Icon.JPG")
            background_colour=ui.color(36,37,36,255)
            self.placeholder_text=" Enter your message"
            with ui.VStack(width=ui.Percent(100), height=ui.Percent(100),style={"background_color":background_colour}):
                with ui.VStack(height=ui.Percent(10),style={"background_color":ui.color.black} ):
                    with ui.ZStack():
                        ui.Rectangle(width=ui.Percent(100), height=ui.Percent(100), style={"background_color": ui.color.black})
                        self.chat_image=ui.Image(image_url,style={"background_color":"green"},alignment=ui.Alignment.LEFT)
                self.add_space=ui.Rectangle(width=ui.Percent(100), height=ui.Percent(5), style={"background_color": background_colour})
                self.chat_scroll_frame = ui.ScrollingFrame(height=ui.Percent(73), horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF)
                with self.chat_scroll_frame:
                    self.chat_display = ui.VStack(spacing=5, height=0)
                    #self.chat_display.add_child(welcome_bot_message_bubble)



                ui.Spacer(height=5)
                with ui.VStack(height=ui.Percent(10), spacing=5, width=ui.Percent(100)):
                    with ui.ZStack():
                        ui.Rectangle(width=ui.Percent(100), height=ui.Percent(100), style={"background_color": background_colour})
                        with ui.HStack(height=ui.Percent(100), spacing=5, width=ui.Percent(100)):
                            self.chat_input = ui.StringField(height=ui.Percent(100), width=ui.Percent(85),multiline=True ,style={"background_color":background_colour, "color": cl("#A9A9A9")})
                            self.chat_input.model.set_value(self.placeholder_text)  # Set initial placeholder
                            self.chat_input.model.add_begin_edit_fn(self.on_input_edit)
                            self.chat_input.model.add_end_edit_fn(self.input_change)
                            with ui.VStack(height=ui.Percent(100), width=ui.Percent(15)):
                                self.send_button=ui.Button(
                                    "",
                                    image_url=os.path.join(base_path,"Send.png"),
                                    height=ui.Percent(80),
                                    #height=50,
                                    width=ui.Percent(100),
                                    margin=ui.Percent(0),
                                    clicked_fn=self.check_and_send_message,
                                    style=send_button_style
                               )
    def check_and_send_message(self):
        text = self.chat_input.model.get_value_as_string()
    # Check if the text is not empty, not just whitespace, and not the placeholder
        if text and text.strip() and text != self.placeholder_text:
            self.send_message()  # Only call send_message if the input is valid
        else:
            print("invalid input")

    def input_change(self,value):
        #print("edit ended")
        text = self.chat_input.model.get_value_as_string()
        #print(f"text is{text}")
        if text is None or text.strip() == "":
            #print("Input is empty, setting placeholder")
            self.chat_input.model.set_value(self.placeholder_text)
            self.chat_input.style = {"color": cl("#A9A9A9") }
        else:
            print("Input is not empty")


    def on_input_edit(self,model):
        self.chat_input.model.set_value("")
        self.chat_input.style = {"color": cl("#FFFFFF") }  # Apply regular style

    def check_and_send_message(self):
        text = self.chat_input.model.get_value_as_string()
    # Check if the text is not empty, not just whitespace, and not the placeholder
        if text and text.strip() and text != self.placeholder_text:
            self.send_message()  # Only call send_message if the input is valid
        else:
            print("invalid input")

    def input_change(self,value):
        print("edit ended")
        text = self.chat_input.model.get_value_as_string()
        print(f"text is{text}")
        if text is None or text.strip() == "":
            print("Input is empty, setting placeholder")
            self.chat_input.model.set_value(self.placeholder_text)
            self.chat_input.style = {"color": cl("#A9A9A9") }
        else:
            print("Input is not empty")


    def on_input_edit(self,model):
        self.chat_input.model.set_value("")
        self.chat_input.style = {"color": cl("#FFFFFF") }

    def set_scroll_to_end(self,value):
        # Ensure this is called after content is added
        #print(f"max scrollable:{self.chat_scroll_frame.scroll_y_max}")
        self.chat_scroll_frame.scroll_y = self.chat_scroll_frame.scroll_y_max*value
        ##print(self.chat_scroll_frame.scroll_y)
        #print("scrolled to end")


    def send_message(self):
        self.set_scroll_to_end(3.5)
        user_message = self.chat_input.model.get_value_as_string()
        #print(self.position_x,self.position_y)
        self.send_button.enabled=False
        if user_message:
            open_windows(user_message)
            # Add user message to chat display

            user_bubble_style_empty_regtangle = {
                    "background_color": ui.color(36,37,36,255),
                    "alignment": ui.Alignment.RIGHT,

             }
            user_bubble_style = {
            "background_color": ui.color(67, 67, 66, 255),
            "alignment": ui.Alignment.RIGHT,
            "padding": 10,
            "border_radius": 5
            }

            label_style_user = {
                "Label": {
                    "font_size": self.font_size,
                    "color": "white",
                    "alignment": ui.Alignment.RIGHT,
                    "margin": 5,
                    "word_wrap": True,
                    "font": "${fonts}/roboto_medium.ttf"
                }
            }

            label_style_me = {
                "Label": {
                    "font_size": self.font_size - 3,
                    "font": "${fonts}/OpenSans-SemiBold.ttf",
                    "color": cl.White,
                    "alignment": ui.Alignment.RIGHT,
                }
            }
            user_message_bubble = ui.ZStack()

            with user_message_bubble:
                with ui.VStack():
                    with ui.HStack():
                        ui.Rectangle(style=user_bubble_style_empty_regtangle, width=ui.Percent(60), alignment=ui.Alignment.RIGHT)
                        with ui.ZStack():
                            ui.Rectangle(style=user_bubble_style, width=ui.Percent(100), alignment=ui.Alignment.RIGHT)
                            ui.Label(f"{user_message}", word_wrap=True, style=label_style_user, width=ui.Percent(100), alignment=ui.Alignment.RIGHT)
            self.chat_display.add_child(ui.Label("Me", alignment=ui.Alignment.RIGHT, word_wrap=True, style=label_style_me))
            self.chat_display.add_child(user_message_bubble)

            asyncio.ensure_future(self.get_response_from_api(user_message))
            #self.chat_input.model.set_value("")
            self.chat_input.model.set_value(self.placeholder_text)
            self.chat_input.style = {"color": cl("#A9A9A9") }
            button_style2 = {
                        "Button": {
                            "background_color": ui.color.grey,
                            "image_url": "data\icon",
                            "border_radius": 5,
                            "padding": 5
                        },
                        "Button:hovered": {
                            "background_color": ui.color(1.0, 1.0, 1.0, 0.1)
                        }
                    }
            self.processing_button=ui.Button("***",height=ui.Percent(100), width=ui.Percent(15), style=button_style2)
            self.chat_display.add_child(self.processing_button)


    async def get_response_from_api(self, message):
        #print("Fetching response from API...")
        async with aiohttp.ClientSession() as session:
            url = "http://52.21.129.119:8000/core/api/document-response/"
            data = {"query": message,
                    "twin_version_id":self.partner_secure_data['twinVersionId']}
            print(f"data is :{data}")
            try:
                async with session.post(url, json=data) as resp:
                    result = await resp.json(content_type=None)
                    response_content = result.get("openai_response", {}).get("content", "No response")
                    self.processing_button.visible=False
                    response_style_ai_assist={
                        "Label":{
                              "font_size": self.font_size-3,
                                "color": cl.White,
                                "font":"${fonts}/OpenSans-SemiBold.ttf",
                                "alignment": ui.Alignment.LEFT,
                                "margin-left":ui.Pixel(10)
                        },
                    }
                    bot_background=ui.color(0,0,0,255)

                bot_bubble_style = {
                    "background_color": ui.color(0, 0, 0, 255),
                    "alignment": ui.Alignment.LEFT,
                    "padding": 10,
                    "border_radius": 5
                }
                response_style2 = {
                    "Label": {
                        "font_size": self.font_size,
                        "color": "white",
                        "alignment": ui.Alignment.LEFT,
                        "margin": 5,
                        "word_wrap": True
                    }
                }

                base_path = os.path.join(os.path.dirname(__file__), "data" ,"icons")
                image_url = os.path.join(base_path,"AIAssist.png")
                bot_message_bubble = ui.VStack()
                with bot_message_bubble:
                    with ui.HStack():
                        self.chat_image = ui.Image(image_url, alignment=ui.Alignment.LEFT, height=ui.Pixel(30), width=ui.Pixel(30))
                        with ui.VStack():
                            with ui.HStack():
                                with ui.ZStack():
                                    ui.Rectangle(style=bot_bubble_style, width=ui.Pixel(240), alignment=ui.Alignment.LEFT)
                                    ui.Label(f"{response_content}", word_wrap=True, style=response_style2)
                                ui.Spacer()
                        ui.Spacer()

                bot_add_ai_assist = ui.VStack()
                with bot_add_ai_assist:
                    with ui.VStack():
                        with ui.HStack():
                            self.chat_image=ui.Image(alignment=ui.Alignment.LEFT,height=ui.Pixel(0),width=ui.Pixel(30))
                            with ui.ZStack():
                                with ui.VStack():
                                    ui.Label("AI Assist", alignment=ui.Alignment.LEFT, word_wrap=True, style=response_style_ai_assist,width=ui.Percent(20))
                    self.chat_display.add_child(bot_add_ai_assist)
                    self.chat_display.add_child(bot_message_bubble)
                    self.send_button.enabled=True
                    self.set_scroll_to_end(1.3)

            except Exception as e:
                #print(f"Caught Exception {e}")
                bot_background=ui.color(0,0,0,255)
                bot_bubble_style = {
                    "background_color":bot_background,
                    "alignment": ui.Alignment.LEFT,
                    "padding":15
                }

                error_bot_message_bubble = ui.ZStack()
                with error_bot_message_bubble:
                    response_style_error = {
                        "Label": {
                            "font_size": self.font_size,
                            "color": "red",
                            "alignment": ui.Alignment.LEFT,
                        }
                    }
                    ui.Rectangle(style=bot_bubble_style, width=ui.Percent(80), alignment=ui.Alignment.LEFT)
                    with ui.VStack():
                        with ui.HStack():
                        #ui.Spacer(height=10)
                            ui.Label("Something went wrong", alignment=ui.Alignment.LEFT, word_wrap=True, style=response_style_error,width=ui.Percent(80))
                self.processing_button.visible=True
                self.chat_display.add_child(error_bot_message_bubble)
                self.processing_button.visible=False
                self.send_button.enabled=True


class MyExtension(omni.ext.IExt):


    def on_startup(self, ext_id):
        print("[ul.gemini.chatbot] Extension startup")
        window_flags = ui.WINDOW_FLAGS_NO_RESIZE
        self._window = ChatBotWindow("Gemini AI", width=449, height=380, flags=window_flags)

    def on_shutdown(self):
        print("[ul.gemini.chatbot] Extension shutdown")
        if self._window:
            self._window.destroy()
            self._window = None
