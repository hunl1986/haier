import json
import logging
import os
from datetime import timedelta

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .haier import HaierClient, HaierDevice

_LOGGER = logging.getLogger(__name__)


class DeviceCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, client: HaierClient, device: HaierDevice, sw_version, specs):
        super().__init__(
            hass,
            _LOGGER,
            name='Haier Device [' + device.id + ']',
            update_interval=timedelta(seconds=15),
        )

        self._client = client
        self._device = device
        self._device_info = DeviceInfo(
            identifiers={(DOMAIN, device.id.lower())},
            name=device.name,
            manufacturer='海尔',
            model=device.product_name,
            sw_version=sw_version
        )

        self._specs = specs

    @property
    def client(self):
        return self._client

    @property
    def device(self) -> HaierDevice:
        return self._device

    @property
    def device_info(self) -> DeviceInfo:
        return self._device_info

    @property
    def sensors(self):
        sensors = []
        for config_property in self._specs['Property']:
            # 跳过已禁用的项目
            if 'disable' in config_property and config_property['disable']:
                continue

            # 可写表示可操作，因为不应该归为传感器
            if config_property['writable']:
                continue

            if config_property['type'] == 'bool':
                continue

            formatter = {}
            if config_property['type'] in ['enum']:
                for item in config_property['variants']:
                    formatter[str(item['stdValue'])] = item['description']

            sensors.append({
                'key': config_property['name'],
                'display_name': config_property['description'],
                'unit': config_property['variants']['unit'] if 'unit' in config_property['variants'] else None,
                'value_formatter': formatter
            })

        return sensors

    @property
    def binary_sensors(self):
        binary_sensors = []
        for config_property in self._specs['Property']:
            # 跳过已禁用的项目
            if 'disable' in config_property and config_property['disable']:
                continue

            # 可写表示可操作，因为不应该归为传感器
            if config_property['writable']:
                continue

            if config_property['type'] != 'bool':
                continue

            binary_sensors.append({
                'key': config_property['name'],
                'display_name': config_property['description']
            })

        return binary_sensors

    @property
    def numbers(self):
        numbers = []
        for config_property in self._specs['Property']:
            # 跳过已禁用的项目
            if 'disable' in config_property and config_property['disable']:
                continue

            # 可写表示可操作，因为不应该归为传感器
            if config_property['writable'] and config_property['type'] in ['int', 'double']:
                numbers.append({
                    'key': config_property['name'],
                    'display_name': config_property['description'],
                    'minValue': config_property['variants']['minValue'],
                    'maxValue': config_property['variants']['maxValue'],
                    'step': config_property['variants']['step'],
                    'unit': config_property['variants']['unit'] if 'unit' in config_property['variants'] else None,
                })

        return numbers

    @property
    def selects(self):
        selects = []
        for config_property in self._specs['Property']:
            # 跳过已禁用的项目
            if 'disable' in config_property and config_property['disable']:
                continue

            # 可写表示可操作，因此不应该归为传感器
            if config_property['writable'] and config_property['type'] in ['enum']:
                selects.append({
                    'key': config_property['name'],
                    'display_name': config_property['description'],
                    'options': [{'value': item['stdValue'], 'label': item['description']} for item in
                                config_property['variants']]
                })

        return selects

    @property
    def switch(self):
        switch = []
        for config_property in self._specs['Property']:
            # 跳过已禁用的项目
            if 'disable' in config_property and config_property['disable']:
                continue

            if config_property['writable'] and config_property['type'] in ['bool']:
                switch.append({
                    'key': config_property['name'],
                    'display_name': config_property['description']
                })

        return switch

    async def _async_update_data(self):
        if self.device.is_virtual:
            with open(os.path.dirname(__file__) + '/virtual_devices/{}.json'.format(self.device.id)) as fp:
                return json.load(fp)['data']

        data = await self._client.get_last_report_status_by_device(self._device.id)

        _LOGGER.debug('设备[{}]已获取到最新状态数据: {}'.format(self._device.id, json.dumps(data)))

        return data
