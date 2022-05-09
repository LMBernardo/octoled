# OctOLED - OctoPrint OLED Display Plugin

### THIS PLUGIN IS EXPERIMENTAL AND IS CURRENTLY IN A PRE-RELEASE STATE!

Allows OctoPrint to display simple text on a SSD1306 OLED screen. Enables static text setting from preferences.
Specifically designed for the Raspberry Pi B+ using pins 3 and 5 for I2C data, but should work with any setup as
long as there is an I2C display at address 0x3C.

### TODO:
1. Expose API functions to enable other plugins to control the display
2. Add more features: 
    - Dynamic text
    - Animations
    - Manual drawing functions
    - Display profiles
    - Multi-display support (maybe)
    - Built-in display functions (e.g., show time, show print status, etc.)
    - Allow user extensibility
3. Support more display devices
4. Support more host devices
5. Better configuration options and setup process
6. TESTS!!!!
7. Add CI/CD process
8. Get plugin published in the Plugin Manager (WAITING FOR IMPROVEMENTS TO CODE - NOT CURRENTLY FIT FOR FULL RELEASE)
9. Attempt to disable display when shutting down / restarting

## Setup
Connect your display to the default I2C pins on the Raspberry Pi. CURRENTLY ONLY SUPPORTS DISPLAYS ON ADDRESS 0x3C!!

Install ~~via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html) or~~
manually using this URL:

    https://github.com/LMBernardo/octoled/archive/master.zip

## Configuration

Any user-editable configuration options are available under the plugin settings in OctoPrint.
You will need to set the appropriate screen resolution, orientation (normal or flipped), and font size for your application. 
