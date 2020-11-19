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
from homeassistant.helpers.config_validation import (  # noqa
    make_entity_service_schema,
    PLATFORM_SCHEMA,
    PLATFORM_SCHEMA_BASE,
)
from homeassistant.const import (
    STATE_ON, SERVICE_TURN_ON, SERVICE_TURN_OFF, SERVICE_TOGGLE,
    ATTR_ENTITY_ID)
from homeassistant.components import group
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA  # noqa

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'miio_acpartner'
SCAN_INTERVAL = timedelta(seconds=30)

GROUP_NAME_ALL_RADIOS = 'all radios'
ENTITY_ID_ALL_RADIOS = group.ENTITY_ID_FORMAT.format('all_radios')

ATTR_ACTIVITY = 'activity'
ATTR_PROGRAMID = 'program_id'
ATTR_RINGTONEID = 'ringtone_id'
ATTR_VOLUME = 'volume'
ATTR_MESSAGE = "message"
ATTR_URL = "url"

ENTITY_ID_FORMAT = DOMAIN + '.{}'
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

ENTITY_SERVICE_SCHEMA = vol.Schema({
    vol.Optional(ATTR_ENTITY_ID): cv.entity_ids
})  
RADIO_SERVICE_ACTIVITY_SCHEMA = make_entity_service_schema({
    vol.Optional(ATTR_ACTIVITY): cv.string
})

RADIO_SERVICE_PLAY_RADIO_SCHEMA = make_entity_service_schema({
    vol.Required(ATTR_PROGRAMID): cv.string,
})

RADIO_SERVICE_SET_VOLUME_SCHEMA = make_entity_service_schema({
    vol.Required(ATTR_VOLUME): cv.string,
})

RADIO_SERVICE_PLAY_RINGTONE_SCHEMA = make_entity_service_schema({
    vol.Required(ATTR_RINGTONEID): cv.string,
    vol.Optional(ATTR_VOLUME): cv.string
})

RADIO_SERVICE_PLAY_TTS_SCHEMA = make_entity_service_schema({
    vol.Required(ATTR_MESSAGE): cv.string,
    vol.Optional(ATTR_VOLUME): cv.string
})

RADIO_SERVICE_PLAY_VOD_SCHEMA = make_entity_service_schema({
    vol.Required(ATTR_URL): cv.string,
    vol.Optional(ATTR_VOLUME): cv.string
})

@bind_hass
def is_on(hass, entity_id=None):
    entity_id = entity_id or ENTITY_ID_ALL_RADIOS
    return hass.states.is_state(entity_id, STATE_ON)

@asyncio.coroutine
def async_setup(hass, config):
    component = hass.data[DOMAIN] = EntityComponent(
        _LOGGER, DOMAIN, hass, SCAN_INTERVAL
    )
    yield from component.async_setup(config)

    component.async_register_entity_service(
        SERVICE_TURN_ON, ENTITY_SERVICE_SCHEMA, "async_turn_on"
    )
    component.async_register_entity_service(
        SERVICE_TURN_OFF, ENTITY_SERVICE_SCHEMA, "async_turn_off"
    )
    component.async_register_entity_service(
        SERVICE_TOGGLE, ENTITY_SERVICE_SCHEMA, "async_toggle"
    )
    component.async_register_entity_service(
        SERVICE_NEXT_RADIO, ENTITY_SERVICE_SCHEMA, "async_next_radio"
    )
    component.async_register_entity_service(
        SERVICE_PREV_RADIO, ENTITY_SERVICE_SCHEMA, "async_prev_radio"
    )
    component.async_register_entity_service(
        SERVICE_SET_VOLUME, RADIO_SERVICE_SET_VOLUME_SCHEMA, "async_set_volume"
    )
    component.async_register_entity_service(
        SERVICE_PLAY_RADIO, RADIO_SERVICE_PLAY_RADIO_SCHEMA, "async_play_radio"
    )
    component.async_register_entity_service(
        SERVICE_PLAY_RINGTONE, RADIO_SERVICE_PLAY_RINGTONE_SCHEMA, "async_play_ringtone"
    )
    component.async_register_entity_service(
        SERVICE_PLAY_TTS, RADIO_SERVICE_PLAY_TTS_SCHEMA, "async_play_tts"
    )
    component.async_register_entity_service(
        SERVICE_PLAY_VOD, RADIO_SERVICE_PLAY_VOD_SCHEMA, "async_play_vod"
    )
    return True


async def async_setup_entry(hass, entry):
    """Set up a config entry."""
    return await hass.data[DOMAIN].async_setup_entry(entry)
async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    return await hass.data[DOMAIN].async_unload_entry(entry)

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
