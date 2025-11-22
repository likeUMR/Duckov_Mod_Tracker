# Mod 追踪配置
# 格式：mod_id: {name, url, mod_id, is_main}

MODS = {
    3596640733: {
        'name': '更好的外观预设 Better Appearance Preset',
        'url': 'https://steamcommunity.com/sharedfiles/filedetails/?id=3596640733',
        'mod_id': 3596640733,
        'is_main': True  # Main mod - other mods align to its timestamps
    },
    3597297032: {
        'name': '隐藏身上装备 Hide Body Equipment',
        'url': 'https://steamcommunity.com/sharedfiles/filedetails/?id=3597297032',
        'mod_id': 3597297032,
        'is_main': False
    },
    3599597476: {
        'name': '隐藏狗子 Hide The Pet',
        'url': 'https://steamcommunity.com/sharedfiles/filedetails/?id=3599597476',
        'mod_id': 3599597476,
        'is_main': False
    }
}

# Get main mod ID
MAIN_MOD_ID = next((mod_id for mod_id, info in MODS.items() if info.get('is_main', False)), None)

