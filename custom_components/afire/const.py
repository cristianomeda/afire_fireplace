DOMAIN = "afire"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"

# AFIRE mobile app id (shared, not user-specific)
DEFAULT_APPID = "8dd16cd21b2d44a895c55897856496d5"

# Known product_key -> model
PRODUCT_MODELS = {
    "e2313fe07bca48fb82861d5f961993c5": "PRESTIGE",
    # TODO: Add ADVANCE product_key once identified
}

# Polling interval for cloud updates (seconds)
UPDATE_INTERVAL = 30