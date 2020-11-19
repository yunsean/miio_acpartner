"""
Support for the Xiaomi Gateway Radio.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/radio.xiaomi_miio/
"""
import functools
import logging
import time
import json
import os
import urllib
import requests
import asyncio
import async_timeout
import sys
import functools as ft
sys.path.append("../..")

# https://github.com/rytilahti/python-miio/issues/295
# 这里面有很多有价值的代码

from datetime import timedelta
from haffmpeg.core import HAFFmpeg

import voluptuous as vol

from custom_components.miio_acpartner import (
    PLATFORM_SCHEMA, DOMAIN, ATTR_VOLUME, RadioDevice)
from homeassistant.components.ffmpeg import (
    DATA_FFMPEG, CONF_EXTRA_ARGUMENTS)    
from homeassistant.const import (
    CONF_NAME, CONF_TOKEN, CONF_TIMEOUT,
    ATTR_ENTITY_ID, ATTR_HIDDEN, CONF_COMMAND)
from homeassistant.exceptions import PlatformNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.util.dt import utcnow

_LOGGER = logging.getLogger(__name__)
CONF_APIKEY = 'api_key'
CONF_SECRETKEY = 'secret_key'
CONF_SPEED =  'speed'
CONF_PITCH = 'pitch'
CONF_VOLUME = 'volume'
CONF_PERSON = 'person'
CONF_BASEURL = "base_url"
CONF_BASEPATH = "base_path"
CONF_NOTIFY = "notify"
CONF_HOST = "host"

LEARN_COMMAND_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): vol.All(str),
})

COMMAND_SCHEMA = vol.Schema({
    vol.Required(CONF_COMMAND): vol.All(cv.ensure_list, [cv.string])
    })

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME): cv.string,
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_TOKEN): vol.All(str, vol.Length(min=32, max=32)),
    vol.Optional(CONF_APIKEY): cv.string,
    vol.Optional(CONF_SECRETKEY): cv.string,
    vol.Optional(CONF_BASEURL, default = ''): cv.string,
    vol.Optional(CONF_BASEPATH, default = ''): cv.string,
    vol.Optional(CONF_SPEED, default = '5'): cv.string,
    vol.Optional(CONF_PITCH, default = '7'): cv.string,
    vol.Optional(CONF_VOLUME, default = '4'): cv.string,
    vol.Optional(CONF_PERSON, default = '0'): cv.string,
    vol.Optional(CONF_NOTIFY, default = False): cv.boolean,
}, extra=vol.ALLOW_EXTRA)


@asyncio.coroutine
def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    from miio import Device, DeviceException

    host = config.get(CONF_HOST)
    token = config.get(CONF_TOKEN)
    baseUrl = config.get(CONF_BASEURL)
    basePath = config.get(CONF_BASEPATH)
    apiKey = config.get(CONF_APIKEY) 
    secretKey = config.get(CONF_SECRETKEY)  
    speed = config.get(CONF_SPEED, 5)
    pitch = config.get(CONF_PITCH, 5)  
    volume = config.get(CONF_VOLUME, 5) 
    person = config.get(CONF_PERSON, 0) 
    notify = config.get(CONF_NOTIFY, False)
    _LOGGER.info("Initializing with host %s (token %s...)", host, token[:5])
    device = Device(host, token, lazy_discover=False)
    try:
        device_info = device.info()
        model = device_info.model
        unique_id = "{}-{}".format(model, device_info.mac_address)
        _LOGGER.info("%s %s %s detected",
                     model,
                     device_info.firmware_version,
                     device_info.hardware_version)
    except DeviceException as ex:
        _LOGGER.error("Device unavailable or token incorrect: %s", ex)
        raise PlatformNotReady
    friendly_name = config.get(CONF_NAME, "miio_miio_acpartner_" + host.replace('.', '_'))
    xiaomi_miio_radio = XiaomiMiioRadio(hass, friendly_name, device, unique_id, apiKey, secretKey, speed, pitch, volume, person, baseUrl, basePath, notify)
    async_add_devices([xiaomi_miio_radio])

TOKEN_INTERFACE = 'https://openapi.baidu.com/oauth/2.0/token'
TEXT2AUDIO_INTERFACE = 'http://tsn.baidu.com/text2audio'
def get_url(url, verify, params) -> object:
    return requests.get(url, verify=verify, params=params)  
class BaiduTTS:
    def __init__(self, hass, apiKey, secretKey, speed = 5, pitch = 5, volume = 15, person = 0):
        self._hass = hass
        self.apiKey = apiKey
        self.secretKey = secretKey
        self.speed = speed
        self.pitch = pitch
        self.volume = volume
        self.person = person
        self.Token = None
    @asyncio.coroutine
    def get_token(self):
        try:
            resp = yield from self._hass.async_add_executor_job(get_url, TOKEN_INTERFACE, False, {'grant_type': 'client_credentials',
                                                         'client_id': self.apiKey,
                                                         'client_secret':self.secretKey})
            if resp.status_code != 200:
                _LOGGER.error('Get ToKen Http Error status_code:%s' % resp.status_code)
                return None
            resp.encoding = 'utf-8'
            tokenJson = resp.json()
            if not 'access_token' in tokenJson:
                _LOGGER.error('Get ToKen Json Error!')
                return None
            return tokenJson['access_token']
        except Exception as ex:
            _LOGGER.error(ex)
            return None
    @asyncio.coroutine
    def generate_tts(self, message, file):
        try:
            if self.Token == None:
                self.Token = yield from self.get_token()
            if self.Token == None:
                _LOGGER.error('get_tts_audio Self.ToKen is nil')
                return False
            resp = yield from self._hass.async_add_executor_job(get_url, TEXT2AUDIO_INTERFACE, False, {'tex': urllib.parse.quote(message),
                                                             'lan': 'zh',
                                                             'tok': self.Token,
                                                             'ctp': '1',
                                                             'aue': 6,
                                                             'cuid': 'HomeAssistant',
                                                             'spd': self.speed,
                                                             'pit': self.pitch,
                                                             'vol': self.volume,
                                                             'per': self.person})
            if resp.status_code == 500:
                _LOGGER.error('Text2Audio Error:500 Not Support.')
                return False
            if resp.status_code == 501:
                _LOGGER.error('Text2Audio Error:501 Params Error')
                return False
            if resp.status_code == 502:
                _LOGGER.wran('Text2Audio Error:502 TokenVerificationError, Now Get Token!')
                self.Token = yield from self.get_token()
                res = yield from self.generate_tts(message, file)
                return res
            if resp.status_code == 503:
                _LOGGER.error('Text2Audio Error:503 Composite Error.')
                return False
            if resp.status_code != 200:
                _LOGGER.error('get_tts_audio Http Error status_code:%s' % resp.status_code)
                return False
            open(file, "wb").write(resp.content)
            return True    
        except Exception as ex:
            _LOGGER.error(ex)
            return False

class AacConverter(HAFFmpeg):
    @asyncio.coroutine
    def convert(self, input_source, output, extra_cmd=None, timeout=15):
        command = [
            "-vn",
            "-c:a",
            "aac",
            "-strict",
            "-2",
            "-b:a",
            "64K",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-y"
        ]      
        is_open = yield from self.open(cmd=command, input_source=input_source, output=output, extra_cmd=extra_cmd)         
        if not is_open:
            _LOGGER.warning("Error starting FFmpeg.")
            return False
        try:
            proc_func = functools.partial(self._proc.communicate, timeout=timeout)
            out, error = yield from self._loop.run_in_executor(None, proc_func)
        except (asyncio.TimeoutError, ValueError):
            _LOGGER.error("Timeout convert audio file.")
            self._proc.kill()
            return False    
        return True         
            
class XiaomiMiioRadio(RadioDevice):
    def __init__(self, hass, friendly_name, device, unique_id, apiKey, secretKey, speed, pitch, volume, person, baseUrl, basePath, notify):
        self._hass = hass
        self._name = friendly_name
        self._device = device
        self._unique_id = unique_id
        self._state = False
        self._baidu = None
        self._apiKey = apiKey
        self._secretKey = secretKey
        self._speed = speed
        self._pitch = pitch
        self._volume = volume
        self._person = person
        self._mp3Path = basePath + "/www/tts_" + str(unique_id).replace(":", "") + ".wav"
        self._aacPath = basePath + "/www/tts_" + str(unique_id).replace(":", "") + ".aac"
        self._ttsUrl = baseUrl + "/local/tts_" + str(unique_id).replace(":", "") + ".aac"
        self._notify = notify
        self._channels = self.all_channels()
        self._spaceFree = self._device.send("get_music_free_space", [])
        self._alarm = self.all_ringtones(0)
        self._clock = self.all_ringtones(1)
        self._chord = self.all_ringtones(2)
        self._custom = self.all_ringtones(3, False)
        self._state = False
        self._attributes = {}
    @property
    def name(self):
        return self._name
    @property
    def device(self):
        return self._device
    @property
    def is_on(self):
        return self._state
    @property
    def should_poll(self):
        return True
    def all_channels(self):
        index = 0
        channels = []
        result = self._device.send("get_channels", {"start": 0})
        while "chs" in result:
            for ch in result["chs"]:
                if "id" in ch:
                    channels.append(ch["id"])
            index = index + 10
            result = self._device.send("get_channels", {"start": index})
        return channels
    def all_ringtones(self, type, sysOnly = True):
        ringtones = []
        result = self._device.send("get_music_info", [type])
        if "list" in result:
            result = result["list"]
            for ringtone in result:
                if (not sysOnly) or (int(ringtone["mid"]) < 1000):
                    ringtones.append(ringtone["mid"])
        return ringtones
    @property
    def device_state_attributes(self):
        return self._attributes

    @asyncio.coroutine
    def async_update(self):
        return self.hass.async_add_job(ft.partial(self.update_state))

    def update_state(self):
        from miio import DeviceException
        try:
            status = self._device.send("get_prop_fm", [])
            self._attributes = {
                'hidden': 'true',
                'miio_channels': self._channels,
                'space_free': self._spaceFree,
                'channel': status["current_program"],
                'volume': status["current_volume"],
                'miio_ringtones': {
                    'alarm': self._alarm,
                    'clock': self._clock,
                    'chord': self._chord,
                    'custom': self._custom
                }
            }
            self._state = status["current_status"] == "run"
        except DeviceException:
            self._state = False        
        self.hass.states.async_set(DOMAIN + "." + self._name, "on" if self._state else "off", self._attributes)
        
    @asyncio.coroutine
    def async_toggle(self, **kwargs):
        if self.is_on:
            self._device.send('play_fm', ["off"])
        else:
            self._device.send('play_fm', ["on"])
        self.hass.async_add_job(ft.partial(self.update_state))
    # pylint: disable=R0201
    @asyncio.coroutine
    def async_turn_on(self, **kwargs):
        self._device.send('play_fm', ["on"])
        self.hass.async_add_job(ft.partial(self.update_state))
    @asyncio.coroutine
    def async_turn_off(self, **kwargs):
        self._device.send('play_fm', ["off"])
        self.hass.async_add_job(ft.partial(self.update_state))
                    
    def set_volume(self, volume, **kwargs):
        if volume is None:
            _LOGGER.debug("Empty packet.")
            return True
        try:
            self._device.send('volume_ctrl_fm', [str(volume)])
        except ValueError as error:
            _LOGGER.error(error)
            return False
        self.hass.async_add_job(ft.partial(self.update_state))
        return True  
    def next_radio(self, **kwargs):
        try:
            status = self._device.send("get_prop_fm", [])
            channel = status["current_program"]
            channels = self.all_channels()
            if len(channels) < 1:
                return False
            current_index = -1
            for idx, val in enumerate(channels):
                if val == channel:
                    current_index = idx
                    break
            if current_index == -1:
                current_index = 0
            elif current_index >= len(channels) - 1:
                current_index = 0
            else:
                current_index = current_index + 1
            channel = channels[current_index]
            self._device.send("play_specify_fm", {'id': channel, 'type': 0})
        except ValueError as error:
            _LOGGER.error(error)
            return False
        self.hass.async_add_job(ft.partial(self.update_state))
        return True
    def prev_radio(self, **kwargs):
        try:
            status = self._device.send("get_prop_fm", [])
            channel = status["current_program"]
            channels = self.all_channels()
            if len(channels) < 1:
                return False
            current_index = -1
            for idx, val in enumerate(channels):
                if val == channel:
                    current_index = idx
                    break
            if current_index == -1:
                current_index = 0
            elif current_index == 0:
                current_index = len(channels) - 1
            else:
                current_index = current_index - 1
            channel = channels[current_index]
            self._device.send("play_specify_fm", {'id': channel, 'type': 0})
        except ValueError as error:
            _LOGGER.error(error)
            return False
        self.hass.async_add_job(ft.partial(self.update_state))
        return True  

    def play_radio(self, program_id, **kwargs):
        if program_id is None:
            return True
        try:
            self._device.send('play_specify_fm', {'id': int(str(program_id)), 'type': 0})
        except ValueError as error:
            return False
        self.hass.async_add_job(ft.partial(self.update_state))
        return True
    @asyncio.coroutine
    def async_play_ringtone(self, ringtone_id, **kwargs):
        if ringtone_id is None:
            return True
        volume = kwargs.get(ATTR_VOLUME)
        try:
            if volume == None:
                self._device.send('play_music',[int(str(ringtone_id))])
            else:    
                self._device.send('play_music_new', [str(ringtone_id), int(str(volume))])
        except ValueError as error:
            return False
        return True
       
    @asyncio.coroutine
    def async_play_tts(self, message, **kwargs):
        if message is None:
            _LOGGER.warning("message is not present.")
            return True
        volume = kwargs.get(ATTR_VOLUME)        
        try:
            if (self._baidu == None) and (self._apiKey == None or self._secretKey == None):
                _LOGGER.error("The baidu tts api key is not configured.")
                return False
            if self._baidu == None:
                self._baidu = BaiduTTS(self._hass, self._apiKey, self._secretKey, self._speed, self._pitch, self._volume, self._person)
            res = yield from self._baidu.generate_tts(message, self._mp3Path)
            if not res:
                _LOGGER.error("generate tts failed.")
                return False
            if os.path.exists(self._aacPath):
                os.remove(self._aacPath)
            ffmpeg = AacConverter(self.hass.data[DATA_FFMPEG].binary, loop=self.hass.loop)
            result = yield from ffmpeg.convert(self._mp3Path, output=self._aacPath)
            if (not result) or (not os.path.exists(self._aacPath)) or (os.path.getsize(self._aacPath) < 1):
                _LOGGER.error("Convert file to aac failed.")
                return False 
            self._device.send("delete_user_music", ['99999'])
            self._device.send("download_user_music", ["99999", self._ttsUrl])
            _LOGGER.error(self._ttsUrl)
            index = 0
            while index < 10:
                progess = self._device.send("get_download_progress", [])
                if str(progess) == "['99999:100']":
                    break
                index += 1
                yield from asyncio.sleep(1)
            if (index >= 10):
                _LOGGER.error("download tts file [" + self._ttsUrl + "] to gateway failed.")
                return False
            if volume == None:
                self._device.send('play_music', [99999])
            else:    
                self._device.send('play_music_new', ["99999", int(str(volume))])
            if self._notify:
                log_msg = "TTS: %s" % message
                self.hass.components.persistent_notification.async_create(log_msg, title='AC partner TTS', notification_id="99999") 
        except Exception as error:
            _LOGGER.error(error)
            return False
        return True 
       
    @asyncio.coroutine
    def async_play_vod(self, url, **kwargs):
        if url is None:
            _LOGGER.warning("message is not present.")
            return True
        volume = kwargs.get(ATTR_VOLUME)        
        try:
            urllib.request.urlretrieve(url, self._mp3Path)
            if os.path.exists(self._aacPath):
                os.remove(self._aacPath)
            ffmpeg = AacConverter(self.hass.data[DATA_FFMPEG].binary, loop=self.hass.loop)
            result = yield from ffmpeg.convert(self._mp3Path, output=self._aacPath)
            if (not result) or (not os.path.exists(self._aacPath)) or (os.path.getsize(self._aacPath) < 1):
                _LOGGER.error("Convert file to aac failed.")
                return False 
            self._device.send("delete_user_music", ['99999'])
            self._device.send("download_user_music", ["99999", self._ttsUrl])
            index = 0
            while index < 60:
                progess = self._device.send("get_download_progress", [])
                _LOGGER.error(progess)
                if str(progess) == "['99999:100']":
                    break
                index += 1
                yield from asyncio.sleep(1)
            if (index >= 60):
                _LOGGER.error("download tts file to gateway failed.")
                return False
            if volume == None:
                self._device.send('play_music', [99999])
            else:    
                self._device.send('play_music_new', ["99999", int(str(volume))])
            _LOGGER.error("play_vod(%s)" % url) 
            if self._notify:
                log_msg = "VOD finished."
                self.hass.components.persistent_notification.async_create(log_msg, title='AC partner TTS', notification_id="99999") 
        except Exception as error:
            _LOGGER.error(error)
            return False
        return True  
            