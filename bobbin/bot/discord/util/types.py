from typing import Optional, Union

import discord
import discord.abc

type DiscordChannel = Optional[
    Union[
        discord.abc.GuildChannel,
        discord.Thread,
        discord.abc.PrivateChannel
    ]
]
