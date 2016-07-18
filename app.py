# The MIT License (MIT)

# Copyright (c) 2016 Rascal_Two

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Bot that assigns flairs to users for them."""

import praw
import json
import sqlite3
import time


class PokemonGiveawayGloreBot(object):
    """Bot that assigns flairs to users for them."""

    def __init__(self):
        """Create database and import settings."""
        self.running = False

        with open("config.json", "r") as config_file:
            self.config = json.loads(config_file.read())

        self.db = sqlite3.connect("database.db")
        cur = self.db.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS processed(
                id   TEXT  NOT NULL  PRIMARY KEY,
                utc  INT   NOT NULL,
                body TEXT   NOT NULL
            )
        """)
        cur.execute("""
            CREATE TRIGGER IF NOT EXISTS processed_limit AFTER INSERT ON processed
              BEGIN
                DELETE FROM processed WHERE utc <= (SELECT utc FROM processed ORDER BY utc DESC LIMIT 100000, 1);
              END;
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS flairs(
                user  TEXT  NOT NULL  PRIMARY KEY,
                utc   INT   NOT NULL,
                text  TEXT,
                css   TEXT
            )
        """)
        cur.execute("""
            CREATE TRIGGER IF NOT EXISTS flairs_limit AFTER INSERT ON flairs
              BEGIN
                DELETE FROM flairs WHERE utc <= (SELECT utc FROM flairs ORDER BY utc DESC LIMIT 100000, 1);
              END;
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS history(
                user  TEXT  NOT NULL,
                utc   INT   NOT NULL,
                text  TEXT,
                css   TEXT
            )
        """)
        cur.execute("""
            CREATE TRIGGER IF NOT EXISTS history_limit AFTER INSERT ON history
              BEGIN
                DELETE FROM history WHERE utc <= (SELECT utc FROM history ORDER BY utc DESC LIMIT 100000, 1);
              END;
        """)
        cur.close()
        self.db.commit()
        self.db.close()

    def execute(self, statement, arguments=()):
        """Execute a provided SQLITE3 statement."""
        if not isinstance(arguments, tuple):
            arguments = (arguments, )
        cur = self.db.cursor()
        cur.execute(statement, arguments)
        cur.close()
        self.db.commit()

    def query(self, statement, arguments=()):
        """Query from the database."""
        if not isinstance(arguments, tuple):
            arguments = (arguments, )
        cur = self.db.cursor()
        cur.execute(statement, arguments)
        results = cur.fetchall()
        cur.close()
        return results

    def _get_processed(self):
        """Return list of processed IDs."""
        return [pid[0] for pid in self.query("SELECT id FROM processed")]

    def _add_processed(self, message):
        """Add processed message to database."""
        self.execute("INSERT INTO processed "
                     "VALUES (?, ?, ?)",
                     (message.id, int(time.time()), message.body))

    def _combine_flair_data(self, primary, secondary):
        """Combine current and newly defined flair data."""
        for attrib in secondary:
            if attrib not in primary or (attrib in primary and primary[attrib] is not None):
                continue
            primary[attrib] = secondary[attrib]
        return primary

    def _flair_text_as(self, data, return_type):
        """Return flair text as either a "str" or "dict"."""
        if return_type == "str":
            if isinstance(data, str):
                return data
            string = ""
            if data["friend_code"] is None:
                string += "0000-0000-0000"
            else:
                string += data["friend_code"]
            if data["in_game_name"] is None:
                if data["message"] is None:
                    return string
                return "{} |  || {}".format(string, data["message"])
            if data["message"] is None:
                return "{} |  || {}".format(string, data["message"])
            return "{} | {} || {}".format(string, data["in_game_name"], data["message"])
        elif return_type == "dict":
            if isinstance(data, dict):
                return data
            return_data = {}
            if "||" in data:
                return_data["message"] = data.split("||")[1].strip()
                data = data.split("||")[0]
            if "|" in data:
                return_data["friend_code"] = data.split("|")[0].strip()
                return_data["in_game_name"] = data.split("|")[1].strip()
            else:
                return_data["friend_code"] = data.strip()
            for data in return_data:
                if return_data[data] == "":
                    return_data[data] = None
            return return_data

    def _set_flair(self, data):
        """Set the flair for a user."""
        sub = self.reddit.get_subreddit(self.config["subreddit"])
        raw_old_flair = sub.get_flair(data["username"])

        if data["flair_css_class"] is None:
            if raw_old_flair["flair_css_class"] != None:
                data["flair_css_class"] = raw_old_flair["flair_css_class"]
            else:
                data["flair_css_class"] = self.config["default_flair_css_class"].lower()
        else:
            data["flair_css_class"] = data["flair_css_class"].lower()

        old_flair = self._flair_text_as(raw_old_flair["flair_text"], "dict")
        data = self._combine_flair_data(data, old_flair)
        flair_text = self._flair_text_as(data, "str")
        if raw_old_flair["flair_text"] == flair_text and raw_old_flair["flair_css_class"] == data["flair_css_class"]:
            return False
        sub.set_flair(data["username"],
                      flair_text=flair_text,
                      flair_css_class=data["flair_css_class"])
        data = (data["username"], int(time.time()), flair_text, data["flair_css_class"])
        self.execute("INSERT OR REPLACE INTO flairs "
                     "VALUES (?, ?, ?, ?)",
                     data)
        self.execute("INSERT INTO history "
                     "VALUES (?, ?, ?, ?)",
                     data)
        return True

    def _process_message(self, message):
        """Return the data from a message."""
        data = {
            "username": message.author.name,
            "friend_code": None,
            "in_game_name": None,
            "flair_css_class": None,
            "message": None
        }
        lines = [line.strip() for line in list(set(message.body.split("\n")))]
        for line in lines:
            for command in self.config["commands"]:
                if line.lower().split(":")[0] not in self.config["commands"][command]:
                    continue
                data[command] = line.split(":")[1].strip()
        return data

    def run(self):
        """Login to reddit and begin running the bot."""
        self.running = True
        self.db = sqlite3.connect("database.db")

        self.reddit = praw.Reddit(self.config["user_agent"])
        self.reddit.login(self.config["username"],
                          self.config["password"],
                          disable_warning=True)

        while True:
            for message in self.reddit.get_unread():
                if message.id in self._get_processed():
                    continue
                self._add_processed(message)
                message.mark_as_read()
                flair_data = self._process_message(message)
                self._set_flair(flair_data)
            print("Waiting...")
            time.sleep(self.config["check_rate"])

if __name__ == "__main__":
    PokemonGiveawayGloreBot().run()
