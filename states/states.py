from aiogram.fsm.state import State, StatesGroup


class FlowerStates(StatesGroup):
    waiting_type = State()  # First: auction or regular
    waiting_media = State()  # Photo or video (collecting multiple)
    waiting_media_done = State()  # Waiting for "done" or more media
    waiting_name = State()
    waiting_description = State()
    waiting_price = State()
    waiting_phone = State()
    waiting_location = State()
    waiting_auction_duration = State()
    waiting_confirm = State()
    waiting_payment = State()  # Waiting for payment to complete flower


class PaymentStates(StatesGroup):
    waiting_amount = State()
    waiting_screenshot = State()
    waiting_screenshot_for_flower = State()  # Payment for pending flower


class AdminStates(StatesGroup):
    waiting_card_number = State()
    waiting_diamond_price = State()
    waiting_user_id_for_diamonds = State()
    waiting_diamond_amount = State()
    waiting_broadcast_message = State()


class AuctionStates(StatesGroup):
    in_auction = State()
    waiting_bid = State()
