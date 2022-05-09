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
    # May throw on _oled.show() or show_text()
    def init_display(self, width = -1, height = -1):
        # TODO: Width and height can be obtained from self._oled once initialized so we probably don't need to store these
        # TODO: Actually we probably don't need to store any of these that are saved in _settings - or at least just store the ones that are frequently accessed
        # TODO: Expose more configuration options on the plugin settings page
        self._disp_width = self._settings.get(["display_width"]) if width == -1 else width
        self._disp_height = self._settings.get(["display_height"]) if height == -1 else height
        self._disp_rotate_180 = self._settings.get(["rotate_180"])
        self._disp_font_face = "Noto_Sans/NotoSans-Regular"
        self._disp_font_size = int(self._settings.get(["display_font_size"]))
        self._disp_border = 5
        # TODO: Scan I2C and present a list of options in the settings page
        self._disp_addr = 0x3C
        self._current_text = self._settings.get(["display_text"])
        self._anim_task = None
        self._font_dir = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + '/fonts') + '/'
        # Only I2C displays are supported
        self._i2c = board.I2C()
        # TODO: Support more display types
        self._oled = adafruit_ssd1306.SSD1306_I2C(self._disp_width, self._disp_height, self._i2c, addr=self._disp_addr)
        # reset=oled_reset)
        if self._disp_rotate_180:
            self._oled.rotation = 2
        else:
            self._oled.rotation = 0

        # Create blank image for drawing.
        # Make sure to create image with mode '1' for 1-bit color.
        self._disp_image = Image.new("1", (self._oled.width, self._oled.height))

        # Get drawing object to draw on image.
        self._disp_draw = ImageDraw.Draw(self._disp_image)
        self._logger.info("Loading font: " + self._disp_font_face + ".ttf")
        self._disp_font = ImageFont.truetype(self._font_dir + self._disp_font_face + ".ttf", int(self._disp_font_size))

        # Clear display.
        self._oled.fill(0)
        self._oled.show()
        # Draw text
        self.show_text(self._settings.get(["display_text"]))

    def change_resolution(self, width = -1, height = -1):
        self._disp_width = self._settings.get(["display_width"]) if width == -1 else width
        self._disp_height = self._settings.get(["display_height"]) if height == -1 else height
        self._logger.info("Setting resolution: " + str(self._disp_width) + "x" + str(self._disp_height))
        self._oled = adafruit_ssd1306.SSD1306_I2C(self._disp_width, self._disp_height, self._i2c, addr=self._disp_addr)
        if self._disp_rotate_180 != self._settings.get(["rotate_180"]):
            self._logger.info("Flipping display")
        if self._disp_rotate_180:
            self._oled.rotation = 2
        else:
            self._oled.rotation = 0

        # Clear display.
        self._oled.fill(0)

        # Create blank image for drawing.
        # Make sure to create image with mode '1' for 1-bit color.
        self._disp_image = Image.new("1", (self._oled.width, self._oled.height))

        # Get drawing object to draw on image.
        self._disp_draw = ImageDraw.Draw(self._disp_image)

        if self._enabled:
            try:
                self._oled.show()
            except OSError as os_err:
                self._logger.error("IO error: " + str(os_err))
            except Exception as err:
                self._logger.error("Unknown error: " + str(err))

        if self._anim_task is None:
            self.show_text(self._settings.get(["display_text"]))
    
    def show_text(self, text):
        # Don't try to update the display if we're playing an animation
        if self._anim_task != None:
            self._logger.info("Animation task is not None, skipping show_text")
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
        if self._enabled:
            try:
                self._oled.show()
            except OSError as os_err:
                self._logger.error("IO error: " + str(os_err))
            except Exception as err:
                self._logger.error("Unknown error: " + str(err))
        else:
            self._logger.info("show_text: Display disabled, skipping show()")

    ##~ Animations

    # # ATTRIBUTION FOR _play_demo_animation_fn():
    # # Copyright (c) 2014 Adafruit Industries
    # # Author: Tony DiCola
    # # 
    # # Permission is hereby granted, free of charge, to any person obtaining a copy
    # # of this software and associated documentation files (the "Software"), to deal
    # # in the Software without restriction, including without limitation the rights
    # # to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    # # copies of the Software, and to permit persons to whom the Software is
    # # furnished to do so, subject to the following conditions:
    # # 
    # # The above copyright notice and this permission notice shall be included in
    # # all copies or substantial portions of the Software.
    # # 
    # # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    # # IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    # # FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    # # AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    # # LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    # # OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
    # # THE SOFTWARE.
    # https://github.com/adafruit/Adafruit_Python_SSD1306/blob/master/examples/animate.py

    # May throw
    # TODO: Get this to work with asyncio
    def _play_demo_animation_fn(self):
        if not self._enabled:
            return
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
                # Clear image buffer by drawing a black filled box.1
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
        except Exception as err:
            self._logger.error("Unknown error: " + str(err))
            raise

    # TODO: Fix this
    async def _play_demo_animation_wrapper(self):
        self._anim_task = asyncio.create_task(self._play_demo_animation_fn())
        await self._anim_task
    
    # TODO: Fix this
    def play_demo_animation(self):
        asyncio.run(self._play_demo_animation_wrapper())

    ##~ EventHandlerPlugin mixin
    def on_event(self, event, payload):
        # self._logger.debug("Event payload: " + str(payload))
        # TODO: Massively refactor this, please
        if event == "SettingsUpdated":
            self._logger.info("Updating display settings...")
            self._enabled = self._settings.get(["enabled"])

            self._logger.info("Display enabled: " + str(self._settings.get(["enabled"])))
            self._logger.debug("Display Width: " + str(self._settings.get(["display_width"])))
            self._logger.debug("Display Height: " + str(self._settings.get(["display_height"])))
            self._logger.debug("Display Rotation: " + str(self._settings.get(["rotate_180"])))
            self._logger.debug("Display Text: " + str(self._settings.get(["display_text"])))
            self._logger.debug("Display Font Size: " + str(self._settings.get(["display_font_size"])))
            self._logger.debug("Display Demo Animation: " + str(self._settings.get(["demo_anim"])))

            # Set display
            width = self._settings.get(["display_width"])
            height = self._settings.get(["display_height"])
            r180 = self._settings.get(["rotate_180"])
            if width != self._disp_width or height != self._disp_height or r180 != self._disp_rotate_180:
                self.change_resolution()

            # Set text
            new_text = self._settings.get(["display_text"])
            new_text_size = int(self._settings.get(["display_font_size"]))

            if int(self._disp_font_size) != new_text_size:
                self._disp_font_size = new_text_size
                self._logger.info("Reloading font: " + self._disp_font_face + ".ttf")
                self._disp_font = ImageFont.truetype(self._font_dir + self._disp_font_face + ".ttf", int(self._disp_font_size))
                
            # Set animation
            if self._settings.get(["demo_anim"]) == True:
                self._logger.info("Playing demo animation...")
                self.play_demo_animation()
            elif self._anim_task != None:
                    self._logger.info("Cancelling demo animation")
                    self._anim_task.cancel()
                    self._anim_task = None

            if not self._settings.get(["enabled"]):
                self._oled.fill(0)
                try:
                    self._oled.show()
                except Exception as err:
                    self._logger.info("Failed to clear display")

            if self._anim_task is None:
                self._logger.info("Updating display text")
                self.show_text(new_text)

            self._logger.info("Updated settings")

    ##~ SimpleApiPlugin mixin
    # TODO: Implement plugin API
    def get_api_commands(self):
        return dict(
            # show_text=["text"]
            apply_settings=[]
        )

    # TODO: Implement plugin API
    def on_api_command(self, command, data):
        import flask
        # if command == "show_text":
        #     self._logger.info("Display show_text called: {parameter}".format(**data()))
        #     self.show_text(data)
        # elif command == "command2":
        #     self._logger.info("command2 called, some_parameter is {some_parameter}".format(**data))

        # TODO: Unfinished
        # if command == "apply_settings":
        #     self.apply_settings()
        #     self._logger.info("Updated settings")

        return flask.jsonify(result="200 OK")

    # TODO: Implement plugin API
    def on_api_get(self, request):
        return flask.jsonify(text=self._settings.get(["display_text"]))

    ##~~ StartupPlugin mixin
    def on_startup(self, _host, _port):
        self._logger.info("Initializing OctOLED...")

    def on_after_startup(self):
        self._enabled = self._settings.get(["enabled"])
        self._logger.info("Enabled: %s" % str(self._enabled))
        self._logger.info("Display Resolution: {0}x{1} (width x height)".format(self._settings.get(["display_width"]), self._settings.get(["display_height"])))
        error = False
        try:
            self.init_display()
        except ValueError as init_error:
            self._logger.error("Failed to initialize! Display not found: " + str(init_error))
            error = True
        except Exception as err:
            self._logger.error("Failed to initialize! Unknown error: " + str(err))
            error = True
        else:
            self._logger.info("Initialization complete.")
        finally:
            if error and self._enabled:
                self._logger.info("Disabling OctOLED!")
                self._enabled = False
                self._settings.set(["enabled"], False)

    ##~~ SettingsPlugin mixin
    def get_settings_defaults(self):
        return dict(
                enabled=True,
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
