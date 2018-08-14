"""
Component to interface with universal radio control devices.

For more details about this component, please refer to the documentation
at https://home-assistant.io/components/radio/
"""
import asyncio
from datetime import timedelta
import functools as ft
import logging

import voluptuous as vol

from homeassistant.loader import bind_hass
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.entity import ToggleEntity
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
    STATE_ON, SERVICE_TURN_ON, SERVICE_TURN_OFF, SERVICE_TOGGLE,
    ATTR_ENTITY_ID)
from homeassistant.components import group
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA  # noqa

_LOGGER = logging.getLogger(__name__)

ATTR_ACTIVITY = 'activity'
ATTR_PROGRAMID = 'program_id'
ATTR_RINGTONEID = 'ringtone_id'
ATTR_VOLUME = 'volume'
ATTR_MESSAGE = "message"
ATTR_URL = "url"

DOMAIN = 'miio_acpartner'
DEPENDENCIES = ['group']
SCAN_INTERVAL = timedelta(seconds=30)

ENTITY_ID_ALL_RADIOS = group.ENTITY_ID_FORMAT.format('all_miio_acpartners')
ENTITY_ID_FORMAT = DOMAIN + '.{}'

GROUP_NAME_ALL_RADIOS = 'all miio_acpartners'

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=10)

SERVICE_PLAY_RADIO = 'play_radio'
SERVICE_SET_VOLUME = 'set_volume'
SERVICE_NEXT_RADIO = 'next_radio'
SERVICE_PREV_RADIO = 'prev_radio'
SERVICE_PLAY_RINGTONE = 'play_ringtone'
SERVICE_PLAY_TTS = 'play_tts'
SERVICE_PLAY_VOD = 'play_vod'
SERVICE_SYNC = 'sync'

DEFAULT_NUM_REPEATS = 1
DEFAULT_DELAY_SECS = 0.4

RADIO_SERVICE_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTITY_ID): cv.entity_ids,
})

RADIO_SERVICE_ACTIVITY_SCHEMA = RADIO_SERVICE_SCHEMA.extend({
    vol.Optional(ATTR_ACTIVITY): cv.string
})

RADIO_SERVICE_PLAY_RADIO_SCHEMA = RADIO_SERVICE_SCHEMA.extend({
    vol.Required(ATTR_PROGRAMID): cv.string,
})

RADIO_SERVICE_SET_VOLUME_SCHEMA = RADIO_SERVICE_SCHEMA.extend({
    vol.Required(ATTR_VOLUME): cv.string,
})

RADIO_SERVICE_PLAY_RINGTONE_SCHEMA = RADIO_SERVICE_SCHEMA.extend({
    vol.Required(ATTR_RINGTONEID): cv.string,
    vol.Optional(ATTR_VOLUME): cv.string
})

RADIO_SERVICE_PLAY_TTS_SCHEMA = RADIO_SERVICE_SCHEMA.extend({
    vol.Required(ATTR_MESSAGE): cv.string,
    vol.Optional(ATTR_VOLUME): cv.string
})

RADIO_SERVICE_PLAY_VOD_SCHEMA = RADIO_SERVICE_SCHEMA.extend({
    vol.Required(ATTR_URL): cv.string,
    vol.Optional(ATTR_VOLUME): cv.string
})

@bind_hass
def is_on(hass, entity_id=None):
    entity_id = entity_id or ENTITY_ID_ALL_RADIOS
    return hass.states.is_state(entity_id, STATE_ON)
    
@bind_hass
def turn_on(hass, activity=None, entity_id=None):
    data = {
        key: value for key, value in [
            (ATTR_ACTIVITY, activity),
            (ATTR_ENTITY_ID, entity_id),
        ] if value is not None}
    hass.services.call(DOMAIN, SERVICE_TURN_ON, data)
    
@bind_hass
def turn_off(hass, activity=None, entity_id=None):
    data = {}
    if activity:
        data[ATTR_ACTIVITY] = activity
    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id
    hass.services.call(DOMAIN, SERVICE_TURN_OFF, data)
    
@bind_hass
def toggle(hass, activity=None, entity_id=None):
    data = {}
    if activity:
        data[ATTR_ACTIVITY] = activity
    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id
    hass.services.call(DOMAIN, SERVICE_TOGGLE, data)

@bind_hass
def next_radio(hass, activity=None, entity_id=None):
    data = {}
    if activity:
        data[ATTR_ACTIVITY] = activity
    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id
    hass.services.call(DOMAIN, SERVICE_NEXT_RADIO, data)
    
@bind_hass
def prev_radio(hass, activity=None, entity_id=None):
    data = {}
    if activity:
        data[ATTR_ACTIVITY] = activity
    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id
    hass.services.call(DOMAIN, SERVICE_PREV_RADIO, data)

@bind_hass
def play_radio(hass, program_id, entity_id=None):
    data = {ATTR_PROGRAMID: program_id}
    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id
    hass.services.call(DOMAIN, SERVICE_PLAY_RADIO, data)

@bind_hass
def set_volume(hass, volume, entity_id=None):
    data = {ATTR_VOLUME: volume}
    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id
    hass.services.call(DOMAIN, SERVICE_SET_VOLUME, data)

@bind_hass
def play_ringtone(hass, ringtone_id, volume=None, entity_id=None):
    data = {ATTR_RINGTONEID, ringtone_id}
    if volume:
        data[ATTR_VOLUME] = volume
    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id
    hass.services.call(DOMAIN, SERVICE_PLAY_RINGTONE, data)
    
@bind_hass
def play_tts(hass, message, volume=None, entity_id=None):
    data = {ATTR_MESSAGE: message}
    if volume:
        data[ATTR_VOLUME] = volume
    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id
    hass.services.call(DOMAIN, SERVICE_PLAY_TTS, data)
    
@bind_hass
def play_vod(hass, url, volume=None, entity_id=None):
    data = {ATTR_URL: url}
    if volume:
        data[ATTR_VOLUME] = volume
    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id
    hass.services.call(DOMAIN, SERVICE_PLAY_VOD, data)    

@asyncio.coroutine
def async_setup(hass, config):
    component = EntityComponent(_LOGGER, DOMAIN, hass, SCAN_INTERVAL, GROUP_NAME_ALL_RADIOS)
    yield from component.async_setup(config)

    @asyncio.coroutine
    def async_handle_acpartner_service(service):
        target_radios = component.async_extract_from_service(service)
        kwargs = service.data.copy()

        update_tasks = []
        for radio in target_radios:
            if service.service == SERVICE_TURN_ON:
                yield from radio.async_turn_on(**kwargs)
            elif service.service == SERVICE_TOGGLE:
                yield from radio.async_toggle(**kwargs)
            elif service.service == SERVICE_PLAY_RADIO:
                yield from radio.async_play_radio(**kwargs)
            elif service.service == SERVICE_PREV_RADIO:
                yield from radio.async_prev_radio(**kwargs)
            elif service.service == SERVICE_NEXT_RADIO:
                yield from radio.async_next_radio(**kwargs)
            elif service.service == SERVICE_SET_VOLUME:
                yield from radio.async_set_volume(**kwargs)
            elif service.service == SERVICE_PLAY_RINGTONE:
                yield from radio.async_play_ringtone(**kwargs)
            elif service.service == SERVICE_PLAY_TTS:
                yield from radio.async_play_tts(**kwargs)
            elif service.service == SERVICE_PLAY_VOD:
                yield from radio.async_play_vod(**kwargs)
            else:
                yield from radio.async_turn_off(**kwargs)
            if not radio.should_poll:
                continue
            update_tasks.append(radio.async_update_ha_state(True))
        if update_tasks:
            yield from asyncio.wait(update_tasks, loop=hass.loop)

    hass.services.async_register(
        DOMAIN, SERVICE_TURN_OFF, async_handle_acpartner_service,
        schema=RADIO_SERVICE_ACTIVITY_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_TURN_ON, async_handle_acpartner_service,
        schema=RADIO_SERVICE_ACTIVITY_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_TOGGLE, async_handle_acpartner_service,
        schema=RADIO_SERVICE_ACTIVITY_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_NEXT_RADIO, async_handle_acpartner_service,
        schema=RADIO_SERVICE_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_PREV_RADIO, async_handle_acpartner_service,
        schema=RADIO_SERVICE_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_SET_VOLUME, async_handle_acpartner_service,
        schema=RADIO_SERVICE_SET_VOLUME_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_PLAY_RADIO, async_handle_acpartner_service,
        schema=RADIO_SERVICE_PLAY_RADIO_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_PLAY_RINGTONE, async_handle_acpartner_service,
        schema=RADIO_SERVICE_PLAY_RINGTONE_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_PLAY_TTS, async_handle_acpartner_service,
        schema=RADIO_SERVICE_PLAY_TTS_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_PLAY_VOD, async_handle_acpartner_service,
        schema=RADIO_SERVICE_PLAY_VOD_SCHEMA)

    return True


class RadioDevice(ToggleEntity):
    def play_radio(self, program_id, **kwargs):
        raise NotImplementedError()
    def async_play_radio(self, program_id, **kwargs):
        return self.hass.async_add_job(ft.partial(self.play_radio, program_id, **kwargs))
            
    def set_volume(self, volume, **kwargs):
        raise NotImplementedError()
    def async_set_volume(self, volume, **kwargs):
        return self.hass.async_add_job(ft.partial(self.set_volume, volume, **kwargs))
            
    def next_radio(self, **kwargs):
        raise NotImplementedError()
    def async_next_radio(self, **kwargs):
        return self.hass.async_add_job(ft.partial(self.next_radio, **kwargs))
            
    def prev_radio(self, **kwargs):
        raise NotImplementedError()
    def async_prev_radio(self, **kwargs):
        return self.hass.async_add_job(ft.partial(self.prev_radio, **kwargs))
        
    def play_ringtone(self, ringtone_id, **kwargs):
        raise NotImplementedError()
    def async_play_ringtone(self, ringtone_id, **kwargs):
        return self.hass.async_add_job(ft.partial(self.play_ringtone, ringtone_id, **kwargs))
        
    def play_tts(self, message, **kwargs):
        raise NotImplementedError()
    def async_play_tts(self, message, **kwargs):
        return self.hass.async_add_job(ft.partial(self.play_tts, message, **kwargs))
        
    def play_vod(self, message, **kwargs):
        raise NotImplementedError()
    def async_play_vod(self, message, **kwargs):
        return self.hass.async_add_job(ft.partial(self.play_vod, message, **kwargs))
