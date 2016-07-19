# Pokemon Giveaway Galore Flair Bot

Bot that assigns the flairs of users to whatever they message it.


*****

# Dependancies

*****

- PRAW

Makes posts using the PRAW Reddit API library.

*****

# Configuration

*****

All configurations are made via the `config.json` file.

```JSON
{
    "user_agent": "",
    "username": "",
    "password": "",
    "check_rate": 60,
    "subreddit": "",
    "default_flair_css_class": "Pikachu",
    "commands": {
        "friend_code": [
            "fc",
            "friend code"
        ],
        "flair_css_class": [
            "flair",
            "css",
            "pokemon"
        ],
        "in_game_name": [
            "ign",
            "username"
        ],
        "message": [
            "message",
            "note"
        ]
    }
}
```

- `user_agent`
    - What Google and Reddit sees the bot as, the more unique this is the better.
- `username`
    - Username of the reddit account making the posts.
- `password`
    - Password of the Reddit account making the posts.
- `check_rate`
    - How often - in seconds - to check for new messages and update flairs.
- `subreddit`
    - Subreddit to run in.
- `default_flair_css_class`
    - Default flair CSS class if none is provided.
- `commands`
    - List of commands and their triggers.

A command consists of two properties:

The key of the command, which is the internal immutable name of the command, and the list of strings within the key, which is what triggers the command.

> Note these must be lowercase, but will match any case from the users perspective.


*****

# Usage

*****

An example message would look like such:

    Pokemon: Pikachu
    Message: <3 Pikachu
    FC: 1234-5678-9012
    IGN: PokemonMaster123

These options can be in any order, and you can have as few or as many of them as you want. You can only change the flair, a certain part of your flair text, or - as shown above - every part of your flair.

Case does not matter for both the attribute to be set - left of the colen - and for the css class.

*****

# Technical Breakdown

*****

## Databases

*****

The bot has three databases, `processed`, `flairs`, and `history`.

### Processed

ID | UTC | Body
--- |  ---  | ---
a1b2c3d | 1451606400 | Actual text of comment\n\nPokemon: Pikachu

Contains all processed messages.

Only 100,000 entries are kept in the table.

### Flairs

User | UTC | Text | CSS
---  | --- |  --- | ---
Rascal_Two | 1451606400 | 1234-5678-9012 \| Rascal_Two \|\| <3 Pikachu | item

Contains the current flairs for all users.

Only 100,000 entries are kept in the table.

### History

User | UTC | Text | CSS
---  | --- |  --- | ---
Rascal_Two | 1451606400 | 1234-5678-9012 \| Rascal_Two \|\| <3 Pikachu | item

This is an log of flairs the bot has set.

Only 100,000 entries are kept in the table.

*****

## Walkthough

*****

- Tables and triggers are created if they're don't already exist.
- Reddit is logged into.
- While the bot is running:
    - List of un-read messages are fetched.
    - For every message in the list of un-read messages:
        - If the message has already been processed, it's skipped.
        - The requested options are parsed from the message.
        - These options used in combination with the current flair to set the new flair.
    - The bot waits `check_rate` seconds, and does the above items again.
