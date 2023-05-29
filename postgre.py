# Работа с базой данных PostgreSQL

import psycopg2
from config import DB_NAME, DB_USER, DB_PASS, DB_HOST

connection = psycopg2.connect(
	dbname = DB_NAME, 
	user = DB_USER,
	password = DB_PASS, 
	host = DB_HOST)

cursor = connection.cursor()

def get_user_id_for_chat(chat_id):
	cursor.execute("Call get_user_id_by_chat_id (%s, 0)", ([chat_id]))
	user_id = cursor.fetchall()[0][0]
	return (user_id 
		if user_id != -1 
		else None)

def link_chat_to_user(chat_id, phone_number):
	cursor.execute('''Call add_session (%s, %s)''', ([chat_id, phone_number]))
	connection.commit()

def unlink_chat_from_user(chat_id):
	cursor.execute("Call delete_session (%s)", ([chat_id]))
	connection.commit()

def get_users():
	cursor.execute ("Select * from show_users")
	return cursor.fetchall()

def is_admin(user_id):
	cursor.execute("Call check_is_admin (%s, False)", ([user_id]))
	return cursor.fetchall()[0][0]

def get_chat_state(chat_id):
	cursor.execute("Call get_state (%s, '')", ([chat_id]))
	return cursor.fetchall()[0][0]

def set_chat_state(chat_id, state):
	cursor.execute("Call change_state (%s, %s)", ([chat_id, state]))
	connection.commit()

def get_discounts():
	cursor.execute("Select * from show_discounts")
	return cursor.fetchall()

def add_user(phone_number, user_is_admin, discount_type_id):
	cursor.execute("Call add_user (%s, %s, %s)", ([phone_number, discount_type_id, user_is_admin]))
	connection.commit()

def delete_user(user_id):
	cursor.execute("Call delete_user (%s)", ([user_id]))
	connection.commit()

def update_user_tariff(user_id, discount_type_id):
	cursor.execute("Call update_user_tariff(%s, %s)", ([user_id, discount_type_id]))
	connection.commit()

def add_device(user_id, device_id):
	cursor.execute("Call add_device(%s, %s)", ([user_id, device_id]))
	connection.commit()

def delete_device(device_id):
    cursor.execute("Call delete_device (%s)", ([device_id]))
    connection.commit()

def get_device_tariffs(device_id):
	cursor.execute("Select * from get_device_tariffs(%s)", ([device_id]))
	return tuple(row[0] for row in cursor.fetchall())

def add_device_tariff(device_id, tariff_id):
	cursor.execute("Call add_tariff_to_device(%s, %s)", ([device_id, tariff_id]))
	connection.commit()

def get_user_devices(user_id):
	cursor.execute("Select * FROM get_user_devices(%s::smallint)", ([user_id]))
	return tuple(row[0] for row in cursor.fetchall())

def get_tariffs():
	cursor.execute ("Select * from show_available_tariffs")
	return cursor.fetchall()

