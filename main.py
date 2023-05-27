# файл со всей логикой и взаимодействиями с telegram api

from telebot.async_telebot import AsyncTeleBot
from telebot import types
from config import API_TOKEN, PHONE_NUMBER_FORMAT
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

	markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

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

# обработка контактов, которая должна происходить только при и для авторизации
@bot.message_handler(content_types=['contact'])
async def authorize_user(message):
	if message.from_user.id == message.contact.user_id:
		Postgre.link_chat_to_user(message.chat.id, message.contact.phone_number)
		print(f'Linked {message.contact.phone_number}!')
		await bot.send_message(
			message.chat.id,
			text=f'Авторизация прошла успешно! Ваш аккаунт привязан к номеру {message.contact.phone_number}.',
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

# Обработка кнопок
@bot.message_handler(content_types=['text'])
async def process_message(message):
	user_id = Postgre.get_user_id_for_chat(message.chat.id)
	
	if user_id is None:
		await send_welcome(message)
		return

	if Postgre.is_admin(user_id):
		phone_number_regexp = re.compile(PHONE_NUMBER_FORMAT)

		state = Postgre.get_chat_state(message.chat.id)

		# Создание клавиатуры для отмены действий
		cancel_keyboard = types.InlineKeyboardMarkup()
		cancel_keyboard.add(
			types.InlineKeyboardButton(
				text = '❌ Отменить действие',
				callback_data = 'cancel'))

		if state is not None and state != '':

			# Обработка состояний
			if state.startswith('ADD_USER'):
				if state.startswith('ADD_USER_PHONE'):
					if phone_number_regexp.match(message.text):
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
					discounts_list = Postgre.get_discounts_list()
					discounts_list_str = '\n'.join((f'{discount_id}) {discount_name}' for discount_id, discount_name in discounts_list))
					await bot.send_message(
						message.chat.id, 
						text='Введите номер тарифа для нового пользователя:\n' + discounts_list_str,
						reply_markup = cancel_keyboard)
				if state.startswith('ADD_USER_DISCOUNT'):
					_, parsed_phone, parsed_new_user_is_admin = state.split(',')
					if message.text in (str(discount_id) for discount_id, _ in Postgre.get_discounts_list()):
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

		# Обработка админских кнопок
		elif message.text in Action.ADMIN_ACTIONS:
			print(f'ADMIN ACTION --- chat_id={message.chat.id} action="{message.text}"')
			match message.text:
				case Action.ADD_USER:
					await bot.send_message(
						message.chat.id,
						text = 'Введите номер телефона для которого хотите добавить аккаунт в формате "+79123456789"',
						reply_markup = cancel_keyboard)
					Postgre.set_chat_state(message.chat.id, 'ADD_USER_PHONE')
				case Action.DEL_USER:
					await bot.send_message(
						message.chat.id,
						text = 'Выберите пользователя, которого хотите удалить:',
						reply_markup = get_users_page_keyboard('delete_user', 0))
					Postgre.set_chat_state(message.chat.id, 'DEL_USER')
				case Action.UPDATE_USER:
					pass
				case Action.ADD_TARIFF:
					pass
				case Action.DEL_TARIFF:
					pass
				case Action.UPDATE_TARIFF:
					pass
				case Action.ADD_DEVICE:
					pass
				case Action.DEL_DEVICE:
					pass

		else:
			await send_error(message)
 	
	else:
		# Обработка пользовательских кнопок
		if message.text in Action.USER_ACTIONS:
			print(f'USER ACTION --- chat_id={message.chat.id} action="{message.text}"')
			match message.text:
				case Action.GET_TARIFFS:
					pass
				case Action.UPDATE_MEASUREMENTS:
					pass
				case Action.GET_BILL:
					pass
				case Action.CHECK_DEBT:
					pass
				case Action.EDIT_DEVICES:
					pass
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
	callback = call.data.split(',')[2]
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
	user_id = call.data.split(',')[1]
	Postgre.delete_user(user_id)
	Postgre.set_chat_state(call.message.chat.id, '')
	await bot.send_message(
		call.message.chat.id,
		text = f'Пользователь с ID {user_id} удалён')

@bot.message_handler(func=lambda message: True)
async def send_error(message):
	await bot.send_message(message.chat.id, text='Сообщение не распознано...')

if __name__=='__main__':
	asyncio.run(bot.polling())