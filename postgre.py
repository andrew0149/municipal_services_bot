# Работа с базой данных PostgreSQL

import psycopg2
from datetime import datetime
from config import DB_NAME, DB_USER, DB_PASS, DB_HOST, DB_PORT

connection = psycopg2.connect(
	dbname = DB_NAME, 
	user = DB_USER,
	password = DB_PASS, 
	host = DB_HOST,
	port = DB_PORT)

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
	cursor.execute("Select * from show_users")
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

def add_discount(discount, discount_name):
	cursor.execute("Call add_discount(%s, %s)", ([discount, discount_name]))
	connection.commit()

def delete_discount(discount_type_id):
	cursor.execute("Call delete_discount_type(%s)", ([discount_type_id]))
	connection.commit()

def update_discount(discount_type_id, discount, discount_name):
	cursor.execute("Call update_discount_type(%s, %s, %s)", ([discount_type_id, discount, discount_name]))
	connection.commit()

def add_tariff(tariff_name, tariff_cost):
	cursor.execute("Call add_tariff (%s, %s)", ([tariff_name, tariff_cost]))
	connection.commit()

def delete_tariff(tariff_id):
    cursor.execute("Call delete_tariff (%s)", ([tariff_id]))
    connection.commit()

def update_tariff(tariff_id, tariff_cost, tariff_name):
	cursor.execute("Call update_tariff(%s, %s, %s)", ([tariff_id, tariff_cost, tariff_name]))
	connection.commit()

def add_device(user_id, device_id):
	cursor.execute("Call add_device(%s, %s)", ([user_id, device_id]))
	connection.commit()

def delete_device(device_id):
    cursor.execute("Call delete_device (%s)", ([device_id]))
    connection.commit()

def get_device_tariffs(device_id):
	cursor.execute("Select * from get_device_tariffs(%s)", ([device_id]))
	return cursor.fetchall()

def add_device_tariff(device_id, tariff_id):
	cursor.execute("Call add_tariff_to_device(%s, %s)", ([device_id, tariff_id]))
	connection.commit()

def get_user_devices(user_id):
	cursor.execute("Select * FROM get_user_devices(%s::smallint)", ([user_id]))
	return tuple(row[0] for row in cursor.fetchall())

def get_devices():
	cursor.execute("Select device_id from devices")
	return tuple(row[0] for row in cursor.fetchall())

def get_device_name(device_id):
	cursor.execute("Select user_device_name from devices where device_id = %s", ([device_id]))
	user_device_name = cursor.fetchall()[0][0]
	return (f'Устройство {device_id}' 
		if user_device_name is None 
		else user_device_name)

def get_tariffs():
	cursor.execute("Select * from show_available_tariffs")
	return cursor.fetchall()

def get_last_measurement(device_id, tariff_id):
	cursor.execute("Select * from get_last_measurement(%s, %s)", ([device_id, tariff_id]))
	return cursor.fetchall()[0]

def send_measurement(device_id, tariff_id, measurement):
    cursor.execute("Call send_measurements(%s, %s, %s)", ([device_id, tariff_id, measurement]))
    connection.commit()

def get_user_last_bill_date(user_id):
	cursor.execute("select get_user_last_bill_date(%s)", ([user_id]))
	return cursor.fetchall()[0][0]

def create_bill(user_id):
	cursor.execute("Call create_bill(%s)", ([user_id]))
	connection.commit()

def get_user_unpaid_bills(user_id):
	cursor.execute("Select * from show_unpaid_bills where user_id = %s order by creation_date", ([user_id]))
	return tuple((creation_date.isoformat(' '), total)
		for _, creation_date, total
		in cursor.fetchall())

def get_user_balance(user_id):
	cursor.execute("Select balance from users where user_id = %s", ([user_id]))
	return cursor.fetchall()[0][0]

def pay_bill(user_id, creation_date):
	cursor.execute("Call pay_bill (%s, %s)", ([user_id, creation_date]))
	connection.commit()

def update_device_name(device_id, device_name):
	cursor.execute("Call update_device_name(%s, %s)", ([device_id, device_name]))
	connection.commit()

def get_user_discount(user_id):
	cursor.execute("Select dt.discount, dt.discount_name from users inner join discount_types dt on dt.discount_type_id = users.discount_type_id where user_id = %s", ([user_id]))
	return cursor.fetchall()[0]