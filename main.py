# файл со всей логикой и взаимодействиями с telegram api

from telebot.async_telebot import AsyncTeleBot
from telebot import types
from config import API_TOKEN, PHONE_NUMBER_FORMAT
import re
import asyncio
import random
import postgre as Postgre
import actions as Action


bot = AsyncTeleBot(API_TOKEN)

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

	if user_id is None:
		phone_send_button = types.KeyboardButton(text='Отправить номер телефона', request_contact=True)
		markup.add(phone_send_button)
		await bot.send_message(message.chat.id,
			text = ('Для работы со мной тебе надо авторизоваться.\n' +
				'Для этого мне понадобится твой номер телефона.'),
			reply_markup=markup)
		return
	
	if Postgre.is_admin(user_id):
		for row in Action.ADMIN_MARKUP:
			markup.add(
				*map(
					lambda index: Action.ADMIN_ACTIONS[index], 
					row), 
				row_width=len(row))
	else:
		for row in Action.USER_MARKUP:
			markup.add(
				*map(
					lambda index: Action.USER_ACTIONS[index], 
					row), 
				row_width=len(row))
	
	if message.text != '/help':
		await bot.send_message(message.chat.id,
			text = f'Привет, {message.chat.first_name}!',
			reply_markup = markup)

@bot.message_handler(commands=['logout'])
async def deauthorize_user(message):
	Postgre.unlink_chat_from_user(message.chat.id)
	await bot.send_message(
		message.chat.id, 
		text=f'Вы были деавторизованы!',
		reply_markup=types.ReplyKeyboardRemove())

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

@bot.message_handler(content_types=['text'])
async def process_message(message):
	user_id = Postgre.get_user_id_for_chat(message.chat.id)
	
	if user_id is None:
		await send_welcome(message)
		return

	if Postgre.is_admin(user_id):
		phone_number_regexp = re.compile(PHONE_NUMBER_FORMAT)

		state = Postgre.get_chat_state(message.chat.id)

		if message.text in Action.ADMIN_ACTIONS:
			print(f'ADMIN ACTION --- chat_id={message.chat.id} action="{message.text}"')
			match message.text:
				case Action.ADD_USER:
					await bot.send_message(
						message.chat.id,
						text = 'Введите номер телефона для которого хотите добавить аккаунт в формате "+79123456789"')
					Postgre.set_chat_state(message.chat.id, 'ADD_USER_PHONE')
				case Action.DEL_USER:
					pass
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

		# Одно большое создание пользователя
		elif state.startswith('ADD_USER_PHONE'):
			if phone_number_regexp.match(message.text):
				Postgre.set_chat_state(message.chat.id, 'ADD_USER_IS_ADMIN,' + message.text)
				await bot.send_message(message.chat.id, text='Должен ли пользователь быть администратором? [да/нет]')
			else:
				Postgre.set_chat_state(message.chat.id, '')
				await bot.send_message(message.chat.id, text='Неверный формат номера...')
		elif state.startswith('ADD_USER_IS_ADMIN'):
			parsed_phone = state.split(',')[1]
			if message.text.lower() in ('да', 'yes', 'д', 'y'):
				new_user_is_admin = 'true'
			elif message.text.lower() in ('нет', 'no', 'н', 'n'):
				new_user_is_admin = 'false'				
			else:
				await bot.send_message(message.chat.id, text='Неверный ввод...')
				Postgre.set_chat_state(message.chat.id, '')
				return
			Postgre.set_chat_state(message.chat.id, ','.join(('ADD_USER_DISCOUNT', parsed_phone, new_user_is_admin)))
			discounts_list = Postgre.get_discounts_list()
			discounts_list_str = '\n'.join((f'{discount_id}) {discount_name}' for discount_id, discount_name in discounts_list))
			await bot.send_message(message.chat.id, text='Введите номер тарифа для нового пользователя:\n' + discounts_list_str)
		elif state.startswith('ADD_USER_DISCOUNT'):
			_, parsed_phone, parsed_new_user_is_admin = state.split(',')
			if message.text in (str(discount_id) for discount_id, _ in Postgre.get_discounts_list()):
				Postgre.add_user(parsed_phone, parsed_new_user_is_admin, message.text)
				await bot.send_message(
					message.chat.id,
					text = f'Добавлен пользователь с номером телефона {parsed_phone}, ' +
						f'тарифом {int(message.text)}, ' +
						('не' if parsed_new_user_is_admin == 'false' else '') + ' являющийся администратором.')
			else:
				await bot.send_message(message.chat.id, text='Неверный номер тарифа...')
			Postgre.set_chat_state(message.chat.id, '')

		else:
			await send_error(message)
 	
	else:
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


@bot.message_handler(func=lambda message: True)
async def send_error(message):
	await bot.send_message(message.chat.id, text='Сообщение не распознано...')


if __name__=='__main__':
	asyncio.run(bot.polling())