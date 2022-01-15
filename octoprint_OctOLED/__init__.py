# coding=utf-8
from __future__ import absolute_import

import os
# OLED Display
import board
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

# API
import flask

# Animations
import asyncio
import math
import time

import octoprint.plugin

class OctOLEDPlugin(octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.EventHandlerPlugin
):

    ##~~ Setup initial display
    def init_display(self, width = -1, height = -1):
        # TODO: Width and height can be obtained from self._oled once initialized so we probably don't need to store these    
        self._disp_width = self._settings.get(["display_width"]) if width == -1 else width
        self._disp_height = self._settings.get(["display_height"]) if height == -1 else height
        self._disp_rotate_180 = self._settings.get(["rotate_180"])
        self._disp_font_face = "Noto_Sans/NotoSans-Regular"
        self._disp_font_size = int(self._settings.get(["display_font_size"]))
        self._disp_border = 5
        self._disp_addr = 0x3C
        self._current_text = ""
        self._anim_task = None
        self._font_dir = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + '/fonts') + '/'
        # Only I2C displays are supported
        self._i2c = board.I2C()
        self._oled = adafruit_ssd1306.SSD1306_I2C(self._disp_width, self._disp_height, self._i2c, addr=self._disp_addr)
        # reset=oled_reset)
        self._oled.rotate(self._settings.get(["rotate_180"]))
        self._disp_rotate_180 = self._settings.get(["rotate_180"])

        # Clear display.
        self._oled.fill(0)
        self._oled.show()

        # Create blank image for drawing.
        # Make sure to create image with mode '1' for 1-bit color.
        self._disp_image = Image.new("1", (self._oled.width, self._oled.height))

        # Get drawing object to draw on image.
        self._disp_draw = ImageDraw.Draw(self._disp_image)
        self._logger.info("Loading font: " + self._disp_font_face + ".ttf")
        self._disp_font = ImageFont.truetype(self._font_dir + self._disp_font_face + ".ttf", int(self._disp_font_size))
        self.show_text(self._settings.get(["display_text"]))

    def change_resolution(self, width = -1, height = -1):
        self._disp_width = self._settings.get(["display_width"]) if width == -1 else width
        self._disp_height = self._settings.get(["display_height"]) if height == -1 else height
        self._oled = adafruit_ssd1306.SSD1306_I2C(self._disp_width, self._disp_height, self._i2c, addr=self._disp_addr)
        self._oled.rotate(self._settings.get(["rotate_180"]))
        self._disp_rotate_180 = self._settings.get(["rotate_180"])

        # Clear display.
        self._oled.fill(0)
        self._oled.show()

        # Create blank image for drawing.
        # Make sure to create image with mode '1' for 1-bit color.
        self._disp_image = Image.new("1", (self._oled.width, self._oled.height))

        # Get drawing object to draw on image.
        self._disp_draw = ImageDraw.Draw(self._disp_image)
        self.show_text(self._settings.get(["display_text"]))
    
    def show_text(self, text):
        # Don't try to update the display if we're playing an animation
        if self._anim_task != None:
            return
        # Clear image buffer by drawing a black filled box.
        self._disp_draw.rectangle((0,0,self._oled.width,self._oled.height), outline=0, fill=0)
        # Draw Some Text
        (font_width, font_height) = self._disp_font.getsize(text)
        self._disp_draw.text(
            (self._oled.width // 2 - font_width // 2, self._oled.height // 2 - font_height // 2),
            text,
            font=self._disp_font,
            fill=255,
        )
        self._current_text = text

        # Display image
        self._oled.image(self._disp_image)
        self._oled.show()

    ##~ Animations
    def _play_demo_animation_fn(self):
        # Clear image buffer by drawing a black filled box.
        self._disp_draw.rectangle((0,0,self._oled.width,self._oled.height), outline=0, fill=0)
        self._logger.info("Demo animation started")
        # Define text and get total width.
        text = 'SSD1306 ORGANIC LED DISPLAY. THIS IS AN OLD SCHOOL DEMO SCROLLER!! GREETZ TO: LADYADA & THE ADAFRUIT CREW, TRIXTER, FUTURE CREW, AND FARBRAUSCH'
        maxwidth, unused = self._disp_draw.textsize(text, font=self._disp_font)
        try:
            # Set animation and sine wave parameters.
            amplitude = self._oled.width/4
            offset = self._oled.height/2 - 4
            velocity = -2
            startpos = self._oled.width

            # Animate text moving in sine wave.
            pos = startpos
            while True:
                # Clear image buffer by drawing a black filled box.
                self._disp_draw.rectangle((0,0,self._oled.width,self._oled.height), outline=0, fill=0)
                # Enumerate characters and draw them offset vertically based on a sine wave.
                x = pos
                for i, c in enumerate(text):
                    # Stop drawing if off the right side of screen.
                    if x > self._oled.width:
                        break
                    # Calculate width but skip drawing if off the left side of screen.
                    if x < -10:
                        char_width, char_height = self._disp_draw.textsize(c, font=self._disp_font)
                        x += char_width
                        continue
                    # Calculate offset from sine wave.
                    y = offset+math.floor(amplitude*math.sin(x/float(self._oled.width)*2.0*math.pi))
                    # Draw text.
                    self._disp_draw.text((x, y), c, font=self._disp_font, fill=255)
                    # Increment x position based on chacacter width.
                    char_width, char_height = self._disp_draw.textsize(c, font=self._disp_font)
                    x += char_width
                # Draw the image buffer.
                self._oled.image(self._disp_image)
                self._oled.show()
                # Move position for next frame.
                pos += velocity
                # Start over if text has scrolled completely off left side of screen.
                if pos < -maxwidth:
                    pos = startpos
                # Pause briefly before drawing next frame.
                time.sleep(0.1)
        except asyncio.CancelledError:
            self._logger.info('Demo animation cancelled')
            raise

    async def _play_demo_animation_wrapper(self):
        self._anim_task = asyncio.create_task(self._play_demo_animation_fn())
        await self._anim_task
    
    def play_demo_animation(self):
        asyncio.run(self._play_demo_animation_wrapper())

    ##~ EventHandlerPlugin mixin
    def on_event(self, event, payload):
        if event == "SettingsUpdated":
            self._logger.info("Updating display settings...")

            # Set display
            width = self._settings.get(["display_width"])
            height = self._settings.get(["display_height"])
            r180 = self._settings.get(["rotate_180"])
            if width != self._disp_width or height != self._disp_height:
                self._logger.info("Setting resolution: " + str(width) + "x" + str(height))
                self.change_resolution()
            elif r180 != self._disp_rotate_180:
                self._logger.info("Setting display rotation: " + str(r180))
                self._oled.rotate(r180)
                self._disp_rotate_180 = r180
                self._oled.show()

            # Set text
            new_text = int(self._settings.get(["display_text"]))
            new_text_size = int(self._settings.get(["display_font_size"]))
            if self._current_text != new_text or int(self._disp_font_size) != new_text_size:
                self._disp_font_size = new_text_size
                self._logger.info("Loading font: " + self._disp_font_face + ".ttf")
                self._disp_font = ImageFont.truetype(self._font_dir + self._disp_font_face + ".ttf", int(self._disp_font_size))
                self.show_text(new_text)
                self._logger.info("Set text: " + new_text)

            # Set animation
            if self._settings.get(["demo_anim"]) == True:
                self._logger.info("Playing demo animation...")
                self.play_demo_animation()
            else:
                if self._anim_task != None:
                    self._logger.info("Cancelling demo animation")
                    self._anim_task.cancel()
                    self._anim_task = None

    ##~ SimpleApiPlugin mixin
    def get_api_commands(self):
        return dict(
            # show_text=["text"]
            apply_settings=[]
        )

    def on_api_command(self, command, data):
        import flask
        # if command == "show_text":
        #     self._logger.info("Display show_text called: {parameter}".format(**data()))
        #     self.show_text(data)
        # elif command == "command2":
        #     self._logger.info("command2 called, some_parameter is {some_parameter}".format(**data))

        if command == "apply_settings":
            self._logger.info("Updated settings")
            self.apply_settings()

        return flask.jsonify(result="200 OK")

    def on_api_get(self, request):
        return flask.jsonify(text=self._settings.get(["display_text"]))

    ##~~ StartupPlugin mixin
    def on_startup(self, host, port):
        self._logger.info("Initializing OctOLED...")

    def on_after_startup(self):
        self._logger.info("Initial display text: %s" % self._settings.get(["display_text"]))
        self.init_display()

    ##~~ SettingsPlugin mixin
    def get_settings_defaults(self):
        return dict(
                display_text="Hello world!",
                display_font_size=14,
                display_width=128,
                display_height=32,
                rotate_180=False,
                demo_anim=False
            )

    # Disable custom bindings (??)
    def get_template_configs(self):
        return [
            dict(type="navbar", custom_bindings=False),
            dict(type="settings", custom_bindings=False)
        ]

    ##~~ AssetPlugin mixin

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return {
            "js": ["js/OctOLED.js"],
            "css": ["css/OctOLED.css"],
            "less": ["less/OctOLED.less"]
        }

    ##~~ Softwareupdate hook
    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        return {
            "OctOLED": {
                "displayName": "OctOLED",
                "displayVersion": self._plugin_version,

                # version check: github repository
                "type": "github_release",
                "user": "lmbernar@uark.edu",
                "repo": "octoled",
                "current": self._plugin_version,

                # update method: pip
                "pip": "https://github.com/lmbernar@uark.edu/octoled/archive/{target_version}.zip",
            }
        }


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "OctOLED"

# Starting with OctoPrint 1.4.0 OctoPrint will also support to run under Python 3 in addition to the deprecated
# Python 2. New plugins should make sure to run under both versions for now. Uncomment one of the following
# compatibility flags according to what Python versions your plugin supports!
#__plugin_pythoncompat__ = ">=2.7,<3" # only python 2
__plugin_pythoncompat__ = ">=3,<4" # only python 3
#__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3

def __plugin_load__():

    plugin = OctOLEDPlugin()

    global __plugin_implementation__
    __plugin_implementation__ = plugin

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }

    global __plugin_helpers__
    __plugin_helpers__ = dict(
        show_text=plugin.show_text
    )
