# на текущий момент используется в качестве плейсхолдера

chats = {
	470922424: [0, ''],
	458948714: [0, '']
}

discounts = (
	(0, 'Обычный, без скидки'),
	(1, 'Пенсионный, 10% скидка')
)

def get_user_id_for_chat(chat_id):
	return (chats[chat_id][0] 
		if chat_id in chats.keys() 
		else None)

def link_chat_to_user(chat_id, phone_number):
	chats[chat_id] = [1, '']

def unlink_chat_from_user(chat_id):
	chats.pop(chat_id)

def is_admin(user_id):
	return user_id == 0

def get_chat_state(chat_id):
	return chats[chat_id][1]

def set_chat_state(chat_id, state):
	chats[chat_id][1] = state

def get_discounts_list():
	return discounts

def add_user(phone, user_is_admin, discount_id):
	print(f'USER ADD --- {phone=}, is_admin={user_is_admin}, {discount_id=}')
