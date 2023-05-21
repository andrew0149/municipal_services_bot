# файл, содержащий все действия, доступные пользователю и администратору

ADD_USER = 'Добавить пользователя'
DEL_USER = 'Удалить пользователя'
UPDATE_USER = 'Обновить тариф пользователя'
ADD_TARIFF = 'Добавить тариф'
DEL_TARIFF = 'Удалить тариф'
UPDATE_TARIFF = 'Обновить стоимость тарифа'
ADD_DEVICE = 'Добавить устройство'
DEL_DEVICE = 'Удалить устройство'

ADMIN_ACTIONS = ( ADD_USER, DEL_USER, UPDATE_USER, ADD_TARIFF, DEL_TARIFF, UPDATE_TARIFF, ADD_DEVICE, DEL_DEVICE )

# альтернативная раскладка

# ADMIN_MARKUP = (
# 	(0, 1),
# 	(2,),
# 	(3, 4),
# 	(5,),
# 	(6, 7)
# )

ADMIN_MARKUP = (
	(0, 1, 2),
	(3, 4, 5),
	(6, 7)
)

GET_TARIFFS = 'Просмотреть тарифы'
UPDATE_MEASUREMENTS = 'Подать показания'
GET_BILL = 'Получить квитанцию'
CHECK_DEBT = 'Проверить задолженности'
EDIT_DEVICES = 'Изменить устройства'

USER_ACTIONS = ( GET_TARIFFS, UPDATE_MEASUREMENTS, GET_BILL, CHECK_DEBT, EDIT_DEVICES )

USER_MARKUP = (
	(0, 1),
	(2, 3),
	(4,)
)