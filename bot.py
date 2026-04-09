import asyncio
import requests
import random
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# --- КОНФИГУРАЦИЯ ---
# Вставь свои данные сюда:
BOT_TOKEN = "8513650923:AAF73kg1AxH1UlsGW7gDSZyOCDkeBLP0tNY"
TMDB_API_KEY = "8dafad01b87d3621f0e3aa10a809f023"

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_URL = "https://image.tmdb.org/t/p/w500"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Временное хранилище для избранного
favorites = {}

# --- ФУНКЦИИ ---
def get_movie_info(movie):
    title = movie.get("title") or movie.get("name")
    rating = movie.get("vote_average", "Нет")
    date = movie.get("release_date", "Неизвестно")
    desc = movie.get("overview", "Описание отсутствует.")
    poster = f"{IMAGE_URL}{movie.get('poster_path')}" if movie.get('poster_path') else None
    
    # Текст без Markdown-разметки (* или _), чтобы бот не выдавал ошибку "can't parse entities"
    text = f"🎬 Название: {title}\n\n⭐ Рейтинг: {rating}\n📅 Дата: {date}\n\n📖 {desc[:350]}..."
    return text, poster

async def fetch_movies(endpoint, params={}):
    p = {"api_key": TMDB_API_KEY, "language": "ru-RU"}
    p.update(params)
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", params=p, timeout=10)
        if response.status_code == 200:
            return response.json().get("results", [])
    except:
        return []
    return []

async def send_movie_with_fav_button(message, movie):
    text, poster = get_movie_info(movie)
    title = movie.get("title") or movie.get("name")
    
    kb = InlineKeyboardBuilder()
    # Сохраняем первые 20 символов названия в кнопку
    kb.button(text="💖 В избранное", callback_data=f"add_fav_{title[:20]}")
    
    try:
        if poster:
            await message.answer_photo(poster, caption=text, reply_markup=kb.as_markup())
        else:
            await message.answer(text, reply_markup=kb.as_markup())
    except Exception as e:
        # Если фото не грузится, пробуем отправить просто текст
        try:
            await message.answer(text, reply_markup=kb.as_markup())
        except:
            print(f"Не удалось отправить сообщение: {e}")

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔥 Популярные")
    builder.button(text="🎲 Случайный")
    builder.button(text="🎯 По жанрам")
    builder.button(text="⭐ Избранное")
    builder.adjust(2)
    
    welcome_text = (
        "Привет! Я твой помощник по фильмам. 🍿\n"
        "Нажимай на кнопки или просто напиши название фильма, чтобы я его нашел! "
        "Под любым фильмом ты увидишь кнопку 'Добавить в избранное'."
    )
    
    await message.answer(welcome_text, reply_markup=builder.as_markup(resize_keyboard=True))

@dp.message(F.text == "⭐ Избранное")
async def show_favorites(message: types.Message):
    user_id = message.from_user.id
    if user_id not in favorites or not favorites[user_id]:
        await message.answer("Твой список избранного пока пуст! 📌")
        return
    
    fav_list = "\n".join([f"📍 {t}" for t in favorites[user_id]])
    await message.answer(f"Твои сохраненные фильмы:\n\n{fav_list}")

@dp.callback_query(F.data.startswith("add_fav_"))
async def add_to_favorites(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    movie_title = callback.data.replace("add_fav_", "")
    
    if user_id not in favorites:
        favorites[user_id] = []
    
    if movie_title not in favorites[user_id]:
        favorites[user_id].append(movie_title)
        await callback.answer(f"Добавлено: {movie_title}")
    else:
        await callback.answer("Уже есть в списке!")

@dp.message(F.text == "🔥 Популярные")
async def popular_movies(message: types.Message):
    movies = await fetch_movies("/movie/popular")
    # Берем 5 фильмов и отправляем каждый отдельным сообщением
    for movie in movies[:5]:
        await send_movie_with_fav_button(message, movie)

@dp.message(F.text == "🎲 Случайный")
async def random_movie(message: types.Message):
    page = random.randint(1, 10)
    movies = await fetch_movies("/movie/top_rated", params={"page": page})
    if movies:
        await send_movie_with_fav_button(message, random.choice(movies))

@dp.message(F.text == "🎯 По жанрам")
async def genre_menu(message: types.Message):
    builder = InlineKeyboardBuilder()
    genres = {28: "Боевик", 35: "Комедия", 18: "Драма", 27: "Ужасы", 878: "Фантастика"}
    for g_id, g_name in genres.items():
        builder.button(text=g_name, callback_data=f"genre_{g_id}")
    builder.adjust(2)
    await message.answer("Выберите жанр:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("genre_"))
async def show_genre_movies(callback: types.CallbackQuery):
    genre_id = callback.data.split("_")[1]
    movies = await fetch_movies("/discover/movie", params={"with_genres": genre_id})
    if movies:
        await send_movie_with_fav_button(callback.message, random.choice(movies))
    await callback.answer()

@dp.message()
async def search_movie(message: types.Message):
    if not message.text: return
    movies = await fetch_movies("/search/movie", params={"query": message.text})
    if movies:
        await send_movie_with_fav_button(message, movies[0])
    else:
        await message.answer("Ничего не нашлось. Попробуй другое название.")

# --- ЗАПУСК ---
async def main():
    print("Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот выключен")