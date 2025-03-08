# myhome_dags

## Прошивка Zigbee для CC2531

Инструкция
с http://psenyukov.ru/%d0%bf%d1%80%d0%be%d1%88%d0%b8%d0%b2%d0%ba%d0%b0-zigbee-%d0%ba%d0%be%d0%bd%d1%82%d1%80%d0%be%d0%bb%d0%bb%d0%b5%d1%80%d0%b0-cc2652p-%d1%81-%d0%bf%d0%be%d0%bc%d0%be%d1%89%d1%8c%d1%8e-usb-ttl-%d0%bf/

Soft https://github.com/xyzroe/ZigStarGW-MT/releases

Прошивка https://github.com/Koenkk/Z-Stack-firmware/tree/master/coordinator/Z-Stack_3.x.0/bin

качаем CC1352P2_CC2652P_launchpad_coordinator_20230507.zip

Подключение к TTL конвертеру:
USB/TTL конвертор CC2652P Примечание
3.3 V VCC
GND GND
TX DIO_12
RX DIO_13
DIO_15 и GND СОединить время при подключении к USB и первой прошивке, чтоб ввести в режим прошивки контроллер. Далее
контакты разомкнуть.

Прошивка:

- Подключаем контроллер к USB/TTL конвертеру
- очищаем память контроллера
- прошиваем файл CC1352P2_CC2652P_launchpad_coordinator_20230507.hex
- верификация

# Подключение к TV box VONTAR x3

Описание https://psenyukov.ru/%D0%BF%D0%BE%D0%B4%D0%BA%D0%BB%D1%8E%D1%87%D0%B5%D0%BD%D0%B8%D0%B5-zigbee-cc2652p-%D0%BA-%D0%B2%D1%81%D1%82%D1%80%D0%BE%D0%B5%D0%BD%D0%BD%D0%BE%D0%BC%D1%83-uart-%D0%BF%D0%BE%D1%80%D1%82%D1%83-tv-box/

Схема
TV BOX Vontar X3 CC2652P
R DIO_13
T DIO_12
V VCC
G GND

