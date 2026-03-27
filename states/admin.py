from aiogram.fsm.state import State, StatesGroup


class AdminMove(StatesGroup):
    choosing_date = State()
    choosing_time = State()
