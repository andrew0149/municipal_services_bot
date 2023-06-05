# файл со всей логикой и взаимодействиями с telegram api

from telebot.async_telebot import AsyncTeleBot
from telebot import types
from config import API_TOKEN, PHONE_NUMBER_FORMAT, INTEGER_FORMAT, FLOAT_FORMAT, NAME_FORMAT
import re
import asyncio
import random
import postgre as Postgre
import actions as Action


def get_users_page_keyboard(callback, page_n):
	users_list = Postgre.get_users()
	keyboard = types.InlineKeyboardMarkup()

	for user in users_list[page_n * 10:min((page_n + 1) * 10, len(users_list))]:
		user_id, user_phone, _, _, _ = user
		keyboard.add(
			types.InlineKeyboardButton(
				text = f'{user_id}) {user_phone}',
				callback_data = f'{callback},{user_id}'),
			row_width = 1)
	
	navigation_buttons = []
	
	if page_n != 0:
		navigation_buttons.append(
			types.InlineKeyboardButton(
				text = '⬅',
				callback_data = f'get_users_page,{page_n - 1},{callback}'))
	if (page_n + 1) * 10 < len(users_list):
		navigation_buttons.append(
			types.InlineKeyboardButton(
				text = '➡',
				callback_data = f'get_users_page,{page_n + 1},{callback}'))
	
	if len(navigation_buttons) != 0:
		keyboard.add(*navigation_buttons, row_width = 2)
	
	keyboard.add(
		types.InlineKeyboardButton(
			text = '❌ Отменить действие',
			callback_data = 'cancel'))

	return keyboard

async def remove_inline_reply_markup(call):
	await bot.edit_message_reply_markup(
		call.message.chat.id,
		call.message.message_id,
		reply_markup = None)

# Инициализация бота
bot = AsyncTeleBot(API_TOKEN)

# Создание клавиатуры для отмены действий
cancel_keyboard = types.InlineKeyboardMarkup()
cancel_keyboard.add(
	types.InlineKeyboardButton(
		text = '❌ Отменить действие',
		callback_data = 'cancel'))

# Обработка команд /start и /help
@bot.message_handler(commands=['start', 'help'])
async def send_welcome(message):
	if message.text in ('/start', '/help'):
		await bot.send_message(message.chat.id,
			text = 'Я бот ЖК "Столичный". С помощью меня ты можешь:\n' +
					' • Ознакомиться с тарифами на коммунальные услуги\n' +
					' • Подать показания приборов учёта\n' +
					' • Получить квитанцию на оплату коммунальных услуг\n' +
					' • Проверить наличие задолженности')

	markup = types.ReplyKeyboardMarkup()

	user_id = Postgre.get_user_id_for_chat(message.chat.id)

	# Если user_id не вернулся, заставляем пользователя авторизоваться 
	if user_id is None:
		phone_send_button = types.KeyboardButton(text='Отправить номер телефона', request_contact=True)
		markup.add(phone_send_button)
		await bot.send_message(message.chat.id,
			text = ('Для работы со мной тебе надо авторизоваться.\n' +
				'Для этого мне понадобится твой номер телефона.'),
			reply_markup=markup)
		return
	
	# админу крепим админские кнопки
	if Postgre.is_admin(user_id):
		for row in Action.ADMIN_MARKUP:
			markup.add(
				*map(
					lambda index: Action.ADMIN_ACTIONS[index], 
					row), 
				row_width=len(row))
	# а пользователю - пользовательские
	else:
		for row in Action.USER_MARKUP:
			markup.add(
				*map(
					lambda index: Action.USER_ACTIONS[index], 
					row), 
				row_width=len(row))
	
	# если пользователь вызывал не справку, здороваемся
	if message.text != '/help':
		await bot.send_message(message.chat.id,
			text = f'Привет, {message.chat.first_name}!',
			reply_markup = markup)

# деавторизация по команде /logout
@bot.message_handler(commands=['logout'])
async def deauthorize_user(message):
	Postgre.unlink_chat_from_user(message.chat.id)
	await bot.send_message(
		message.chat.id, 
		text=f'Вы были деавторизованы!',
		reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(commands=['reset'])
async def restart_session(message):
	Postgre.set_chat_state(message.chat.id, '')
	await bot.send_message(
		message.chat.id,
		text = 'Перезапуск сессии...')
	await send_welcome(message)

# обработка контактов, которая должна происходить только при и для авторизации
@bot.message_handler(content_types=['contact'])
async def authorize_user(message):
	if message.from_user.id == message.contact.user_id:
		phone_numbers_list = tuple(phone_number 
			for _, phone_number, _, _, _ 
			in Postgre.get_users())
		parsed_phone_number = (('' 
				if message.contact.phone_number.startswith('+') 
				else '+') 
			+ message.contact.phone_number)
		if parsed_phone_number not in phone_numbers_list:
			print(f'{message.contact.phone_number} not in DB!')
			await bot.send_message(
				message.chat.id,
				text = 'Вашего номера нет в базе... 😭',
				reply_markup = types.ReplyKeyboardRemove())
			return
		Postgre.link_chat_to_user(message.chat.id, parsed_phone_number)
		print(f'Linked {parsed_phone_number}!')
		await bot.send_message(
			message.chat.id,
			text=f'Авторизация прошла успешно! Ваш аккаунт привязан к номеру {parsed_phone_number}.',
			reply_markup=types.ReplyKeyboardRemove())
		await send_welcome(message)
	else:
		markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
		phone_send_button = types.KeyboardButton(text='Отправить номер телефона', request_contact=True)
		markup.add(phone_send_button)
		await bot.send_message(
			message.chat.id,
			text='Это не ваш контакт! Используйте свой контакт для авторизации.',
			reply_markup=markup)

# Обработка кнопок и ввода текста
@bot.message_handler(content_types=['text'])
async def process_message(message):
	user_id = Postgre.get_user_id_for_chat(message.chat.id)
	
	if user_id is None:
		await send_welcome(message)
		return

	state = Postgre.get_chat_state(message.chat.id)

	phone_number_regexp = re.compile(PHONE_NUMBER_FORMAT)
	integer_regexp = re.compile(INTEGER_FORMAT)
	float_regexp = re.compile(FLOAT_FORMAT)
	name_regexp = re.compile(NAME_FORMAT)


	if state is not None and state != '':
		# Обработка состояний
		if state.startswith('ADD_USER'):
			if state.startswith('ADD_USER_PHONE'):
				if phone_number_regexp.fullmatch(message.text):
					Postgre.set_chat_state(message.chat.id, 'ADD_USER_IS_ADMIN,' + message.text)
					await bot.send_message(
						message.chat.id, 
						text = 'Должен ли пользователь быть администратором? [да/нет]',
						reply_markup = cancel_keyboard)
				else:
					await bot.send_message(message.chat.id, text='Неверный формат номера...')
			if state.startswith('ADD_USER_IS_ADMIN'):
				parsed_phone = state.split(',')[1]

				if message.text.lower() in ('да', 'yes', 'д', 'y'):
					new_user_is_admin = 'true'
				elif message.text.lower() in ('нет', 'no', 'н', 'n'):
					new_user_is_admin = 'false'				
				else:
					await bot.send_message(message.chat.id, text='Неверный ввод...')
					return

				Postgre.set_chat_state(message.chat.id, ','.join(('ADD_USER_DISCOUNT', parsed_phone, new_user_is_admin)))
				discounts_list = Postgre.get_discounts()
				discounts_list_str = '\n'.join((f'{discount_id}) {discount_name}' for discount_id, discount_name in discounts_list))
				await bot.send_message(
					message.chat.id, 
					text='Введите номер тарифа для нового пользователя:\n' + discounts_list_str,
					reply_markup = cancel_keyboard)
			if state.startswith('ADD_USER_DISCOUNT'):
				_, parsed_phone, parsed_new_user_is_admin = state.split(',')
				if message.text in (str(discount_id) for discount_id, _ in Postgre.get_discounts()):
					Postgre.add_user(parsed_phone, parsed_new_user_is_admin, message.text)
					await bot.send_message(
						message.chat.id,
						text = f'Добавлен пользователь с номером телефона {parsed_phone}, ' +
							f'тарифом {int(message.text)}, ' +
							('не' if parsed_new_user_is_admin == 'false' else '') + ' являющийся администратором.')
					Postgre.set_chat_state(message.chat.id, '')
				else:
					await bot.send_message(message.chat.id, text='Неверный номер тарифа...')
		if state.startswith('DEL_USER'):
			await bot.send_message(
				message.chat.id,
				text = 'Завершите или отмените удаление перед выполнением других действий')
		if state.startswith('UPDATE_USER'):
			if state.startswith('UPDATE_USER_USER_SELECT'):
				await bot.send_message(
					message.chat.id,
					text = 'Завершите изменение тарифа пользователя или отмените операцию для выполнения других действий')
			if state.startswith('UPDATE_USER_TARIFF'):
				if message.text in (str(discount_id) for discount_id, _ in Postgre.get_discounts()):
					user_id = state.split(',')[1]
					Postgre.update_user_tariff(user_id, message.text)
					Postgre.set_chat_state(message.chat.id, '')
					await bot.send_message(
						message.chat.id,
						text = f'Тариф пользователя {user_id} изменён на {message.text}')
				else:
					await bot.send_message(message.chat.id, text = 'Неверный номер тарифа...')

		if state.startswith('ADD_TARIFF'):
			if state.startswith('ADD_TARIFF_NAME'):
				tariff_name = message.text
				if name_regexp.fullmatch(tariff_name):
					Postgre.set_chat_state(message.chat.id, f'ADD_TARIFF_COST,{tariff_name}')
					await bot.send_message(
						message.chat.id,
						text = 'Введите стоимость тарифа',
						reply_markup = cancel_keyboard)
				else:
					await bot.send_message(
						message.chat.id, 
						text = 'Неверный формат имени устройства: '\
						'используйте только буквы, пробелы, обычные скобки и дефисы')
			if state.startswith('ADD_TARIFF_COST'):
				tariff_cost = message.text.replace(',', '.')
				tariff_name = state.split(',')[1]
				if float_regexp.fullmatch(tariff_cost) and float(tariff_cost) >= 0.01:
					Postgre.set_chat_state(message.chat.id, '')
					Postgre.add_tariff(tariff_name, tariff_cost)
					await bot.send_message(
						message.chat.id,
						text = f'Тариф "{tariff_name}" стоимостью {tariff_cost} руб./у.е добавлен')
				else:
					await bot.send_message(message.chat.id, text = 'Неверная стоимость тарифа...')
		if state.startswith('DEL_TARIFF'):
			if state.startswith('DEL_TARIFF_ID'):
				if message.text in (str(tariff_id) for tariff_id, _, _, _ in Postgre.get_tariffs()):
					Postgre.set_chat_state(message.chat.id, '')
					Postgre.delete_tariff(message.text)
					await bot.send_message(
						message.chat.id,
						text = f'Тариф с ID {message.text} был удалён')
				else:
					await bot.send_message(message.chat.id, text = 'Неверный ID тарифа...')
		if state.startswith('UPDATE_TARIFF'):
			if state.startswith('UPDATE_TARIFF_TARIFF_ID'):
				if message.text in (str(tariff_id) for tariff_id, _, _, _ in Postgre.get_tariffs()):
					Postgre.set_chat_state(message.chat.id, f'UPDATE_TARIFF_TARIFF_NAME,{message.text}')
					await bot.send_message(
						message.chat.id,
						text = 'Введите новое имя тарифа или -1, если не хотите его менять',
						reply_markup = cancel_keyboard)
				else:
					await bot.send_message(message.chat.id, text = 'Неверный ID тарифа...')
			if state.startswith('UPDATE_TARIFF_TARIFF_NAME'):
				if name_regexp.fullmatch(message.text):
					tariff_id = state.split(',')[1]
					Postgre.set_chat_state(message.chat.id, f'UPDATE_TARIFF_TARIFF_COST,{tariff_id},{message.text}')
					await bot.send_message(
						message.chat.id, 
						text = 'Введите новую стоимость тарифа',
						reply_markup = cancel_keyboard)
				else:
					await bot.send_message(
						message.chat.id, 
						text = 'Неверный формат имени устройства: '\
						'используйте только буквы, пробелы, обычные скобки и дефисы')
			if state.startswith('UPDATE_TARIFF_TARIFF_COST'):
				tariff_cost = message.text.replace(',', '.')
				if float_regexp.fullmatch(message.text) and float(tariff_cost) >= 0.01:
					_, tariff_id, tariff_name = state.split(',')
					Postgre.set_chat_state(message.chat.id, '')
					Postgre.update_tariff(tariff_id, tariff_cost, tariff_name)
					await bot.send_message(
						message.chat.id,
						text = f'Имя и стоимость тарифа с ID {tariff_id} обновлены')

		if state.startswith('ADD_DEVICE'):
			if state.startswith('ADD_DEVICE_ID'):
				if integer_regexp.fullmatch(message.text) and int(message.text) > 10000:
					device_id = int(message.text)
					if device_id in Postgre.get_devices():
						await bot.send_message(message.chat.id, text = 'Данный ID устройства уже существует!')
					else:
						await bot.send_message(
							message.chat.id,
							text = 'Выберите пользователя, владеющего устройством',
							reply_markup = get_users_page_keyboard(f'add_device_to_user,{device_id}', 0))
						Postgre.set_chat_state(message.chat.id, 'ADD_DEVICE_TO_USER')
				else:
					await bot.send_message(
						message.chat.id,
						text = 'Неверный формат серийного номера...')
			if state.startswith('ADD_DEVICE_TO_USER'):
				await bot.send_message(
					message.chat.id,
					text = 'Завершите или отмените добавление устройства перед выполнением других действий')
			if state.startswith('ADD_DEVICE_SET_TARIFF'):
				device_id = state.split(',')[1]
				if message.text in (str(tariff_id) 
					for tariff_id, _, _, _ 
					in Postgre.get_tariffs()):
					Postgre.add_device_tariff(device_id, message.text)
					await bot.send_message(
						message.chat.id,
						text = f'Добавлено устройство с серийным номером {device_id} и тарифом {message.text}')
					Postgre.set_chat_state(message.chat.id, '')
		if state.startswith('DEL_DEVICE'):
			if state.startswith('DEL_DEVICE_USER_ID'):
				await bot.send_message(
					message.chat.id, 
					text = 'Завершите удаление устройства или отмените операцию для выполнения других действий')
			if state.startswith('DEL_DEVICE_DEVICE_ID'):
				user_id = state.split(',')[1]
				if message.text in (str(device_id) for device_id in Postgre.get_user_devices(user_id)):
					Postgre.delete_device(message.text)
					Postgre.set_chat_state(message.chat.id, '')
					await bot.send_message(
						message.chat.id,
						text = f'Устройство с ID {message.text} удалено!')
				else:
					await bot.send_message(message.chat.id, text = 'Неверный ID устройства...')
		if state.startswith('ADD_DEVICE_TARIFF'):
			if state.startswith('ADD_DEVICE_TARIFF_USER_ID'):
				await bot.send_message(
					message.chat.id,
					text = 'Завершите добавление тарифа или отмените операцию для выполнения других действий')
			if state.startswith('ADD_DEVICE_TARIFF_DEVICE_ID'):
				user_id = state.split(',')[1]
				if message.text in (str(device_id) for device_id in Postgre.get_user_devices(user_id)):
					Postgre.set_chat_state(message.chat.id, f'ADD_DEVICE_TARIFF_SET_TARIFF,{message.text}')
					tariffs_list_str = '\n'.join(
						f'{tariff_id}) {tariff_name} - {tariff_cost} руб./у.е.'
						for tariff_id, tariff_name, _, tariff_cost
						in Postgre.get_tariffs())
					await bot.send_message(
						message.chat.id,
						text = 'Введите номер тарифа для добавления устройству:\n' + tariffs_list_str,
						reply_markup = cancel_keyboard)
				else:
					await bot.send_message(message.chat.id, text = 'Неверный ID устройства...')
			if state.startswith('ADD_DEVICE_TARIFF_SET_TARIFF'):
				device_id = state.split(',')[1]
				if message.text in (str(tariff_id)
					for tariff_id, _, _, _
					in Postgre.get_tariffs()):
					if message.text in (str(tariff_id)
						for tariff_id, _
						in Postgre.get_device_tariffs(device_id)):
						await bot.send_message(
							message.chat.id,
							text = 'Этот тариф уже добавлен этому устройству: ' \
							'введите другой номер тарифа или отмените добавление тарифа')
					else:
						Postgre.add_device_tariff(device_id, message.text)
						Postgre.set_chat_state(message.chat.id, '')
						await bot.send_message(
							message.chat.id,
							text = f'Устройству с ID {device_id} был добавлен тариф {message.text}')
				else:
					await bot.send_message(message.chat.id, text = 'Неверный номер тарифа')

		if state.startswith('UPDATE_MEASUREMENTS'):
			if state.startswith('UPDATE_MEASUREMENTS_DEVICE_ID'):
				if message.text in (str(device_id) 
					for device_id 
					in Postgre.get_user_devices(user_id)):
					
					Postgre.set_chat_state(message.chat.id, f'UPDATE_MEASUREMENTS_TARIFF_ID,{message.text}')
					device_tariffs_list = '\n'.join(
						f'{tariff_id}) {tariff_name}' 
							for tariff_id, tariff_name 
							in Postgre.get_device_tariffs(message.text))
					await bot.send_message(
						message.chat.id,
						text = 'Введите номер тарифа устройства для которого хотите подать показания:\n' + device_tariffs_list,
						reply_markup = cancel_keyboard)
				else:
					await bot.send_message(message.chat.id, text = 'Неверный ID устройства...')
			if state.startswith('UPDATE_MEASUREMENTS_TARIFF_ID'):
				device_id = state.split(',')[1]
				if message.text in (str(tariff_id)
					for tariff_id, _ 
					in Postgre.get_device_tariffs(device_id)):
					
					Postgre.set_chat_state(message.chat.id, f'UPDATE_MEASUREMENTS_MEASUREMENT,{device_id},{message.text}')
					await bot.send_message(
						message.chat.id,
						text = f'Введите текущие показания для устройства "{Postgre.get_device_name(device_id)}" и тарифа {message.text}',
						reply_markup = cancel_keyboard)
				else:
					await bot.send_message('Неверный номер тарифа...')
			if state.startswith('UPDATE_MEASUREMENTS_MEASUREMENT'):
				_, device_id, tariff_id = state.split(',')
				measurement = message.text.replace(',', '.')

				if float_regexp.fullmatch(measurement):
					if float(measurement) >= Postgre.get_last_measurement(device_id, tariff_id)[0]:
						Postgre.set_chat_state(message.chat.id, '')
						Postgre.send_measurement(device_id, tariff_id, measurement)
						await bot.send_message(
							message.chat.id,
							text = f'Поданы показания {measurement} у.е. '\
								f'для устройства "{Postgre.get_device_name(device_id)}"'\
								f' и тарифа {tariff_id}')
					else:
						await bot.send_message(message.chat.id, text = 'Текущие показания не могут быть меньше предыдущих')
				else:
					await bot.send_message(message.chat.id, text = 'Вы ввели не число...')

	else:
		if (Postgre.is_admin(user_id) 
			and message.text in Action.ADMIN_ACTIONS):
			
			print(f'ADMIN ACTION --- chat_id={message.chat.id} action="{message.text}"')
			match message.text:
				case Action.ADD_USER:
					await bot.send_message(
						message.chat.id,
						text = 'Введите номер телефона для которого хотите добавить аккаунт в формате "+79123456789"',
						reply_markup = cancel_keyboard)
					Postgre.set_chat_state(message.chat.id, 'ADD_USER_PHONE')
				case Acion.DEL_USER:
					Postgre.set_chat_state(message.chat.id, 'DEL_USER')
					await bot.send_message(
						message.chat.id,
						text = 'Выберите пользователя, которого хотите удалить:',
						reply_markup = get_users_page_keyboard('delete_user', 0))
				case Action.UPDATE_USER:
					Postgre.set_chat_state(message.chat.id, 'UPDATE_USER_USER_SELECT')
					await bot.send_message(
						message.chat.id,
						text = 'Выберите пользователя, тариф которого хотите изменить',
						reply_markup = get_users_page_keyboard('update_user_tariff', 0))

				case Action.ADD_TARIFF:
					Postgre.set_chat_state(message.chat.id, 'ADD_TARIFF_NAME')
					await bot.send_message(
						message.chat.id,
						text = 'Введите название нового тарифа',
						reply_markup = cancel_keyboard)
				case Action.DEL_TARIFF:
					Postgre.set_chat_state(message.chat.id, 'DEL_TARIFF_ID')
					tariffs_list_str = '\n'.join(
						f'{tariff_id}) {tariff_name} - {tariff_cost} руб./у.е.'
						for tariff_id, tariff_name, _, tariff_cost
						in Postgre.get_tariffs())
					await bot.send_message(
						message.chat.id,
						text = 'Введите ID тарифа, который хотите удалить:\n' + tariffs_list_str,
						reply_markup = cancel_keyboard)
				case Action.UPDATE_TARIFF:
					Postgre.set_chat_state(message.chat.id, 'UPDATE_TARIFF_TARIFF_ID')
					tariffs_list_str = '\n'.join(
						f'{tariff_id}) {tariff_name} - {tariff_cost} руб./у.е.'
						for tariff_id, tariff_name, _, tariff_cost
						in Postgre.get_tariffs())
					await bot.send_message(
						message.chat.id,
						text = 'Введите ID тарифа, который хотите изменить:\n' + tariffs_list_str,
						reply_markup = cancel_keyboard)

				case Action.ADD_DEVICE:
					await bot.send_message(
						message.chat.id,
						text = 'Введите серийный номер (ID) добавляемого устройства (5-7 цифр):',
						reply_markup = cancel_keyboard)
					Postgre.set_chat_state(message.chat.id, 'ADD_DEVICE_ID')
				case Action.DEL_DEVICE:
					await bot.send_message(
						message.chat.id,
						text = 'Выберите пользователя, устройство которого хотите удалить',
						reply_markup = get_users_page_keyboard('delete_device', 0))
					Postgre.set_chat_state(message.chat.id, 'DEL_DEVICE_USER_ID')
				case Action.ADD_DEVICE_TARIFF:
					Postgre.set_chat_state(message.chat.id, 'ADD_DEVICE_TARIFF_USER_ID')
					await bot.send_message(
						message.chat.id,
						text = 'Выберите пользователя, устройству которого вы хотите добавить тариф',
						reply_markup = get_users_page_keyboard('add_device_tariff', 0))

 		
		elif message.text in Action.USER_ACTIONS:
			
			print(f'USER ACTION --- chat_id={message.chat.id} action="{message.text}"')
			match message.text:
				case Action.GET_TARIFFS:
					tariffs_list_str = '\n'.join(
						f'{tariff_id}) {tariff_name} - {tariff_cost} руб./у.е'
						for tariff_id, tariff_name, _, tariff_cost
						in Postgre.get_tariffs())
					await bot.send_message(
						message.chat.id, 
						text = 'На текущий момент установлены следующие тарифы:\n' + tariffs_list_str)
				case Action.UPDATE_MEASUREMENTS:
					Postgre.set_chat_state(message.chat.id, f'UPDATE_MEASUREMENTS_DEVICE_ID')
					devices_list = '\n'.join(
						f'{device_id}) {Postgre.get_device_name(device_id)}' 
							for device_id 
							in Postgre.get_user_devices(user_id))
					await bot.send_message(
						message.chat.id, 
						text = 'Введите ID устройства для которого хотите подать показания:\n' + devices_list,
						reply_markup = cancel_keyboard)
				case Action.GET_BILL:

					last_bill_date = Postgre.get_user_last_bill_date(user_id)
					devices_with_old_measurements = []
					for device_id in Postgre.get_user_devices(user_id):
						for tariff_id, tariff_name  in Postgre.get_device_tariffs(device_id):
							if Postgre.get_last_measurement(device_id, tariff_id)[1] <= last_bill_date:
								devices_with_old_measurements.append(f'{device_id}) Устройство "{Postgre.get_device_name(device_id)}" тариф "{tariff_name}"')
					if len(devices_with_old_measurements) > 0:
						await bot.send_message(
							message.chat.id,
							text = ('Для того, чтобы получить квитанцию, подайте новые показания для следующих устройств:\n' 
								+ '\n'.join(devices_with_old_measurements)))
					else:
						pass # TODO: Дописать генерацию квитка, кнопки для оплаты и работу с базой
				case Action.CHECK_DEBT:
					pass # TODO: Дописать подтягивание неоплаченных квитков и кнопки как выше
				case Action.EDIT_DEVICES:
					pass # TODO: Дописать редактирование имени устройства
		else:
			await send_error(message)

# Обработка кнопки отмены
@bot.callback_query_handler(func=lambda call: call.data == 'cancel')
async def cancel_operation(call):
	Postgre.set_chat_state(call.message.chat.id, '')
	await remove_inline_reply_markup(call)
	await bot.send_message(
		call.message.chat.id,
		text = 'Операция отменена')

# Обработка перелистывания страниц с пользователями
@bot.callback_query_handler(func=lambda call: call.data.split(',')[0] == 'get_users_page')
async def get_new_users_page(call):
	page_n = int(call.data.split(',')[1])
	callback = ','.join(call.data.split(',')[2:])
	await bot.edit_message_reply_markup(
		call.message.chat.id,
		call.message.message_id,
		reply_markup = get_users_page_keyboard(callback, page_n))

# Запрос подтверждения на удаление пользователя
@bot.callback_query_handler(func=lambda call: call.data.split(',')[0] == 'delete_user')
async def delete_user(call):
	user_id = call.data.split(',')[1]
	await remove_inline_reply_markup(call)
	choice_keyboard = types.InlineKeyboardMarkup()
	choice_keyboard.add(
		types.InlineKeyboardButton(
			text = '✔ Да',
			callback_data = f'delete_user_confirmed,{user_id}'),
		types.InlineKeyboardButton(
			text = '❌ Нет',
			callback_data = 'cancel'),
		row_width = 2)
	await bot.send_message(
		call.message.chat.id,
		text = 'Вы уверены, что хотите удалить пользователя?',
		reply_markup = choice_keyboard)

# Удаление пользователя подтверждено - УДАЛЯЕМ!
@bot.callback_query_handler(func=lambda call: call.data.split(',')[0] == 'delete_user_confirmed')
async def delete_user_confirmed(call):
	await remove_inline_reply_markup(call)
	Postgre.set_chat_state(call.message.chat.id, '')
	user_id = int(call.data.split(',')[1])
	if Postgre.is_admin(user_id) and user_id != Postgre.get_user_id_for_chat(call.message.chat.id):
		await bot.send_message(
			call.message.chat.id,
			text = f'Вы не можете удалить аккаунт другого администратора через бота!')
	else:
		Postgre.delete_user(user_id)
		await bot.send_message(
			call.message.chat.id,
			text = f'Пользователь с ID {user_id} удалён')

# Изменение тарифа
@bot.callback_query_handler(func=lambda call: call.data.split(',')[0] == 'update_user_tariff')
async def update_user_tariff(call):
	await remove_inline_reply_markup(call)

	user_id = call.data.split(',')[1]
	Postgre.set_chat_state(call.message.chat.id, f'UPDATE_USER_TARIFF,{user_id}')

	discounts_list = Postgre.get_discounts()
	discounts_list_str = '\n'.join((f'{discount_id}) {discount_name}' for discount_id, discount_name in discounts_list))

	await bot.send_message(
		call.message.chat.id, 
		text='Введите номер нового тарифа для выбранного пользователя:\n' + discounts_list_str,
		reply_markup = cancel_keyboard)

# Привязка устройства к пользователю в процессе добавления
@bot.callback_query_handler(func=lambda call: call.data.split(',')[0] == 'add_device_to_user')
async def link_device_to_user(call):
	await remove_inline_reply_markup(call)

	device_id, user_id = call.data.split(',')[1:]

	Postgre.add_device(user_id, device_id)
	Postgre.set_chat_state(call.message.chat.id, f'ADD_DEVICE_SET_TARIFF,{device_id}')

	tariffs_list_str = '\n'.join(
		f'{tariff_id}) {tariff_name} - {tariff_cost} руб./у.е.'
		for tariff_id, tariff_name, _, tariff_cost
		in Postgre.get_tariffs())

	await bot.send_message(
		call.message.chat.id,
		text = 'Введите номер тарифа для устройства:\n' + tariffs_list_str,
		reply_markup = cancel_keyboard)

# Удаление устройства пользователя
@bot.callback_query_handler(func=lambda call: call.data.split(',')[0] == 'delete_device')
async def delete_device(call):
	await remove_inline_reply_markup(call)

	user_id = call.data.split(',')[1]

	Postgre.set_chat_state(call.message.chat.id, f'DEL_DEVICE_DEVICE_ID,{user_id}')

	devices_list = '\n'.join(map(str, Postgre.get_user_devices(user_id)))
	await bot.send_message(
		call.message.chat.id,
		text = 'Введите ID устройства, которое хотите удалить:\n' + devices_list,
		reply_markup = cancel_keyboard)

# Добавление тарифа устройству
@bot.callback_query_handler(func=lambda call: call.data.split(',')[0] == 'add_device_tariff')
async def add_device_tariff(call):
	await remove_inline_reply_markup(call)

	user_id = call.data.split(',')[1]

	Postgre.set_chat_state(call.message.chat.id, f'ADD_DEVICE_TARIFF_DEVICE_ID,{user_id}')

	devices_list = '\n'.join(map(str, Postgre.get_user_devices(user_id)))
	await bot.send_message(
		call.message.chat.id,
		text = 'Введите ID устройства, которому хотите добавить тариф:\n' + devices_list,
		reply_markup = cancel_keyboard)

@bot.message_handler(func=lambda message: True)
async def send_error(message):
	await bot.send_message(message.chat.id, text='Сообщение не распознано...')

if __name__=='__main__':
	asyncio.run(bot.polling())