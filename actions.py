# файл, содержащий все действия, доступные пользователю и администратору

ADD_USER = 'Добавить пользователя'
DEL_USER = 'Удалить пользователя'
UPDATE_USER = 'Обновить льготы пользователя'
ADD_DISCOUNT = 'Добавить льготу'
DEL_DISCOUNT = 'Удалить льготу'
UPDATE_DISCOUNT = 'Изменить льготу'
ADD_TARIFF = 'Добавить тариф'
DEL_TARIFF = 'Удалить тариф'
UPDATE_TARIFF = 'Обновить стоимость тарифа'
ADD_DEVICE = 'Добавить устройство'
DEL_DEVICE = 'Удалить устройство'
ADD_DEVICE_TARIFF = 'Добавить тариф устройству'

ADMIN_ACTIONS = ( ADD_USER, DEL_USER, UPDATE_USER, 
	ADD_DISCOUNT, DEL_DISCOUNT, UPDATE_DISCOUNT,
	ADD_TARIFF, DEL_TARIFF, UPDATE_TARIFF, 
	ADD_DEVICE, DEL_DEVICE, ADD_DEVICE_TARIFF
)

ADMIN_MARKUP = (
	(0, 1, 2),
	(3, 4, 5),
	(6, 7, 8),
	(9, 10, 11),
)

GET_DISCOUNT_TYPE = 'Просмотреть мою льготу'
GET_TARIFFS = 'Просмотреть тарифы'
UPDATE_MEASUREMENTS = 'Подать показания'
GET_BILL = 'Получить квитанцию'
CHECK_DEBT = 'Проверить задолженности'
EDIT_DEVICES = 'Изменить устройства'

USER_ACTIONS = ( 
	GET_DISCOUNT_TYPE, GET_TARIFFS, 
	UPDATE_MEASUREMENTS, GET_BILL, CHECK_DEBT, 
	EDIT_DEVICES 
)

USER_MARKUP = (
	(0, 1),
	(2, 3, 4),
	(5,),
)