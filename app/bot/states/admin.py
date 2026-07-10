"""FSM-состояния административной панели."""

from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    """Состояния диалога управления пользователями."""

    waiting_phone = State()
