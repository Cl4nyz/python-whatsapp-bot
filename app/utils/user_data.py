import uuid
import shelve
import logging
import app.constants as constants

def get_salesman(wa_id):
    with shelve.open("users_db") as users_shelf:
        if wa_id in users_shelf:
            return users_shelf[wa_id]["vendedor"]

        user_data = {
            "id": str(uuid.uuid4()),
            "vendedor": constants.VENDAS[get_total_users() % len(constants.VENDAS)]
        }

        users_shelf[wa_id] = user_data
        logging.info(f"Novo usuário gerado para {wa_id}: {user_data}")
        return user_data["vendedor"]
    

def get_total_users():
    with shelve.open('users_db') as db:
        return len(db)
