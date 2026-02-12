import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import F

import yt_dlp

TOKEN = "ТВОЙ_ТОКЕН_ЗДЕСЬ"  # Не меняй, если уже в переменной окружения на Render

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class DownloadStates(StatesGroup):
    waiting_for_link = State()


@dp.message(CommandStart())
async def start_command(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Скачать видео", callback_data="download")]]
    )
    await message.answer(
        "Привет! Отправь ссылку на видео из YouTube или Instagram (публичное).",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "download")
async def request_link(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправь ссылку на видео:")
    await state.set_state(DownloadStates.waiting_for_link)
    await callback.answer()


@dp.message(DownloadStates.waiting_for_link)
async def process_link(message: Message, state: FSMContext):
    url = message.text.strip()
    await message.answer("Обрабатываю ссылку... (5–30 секунд)")

    ydl_opts = {
        'format': 'best[height<=720][ext=mp4]/best',  # Только готовые mp4
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'retries': 10,
        'socket_timeout': 30,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)  # Только метаданные и direct URL

        # Берём прямую ссылку
        if 'url' in info:
            direct_url = info['url']
        elif 'formats' in info:
            # Ищем лучший mp4 с аудио
            for f in info['formats']:
                if f.get('ext') == 'mp4' and f.get('height', 0) <= 720 and f.get('acodec') != 'none':
                    direct_url = f['url']
                    break
            else:
                raise Exception("Не найден подходящий формат")
        else:
            raise Exception("Не удалось получить ссылку")

        title = info.get('title', 'Видео')
        await message.answer_video(
            video=direct_url,
            caption=f"{title}\nИсточник: {url}",
            parse_mode="HTML"
        )
        await message.answer("Готово! Отправь ещё ссылку.")

    except Exception as e:
        await message.answer(
            "Не удалось скачать видео 😔\n"
            "Возможные причины:\n"
            "• Приватное/удалённое видео\n"
            "• Временная проблема YouTube\n"
            "• Попробуй другую ссылку или позже"
        )
        logging.error(f"Ошибка при обработке {url}: {str(e)}")  # Только в логи Render

    await state.clear()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())


