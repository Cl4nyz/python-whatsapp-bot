import logging
from flask import current_app, jsonify
import json
import requests
from pydub import AudioSegment
import io

from app.services.openai_service import generate_response, transcribe_audio
from app.utils.user_data import get_salesman
from app.constants import *
import re


def log_http_response(response):
    logging.info(f"Status: {response.status_code}")
    logging.info(f"Content-type: {response.headers.get('content-type')}")
    logging.info(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=10
        )  # 10 seconds timeout as an example
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except (
        requests.RequestException
    ) as e:  # This will catch any general request exception
        logging.error(f"Request failed due to: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500
    else:
        # Process the response as normal
        log_http_response(response)
        return response


def process_text_for_whatsapp(text):
    # Remove brackets
    pattern = r"\【.*?\】"
    # Substitute the pattern with an empty string
    text = re.sub(pattern, "", text).strip()

    # Pattern to find double asterisks including the word(s) in between
    pattern = r"\*\*(.*?)\*\*"

    # Replacement pattern with single asterisks
    replacement = r"*\1*"

    # Substitute occurrences of the pattern with the replacement
    whatsapp_style_text = re.sub(pattern, replacement, text)

    return whatsapp_style_text


def replace_phone(wa_id, text):
    if '<<contato' in text:
        if (pattern := '<<contato_vendas>>') in text:
            # Checks if current client already has salesman attached
            substitute = get_salesman(wa_id)
        elif (pattern := '<<contato_assistencia>>') in text:
            substitute = TECNICO
        elif (pattern := '<<contato_financeiro>>') in text:
            substitute = FINANCEIRO
        text = re.sub(pattern, substitute, text)
    return text


def process_whatsapp_message(body):
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    name = body["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]

    message = body["entry"][0]["changes"][0]["value"]["messages"][0]
    match message['type']:

        case 'text':
            message_body = message["text"]["body"]
            print(f'{LIGHTBLUE}{wa_id} - {message_body}{RESET}')
            response = open_ai_response(wa_id, name, message_body)

        case 'audio':
            print(f'{LIGHTBLUE}{wa_id}{YELLOW} - Mensagem de áudio{RESET}')
            audio_id = message['audio']['id']
            message_body = process_audio_message(audio_id)

            if message_body == FALSE:
                response = 'Não consegui entender seu áudio! Tente novamente por gentileza.'

            else:
                print(f'{LIGHTBLUE}{wa_id} - {message_body}{RESET}')
                response = open_ai_response(wa_id, name, message_body)

        case _:
            print(f'{LIGHTBLUE}{wa_id} - {RED}Formato inválido de mensagem{RESET}')
            response = "Atualmente só entendo mensagens de texto e áudio! Poderia tentar novamente?"

    data = get_text_message_input(wa_id, response)
    print(f'{GREEN}Homero → {LIGHTBLUE}{wa_id}{GREEN} - {response}{RESET}')
    send_message(data)


def is_valid_whatsapp_message(body):
    """
    Check if the incoming webhook event has a valid WhatsApp message structure.
    """
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )


def open_ai_response(wa_id, name, message_body):
    response = generate_response(message_body, wa_id, name)
    response = replace_phone(wa_id, response)
    response = process_text_for_whatsapp(response)
    return response

def download_audio(media_id):
    '''
    Retorna binário
    '''
    url = f"https://graph.facebook.com/v22.0/{media_id}"
    headers = {"Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        media_url = response.json().get("url")
        return requests.get(media_url, headers=headers).content  # Retorna o arquivo binário
    else:
        raise Exception("Erro ao baixar o áudio do WhatsApp")


def convert_audio_to_mp3(audio_bytes):
    audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="ogg")
    mp3_buffer = io.BytesIO()
    audio.export(mp3_buffer, format="mp3")
    return mp3_buffer.getvalue()


def process_audio_message(audio_id):
    try:
        audio_bytes = download_audio(audio_id)
        mp3_audio = convert_audio_to_mp3(audio_bytes)
        transcribed_text = transcribe_audio(mp3_audio)

        return transcribed_text

    except Exception as e:
        return FALSE


