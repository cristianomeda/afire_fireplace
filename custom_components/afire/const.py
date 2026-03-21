DOMAIN = "afire"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"

SERIES_AWPR = "AWPR"
SERIES_AWPR2 = "AWPR2"

MODEL_PRESTIGE = "PRESTIGE"
MODEL_ADVANCED = "ADVANCED"

# AFIRE mobile app id for the legacy AWPR mobile app.
DEFAULT_APPID = "8dd16cd21b2d44a895c55897856496d5"

# Known legacy AWPR product_key -> model mappings.
AWPR_PRODUCT_MODELS = {
    "e2313fe07bca48fb82861d5f961993c5": MODEL_PRESTIGE,
    # TODO: Add AWPR ADVANCED product_key once identified.
}

# Known AWPR2 iotId -> model mappings.
AWPR2_IOT_MODELS = {
    # TODO: Add AWPR2 PRESTIGE / ADVANCED iotId mappings once identified.
}
AWPR2_DEFAULT_MODEL = MODEL_PRESTIGE

POLL_INTERVAL_SECONDS = 30
AWPR2_REFRESH_DELAY_SECONDS = 3
AWPR2_COMMAND_DELAY_SECONDS = 0.2

NUMBER_SPECS = {
    "FLAME": {"label": "Flame Height", "min": 0, "max": 5, "step": 1, "icon": "mdi:fire"},
    "SPEED": {"label": "Flame Speed", "min": 0, "max": 5, "step": 1, "icon": "mdi:fan"},
    "BRIGHTNESS": {"label": "Brightness", "min": 1, "max": 5, "step": 1, "icon": "mdi:brightness-6"},
}

COLOR_PRESETS = {
    "Red 1": ("RED_KEY1", (198, 50, 38)),
    "Red 2": ("RED_KEY2", (232, 61, 42)),
    "Red 3": ("RED_KEY3", (232, 89, 21)),
    "Red 4": ("RED_KEY4", (232, 154, 41)),
    "Red 5": ("RED_KEY5", (249, 234, 37)),
    "Green 1": ("GREEN_KEY1", (99, 152, 74)),
    "Green 2": ("GREEN_KEY2", (168, 201, 65)),
    "Green 3": ("GREEN_KEY3", (144, 182, 164)),
    "Green 4": ("GREEN_KEY4", (125, 174, 190)),
    "Green 5": ("GREEN_KEY5", (90, 159, 218)),
    "Blue 1": ("BLUE_KEY1", (88, 85, 132)),
    "Blue 2": ("BLUE_KEY2", (108, 110, 173)),
    "Blue 3": ("BLUE_KEY3", (117, 78, 107)),
    "Blue 4": ("BLUE_KEY4", (168, 99, 122)),
    "Blue 5": ("BLUE_KEY5", (196, 103, 144)),
}

AWPR_EFFECTS = {
    "Smooth": "KEY_SMOOTH",
    "Fade 1": "KEY_FADE1",
    "Fade 2": "KEY_FADE2",
}

AWPR2_EFFECTS = {
    "Smooth": "RGB_PLAY",
}

AWPR2_COLOR_COMMANDS = {
    "RED_KEY1": "KeyB",
    "RED_KEY2": "KeyC",
    "RED_KEY3": "KeyD",
    "RED_KEY4": "KeyE",
    "RED_KEY5": "KeyF",
    "GREEN_KEY1": "KeyG",
    "GREEN_KEY2": "KeyH",
    "GREEN_KEY3": "KeyI",
    "GREEN_KEY4": "KeyJ",
    "GREEN_KEY5": "KeyK",
    "BLUE_KEY1": "KeyL",
    "BLUE_KEY2": "KeyM",
    "BLUE_KEY3": "KeyN",
    "BLUE_KEY4": "KeyO",
    "BLUE_KEY5": "KeyP",
}

AWPR2_COLOR_STATE_MAP = {
    "1": "RED_KEY1",
    "2": "RED_KEY2",
    "3": "RED_KEY3",
    "4": "RED_KEY4",
    "5": "RED_KEY5",
    "6": "GREEN_KEY1",
    "7": "GREEN_KEY2",
    "8": "GREEN_KEY3",
    "9": "GREEN_KEY4",
    "A": "GREEN_KEY5",
    "B": "BLUE_KEY1",
    "C": "BLUE_KEY2",
    "D": "BLUE_KEY3",
    "E": "BLUE_KEY4",
    "F": "BLUE_KEY5",
}
