import json
from typing import List, Optional, Text

import aiohttp
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from linebot import AsyncLineBotApi
from linebot.aiohttp_async_http_client import AiohttpAsyncHttpClient
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    SourceUser,
    TextMessage,
    TextSendMessage,
)

from app.bot.line.handler import AsyncWebhookHandler
from app.config import logger, settings
from app.resources.chat import requests_chat_api
from app.schemas.channel import LineCallback
from app.schemas.chat import Message
from app.schemas.tracker import Message as TrackerMessage
from app.utils.datetime import datetime_now


router = APIRouter()


line_bot_api = AsyncLineBotApi(
    settings.line_channel_access_token,
    async_http_client=AiohttpAsyncHttpClient(aiohttp.ClientSession()),
)
handler = AsyncWebhookHandler(settings.line_channel_secret)


async def get_user_records(
    source_user_id: Text,
    source_group_id: Optional[Text] = None,
    record_length: int = 10,
) -> List["TrackerMessage"]:
    """Get user records.

    Parameters
    ----------
    source_user_id : Text
        User ID.
    source_group_id : Optional[Text], optional
        Group ID, by default None
    record_length : int, optional
        Record length, by default 10

    Returns
    -------
    List["TrackerMessage"]
        User records.
    """

    records = (
        await TrackerMessage.objects.limit(record_length)
        .filter(source_user_id=source_user_id)
        .order_by(TrackerMessage.message_datetime.desc())
        .all()
    )
    return records


@handler.add(MessageEvent, message=TextMessage)
async def handle_message(event: MessageEvent):
    """Handle Line text message.

    Parameters
    ----------
    event : MessageEvent
        Line message event.
    """

    logger.debug(f"Line event {type(event)}: {event}")

    line_message: "TextMessage" = event.message
    line_source: "SourceUser" = event.source

    # Collect user message records and save new record
    user_message = TrackerMessage.from_line_text_message(
        text_message=line_message, source=line_source
    )
    records = await get_user_records(source_user_id=line_source.user_id)
    await user_message.save()

    # Call Chat API
    chat_call_messages: List[Message] = []
    for record in records[::-1]:
        if record.source_type == "user" and record.message_type == "text":
            chat_call_messages.append(Message(role="user", content=record.message_text))
        elif record.source_type == "bot" and record.message_type == "text":
            chat_call_messages.append(
                Message(role="assistant", content=record.message_text)
            )
    chat_call_messages.append(Message(role="user", content=line_message.text))
    logger.debug(f"Call chat messages: {chat_call_messages}")

    res_messages = await requests_chat_api(messages=chat_call_messages)
    logger.debug(f"Return chat messages: {res_messages}")

    # Reply Line message
    for res_message in res_messages:
        await line_bot_api.reply_message(
            event.reply_token, TextSendMessage(text=res_message["content"].strip())
        )

    # Save bot message records
    for res_message in res_messages:
        bot_message = TrackerMessage(
            message_type="text",
            message_text=res_message["content"].strip(),
            source_type="bot",
            source_user_id=line_source.user_id,
            message_datetime=datetime_now(tz=settings.app_timezone),
        )
        await bot_message.save()


@router.post("/callback")
async def callback(request: Request, x_line_signature: Text = Header(...)):
    """Line callback endpoint.

    Parameters
    ----------
    request : Request
        FastAPI request.
    x_line_signature : Text, optional
        Line signature, must be set in header.
    """

    # get request body as text
    line_callback_data = await request.body()
    line_callback = LineCallback(**json.loads(line_callback_data))
    logger.debug(f"line_callback: {line_callback.json(ensure_ascii=False)}")

    line_callback_str = line_callback_data.decode("utf-8")

    # handle webhook body
    try:
        await handler.async_handle(line_callback_str, x_line_signature)
    except InvalidSignatureError as e:
        logger.exception(e)
        logger.error(
            "Invalid signature. Please check your channel access token/channel secret."
        )
        raise HTTPException(status_code=400)

    return PlainTextResponse("OK")
