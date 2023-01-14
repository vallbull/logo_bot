from config import API_TOKEN, database, user, password, host, MyID, PSWD
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.types import ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
import psycopg2

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
connection = psycopg2.connect(
    database=database,
    user=user,
    password=password,
    host=host,
)


class AddPupil(StatesGroup):
    name = State()
    parent = State()
    phone = State()
    weekday = State()
    hour = State()
    stop = State()


class Illness(StatesGroup):
    start_or_stop = State()
    name = State()
    date = State()


class DeletePupil(StatesGroup):
    name = State()


allowed_id = list()

menu_keyboard = ReplyKeyboardMarkup(one_time_keyboard=True).add(
    KeyboardButton(text="Вывести расписание на неделю")).add(KeyboardButton(text='Вывести список детей')).row(
    KeyboardButton(text="Добавить нового ребенка"), KeyboardButton(text="Удалить ребенка")).add(
    KeyboardButton(text="Отметить болезнь"), KeyboardButton(text="Посмотреть болезни"))

weekdays = {'понедельник': 'mon', 'вторник': 'tue', 'среда': 'wed', 'четверг': 'thu', 'пятница': 'fri',
            'суббота': 'sat', 'воскресенье': 'sun'}


@dp.message_handler(text=PSWD)
async def send_welcome(message: types.Message):
    await message.answer("Привет! Теперь у тебя есть права администратора!")
    allowed_id.append(message.from_user.id)


@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer("Привет!\nЯ помогу тебе вести расписание занятий\nНажми /menu для управления расписанием")


@dp.message_handler(commands=['menu'])
async def send_menu(message: types.Message):
    await message.answer("Выбери действие", reply_markup=menu_keyboard)


def add_day(curs, day):
    all_users = curs.fetchall()
    text = ""
    text += '*' + day + '*\n'
    if len(all_users) == 0:
        text += '\tНет занятий\n'
    else:
        for pupil in all_users:
            if pupil[1] is not None:
                text += '\t' + str(pupil[1]) + '\t\t' + str(pupil[0]) + '\n'
    return text + '\n'


@dp.message_handler(content_types=['text'])
async def get_text_messages(message):
    if message.text == 'Вывести расписание на неделю':
        text = ""
        with connection.cursor() as curs:
            curs.execute('SELECT name, mon FROM logo_scheduler.timetable WHERE mon is NOT NULL ORDER BY mon')
            text += add_day(curs, 'Понедельник')
            curs.execute('SELECT name, tue FROM logo_scheduler.timetable where tue is not NULL ORDER BY tue')
            text += add_day(curs, 'Вторник')
            curs.execute('SELECT name, wed FROM logo_scheduler.timetable where wed is not NULL ORDER BY wed')
            text += add_day(curs, 'Среда')
            curs.execute('SELECT name, thu FROM logo_scheduler.timetable where thu is not NULL ORDER BY thu')
            text += add_day(curs, 'Четверг')
            curs.execute('SELECT name, fri FROM logo_scheduler.timetable where fri is not NULL ORDER BY fri')
            text += add_day(curs, 'Пятница')
            curs.execute('SELECT name, sat FROM logo_scheduler.timetable where sat is not NULL ORDER BY sat')
            text += add_day(curs, 'Суббота')
            curs.execute('SELECT name, sun FROM logo_scheduler.timetable where sun is not NULL ORDER BY sun')
            text += add_day(curs, 'Воскресенье')
        await message.answer(text + 'Нажмите /menu для просмотра действий', parse_mode="Markdown")


    elif message.text == 'Добавить нового ребенка':
        print(message)
        if message.from_user.id not in allowed_id:
            await message.answer("У вас нет прав. Попросите пароль у администратора. Вы можете посмотреть расписание и список детей")
            return None
        await AddPupil.name.set()
        await bot.send_message(message.chat.id,
                               "Введите фамилию и имя ребенка:\n\nЧтобы отменить добавление нажмите /cancel или "
                               "введите \"Отмена\" ")


    elif message.text == 'Удалить ребенка':
        if message.from_user.id not in allowed_id:
            await message.answer("У вас нет прав. Попросите пароль у администратора. Вы можете посмотреть расписание и список детей")
            return None

        delete_keyboard = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        with connection.cursor() as curs:
            curs.execute("SELECT name FROM logo_scheduler.pupils")
            all_users = curs.fetchall()
            for pupil in all_users:
                delete_keyboard.add(str(pupil[0]))

        if len(delete_keyboard['keyboard']) != 0:
            await bot.send_message(message.chat.id,
                                   "Выберите ребенка, которого надо удалить\n\nЧтобы отменить удаление нажмите "
                                   "/cancel или введите \"Отмена\" ",
                                   reply_markup=delete_keyboard)
            await DeletePupil.name.set()
        else:
            await bot.send_message(message.chat.id, 'У вас пока нет учеников', reply_markup=menu_keyboard)


    elif message.text == 'Отметить болезнь':
        if message.from_user.id not in allowed_id:
            await message.answer("У вас нет прав. Попросите пароль у администратора. Вы можете посмотреть расписание и список детей")
            return None
        kb = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True).add(
            KeyboardButton(text="Кто-то заболел"), KeyboardButton(text="Кто-то выздоровел"))
        await Illness.start_or_stop.set()
        await bot.send_message(message.chat.id, "Выберите, что хотите отметить\n\nЧтобы отменить действие нажмите "
                                                "/cancel или введите \"Отмена\" ", reply_markup=kb)


    elif message.text == 'Вывести список детей':
        with connection.cursor() as curs:
            curs.execute('SELECT * FROM logo_scheduler.pupils')
            all_users = curs.fetchall()
            text = ""
            if len(all_users) == 0:
                await bot.send_message(message.chat.id, 'У вас пока нет учеников', reply_markup=menu_keyboard)
            else:
                for pupil in all_users:
                    text += '\n*' + str(pupil[0]) + ':*\n\t\tРодитель: ' + str(pupil[1]) + '\n\t\tТелефон:   ' + str(
                        pupil[2]) + '\n'
                await message.answer(text, parse_mode="Markdown", reply_markup=menu_keyboard)

    elif message.text == 'Посмотреть болезни':
        with connection.cursor() as curs:
            curs.execute('SELECT * FROM logo_scheduler.illness order by (stop, start)')
            all = curs.fetchall()
            if len(all) == 0:
                await bot.send_message(message.chat.id, 'Никто еще не болел!', reply_markup=menu_keyboard)
            else:
                text = '*Даты болезней:*\n'
                for pupil in all:
                    if pupil[2] is None:
                        text += pupil[1] + ' - ' + 'еще болеет' + ' *' + pupil[0] + '*\n'
                    else:
                        text += pupil[1] + ' - ' + pupil[2] + ' *' + pupil[0] + '* \t(пропущено n дней)\n'
                await message.answer(text, parse_mode="Markdown", reply_markup=menu_keyboard)


@dp.message_handler(commands=['cancel'],
                    state=[AddPupil.parent, AddPupil.phone, AddPupil.weekday, AddPupil.hour,
                           AddPupil.stop])
async def cancel_handler1(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return
    async with state.proxy() as data:
        with connection.cursor() as curs:
            curs.execute('DELETE FROM logo_scheduler.pupils WHERE name=%s', (data['name'],))
            connection.commit()

    await state.finish()
    await message.reply('Отменено', reply_markup=menu_keyboard)


@dp.message_handler(text='Отмена',
                    state=[AddPupil.parent, AddPupil.phone, AddPupil.weekday, AddPupil.hour,
                           AddPupil.stop])
async def cancel_handler2(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    async with state.proxy() as data:
        with connection.cursor() as curs:
            curs.execute('DELETE FROM logo_scheduler.pupils WHERE name=%s', (data['name'],))
            connection.commit()

    await state.finish()
    # And remove keyboard (just in case)
    await message.reply('Отменено', reply_markup=menu_keyboard)


@dp.message_handler(commands=['cancel'],
                    state=[DeletePupil.name, AddPupil.name, Illness.start_or_stop, Illness.name, Illness.date])
async def cancel_handler1(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.finish()
    await message.reply('Отменено', reply_markup=menu_keyboard)


@dp.message_handler(text='Отмена',
                    state=[DeletePupil.name, AddPupil.name, Illness.start_or_stop, Illness.name, Illness.date])
async def cancel_handler2(message: types.Message, state: FSMContext):
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.finish()
    # And remove keyboard (just in case)
    await message.reply('Отменено', reply_markup=menu_keyboard)


@dp.message_handler(state=Illness.start_or_stop)
async def process_illness_start_or_stop(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['start_or_stop'] = message.text

    await Illness.next()
    if data['start_or_stop'] == 'Кто-то заболел':
        all = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        with connection.cursor() as curs:
            curs.execute("SELECT name FROM logo_scheduler.pupils")
            all_users = curs.fetchall()
            for pupil in all_users:
                all.add(str(pupil[0]))

        if len(all['keyboard']) != 0:
            await message.reply(
                "Выберите, кто заболел\n\nЧтобы отменить действие нажмите "
                "/cancel или введите \"Отмена\" ", reply_markup=all)
        else:
            await bot.send_message(message.chat.id, 'У вас пока нет учеников', reply_markup=menu_keyboard)
            await state.finish()


    else:
        all = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        with connection.cursor() as curs:
            curs.execute("SELECT name FROM logo_scheduler.illness where stop is null")
            all_users = curs.fetchall()
            for pupil in all_users:
                all.add(str(pupil[0]))

        if len(all['keyboard']) != 0:
            await message.reply(
                "Выберите, кто выздоровел\n\nЧтобы отменить действие нажмите "
                "/cancel или введите \"Отмена\" ", reply_markup=all)
        else:
            await bot.send_message(message.chat.id, 'Никто не болеет!', reply_markup=menu_keyboard)
            await state.finish()


@dp.message_handler(state=Illness.name)
async def process_illness_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await Illness.next()
    if data['start_or_stop'] == 'Кто-то заболел':
        await message.reply("Введите дату начала болезни в формате dd.mm:\n\nЧтобы отменить действие нажмите "
                            "/cancel или введите \"Отмена\" ")
    else:
        await message.reply("Введите дату конца болезни в формате dd.mm:\n\nЧтобы отменить действие нажмите "
                            "/cancel или введите \"Отмена\" ")


@dp.message_handler(state=Illness.date)
async def process_illness_date(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['date'] = message.text
    if data['start_or_stop'] == 'Кто-то заболел':
        with connection.cursor() as curs:
            curs.execute('INSERT INTO logo_scheduler.illness(name, start, stop) values(%s, %s, NULL)',
                         (data['name'], data['date']))
            connection.commit()
            await bot.send_message(message.chat.id, 'Готово', reply_markup=menu_keyboard)
    else:
        with connection.cursor() as curs:
            curs.execute('UPDATE logo_scheduler.illness SET stop=%s WHERE name=%s and stop is null',
                         (data['date'], data['name']))
            connection.commit()
            await bot.send_message(message.chat.id, 'Готово', reply_markup=menu_keyboard)

    await state.finish()


@dp.message_handler(state=AddPupil.name)
async def process_add_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text

    with connection.cursor() as curs:
        curs.execute('SELECT name FROM logo_scheduler.pupils WHERE name=%s', (data['name'],))
        if len(curs.fetchall()) != 0:
            await bot.send_message(message.chat.id, 'Такой ребенок уже есть в списке. Действие отменено',
                                   reply_markup=menu_keyboard)
            await state.finish()
        else:
            await AddPupil.next()
            await message.reply(
                "Введите фамилию и имя родителя ученика {}:\n\nЧтобы отменить добавление нажмите /cancel или введите \"Отмена\"".format(
                    data['name']))


@dp.message_handler(state=AddPupil.parent)
async def process_add_parent(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['parent'] = message.text

    await AddPupil.next()
    await message.reply("Введите телефон родителя:\n\nЧтобы отменить добавление нажмите /cancel или введите \"Отмена\"")


@dp.message_handler(state=AddPupil.phone)
async def process_add_phone(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['phone'] = message.text

    with connection.cursor() as curs:
        curs.execute('INSERT INTO logo_scheduler.pupils(name, parent_name, parent_phone) values(%s, %s, %s)',
                     (data['name'], data['parent'], data['phone']))
        curs.execute('INSERT INTO logo_scheduler.timetable(name) values(%s)',
                     (data['name'],))
        connection.commit()

    await AddPupil.next()

    weekday_kb = ReplyKeyboardMarkup(one_time_keyboard=True).add(
        KeyboardButton(text="понедельник"),
        KeyboardButton(text="вторник")).add(
        KeyboardButton(text="среда"),
        KeyboardButton(text="четверг")).add(
        KeyboardButton(text="пятница"),
        KeyboardButton(text="суббота")).add(
        KeyboardButton(text="воскресенье"))

    await message.reply(
        "Выберите день недели, в который ребенок будет приходить(потом можно будет выбрать еще один)\n\nЧтобы отменить добавление нажмите /cancel или введите \"Отмена\"",
        reply_markup=weekday_kb)


@dp.message_handler(state=AddPupil.weekday)
async def process_add_weekday(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['weekday'] = weekdays[message.text]

    await AddPupil.next()
    await message.reply(
        "Введите время в формате hh:mm\n\nЧтобы отменить добавление нажмите /cancel или введите \"Отмена\"")


@dp.message_handler(state=AddPupil.hour)
async def process_add_weekday(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['hour'] = message.text

    with connection.cursor() as curs:
        print(data['weekday'])
        curs.execute('UPDATE logo_scheduler.timetable SET {}={} WHERE name={}'.format(data['weekday'],
                                                                                      "'" + str(data['hour']) + "'",
                                                                                      "'" + str(data['name']) + "'"))
        connection.commit()
        print(1)

    await AddPupil.next()

    stop_kb = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True).add(
        KeyboardButton(text="Готово")).add(
        KeyboardButton(text="Добавить еще день"))
    await message.reply("Это все?", reply_markup=stop_kb)


@dp.message_handler(state=AddPupil.stop)
async def process_add_stop(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['stop'] = message.text
    if message.text == 'Готово':
        name = 'Добавил *' + data['name'] + '*'
        await message.answer(name, parse_mode="Markdown", reply_markup=menu_keyboard)
        await state.finish()

    elif message.text == 'Добавить еще день':
        await AddPupil.weekday.set()
        weekday_kb = ReplyKeyboardMarkup(one_time_keyboard=True).add(
            KeyboardButton(text="понедельник"),
            KeyboardButton(text="вторник")).add(
            KeyboardButton(text="среда"),
            KeyboardButton(text="четверг")).add(
            KeyboardButton(text="пятница"),
            KeyboardButton(text="суббота")).add(
            KeyboardButton(text="воскресенье"))

        await message.reply(
            "Выберите день недели, в который ребенок будет приходить(потом можно будет выбрать еще один\n\nЧтобы отменить добавление нажмите /cancel или введите \"Отмена\")",
            reply_markup=weekday_kb)

    else:
        stop_kb = ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True).add(
            KeyboardButton(text="Готово")).add(
            KeyboardButton(text="Добавить еще день"))
        await message.reply("Выберите из предложенных", reply_markup=stop_kb)


@dp.message_handler(state=DeletePupil.name)
async def process_delete_name(message: types.Message, state: FSMContext):
    print(state)
    async with state.proxy() as data:
        data['delete_name'] = message.text
    with connection.cursor() as curs:
        curs.execute('DELETE FROM logo_scheduler.pupils WHERE name=%s RETURNING *', (data['delete_name'],))
        if curs.fetchone() is None:
            await message.answer('Такого ученика нет', reply_markup=menu_keyboard)
        else:
            connection.commit()
            text = 'Удалил *' + data['delete_name'] + '*'
            await message.answer(text, parse_mode="Markdown", reply_markup=menu_keyboard)
        await state.finish()


if __name__ == '__main__':
    allowed_id.append(MyID)
    executor.start_polling(dp)
