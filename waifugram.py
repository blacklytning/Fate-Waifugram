import mysql.connector
import random
import logging
import unidecode
import re
import time
from telegram.ext import *
from telegram import *
from telegram.ext import MessageHandler, Filters

db = mysql.connector.connect(
    host="localhost",
    user="PUT YOUR ROOT",
    passwd="PUT YOUR PASSWORD",
    database="PUT YOUR DB",
    autocommit=True)
mycursor = db.cursor(buffered=True)

logger = logging.getLogger(__name__)
updater = Updater('PUT YOUR BOT TOKEN', use_context=True)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

    
# Create sleep call that makes a call every hour
@run_async
def calldb():
    mycursor.execute("""SELECT Name_Servant
                        FROM servants
                        WHERE ID_Servant = 1""")
    data = mycursor.fetchone()
    print("ping: " + data[0])
    time.sleep(1800)
    calldb()


calldb()


# REGULAR CHAT
# Update the message time
def maindef(update: Update, context: CallbackContext):
    # Collect group data
    Supergroup_name = str(update.message.chat.title)
    ID_Supergroup = str(update.message.chat.id)

    # Check if the group is registered in the db
    NewGroup(ID_Supergroup, Supergroup_name)

    # Refresh the group data
    UpdateGroup(ID_Supergroup, context)


# PRIVATE CHAT
def private(update: Update, context: CallbackContext):
    update.message.reply_text(text="This doesn't look like a group kek. "
                                   "Add me to one to get start collecting servants waifus OwO. "
                                   "In a group you can use /protecc to catch waifus and "
                                   "/listservants to view your waifus. (If this really is a group, "
                                   "try re-adding the bot).")


# INFORMATION ABOUT THE BOT
def help(update: Update, context: CallbackContext):
    update.message.reply_text(text="Add servants to your harem by sending /protecc <i>character name</i>\n"
                                   "<i>The localization names are based on the Spirit Origin List of Fate/Grand Order "
                                   "NA server and from FGO Wiki for unreleased servants</i>\n"
                                   "<b>The only exception is Altria, here reported as Artoria</b>\n"
                                   "/listservants to view your harem\n"
                                   "/groupservants view this group's top harems\n"
                                   "/changetime <i>number</i> to change after how many messages waifus will spawn again"
                                   " (only administrators)\n<i>The new time must be 100 &lt;= new time &lt;= 10000</i>\n"
                              , parse_mode='HTML')


# COMMANDS INTERACTION WITH THE BOT
#############################################

# Protecc servant
def proteccservant(update: Update, context: CallbackContext):
    # Get the message reference data
    # Check if the message is edited
    if update.edited_message:
        ID_Supergroup = str(update.edited_message.chat.id)
        ID_User = int(update.edited_message.from_user.id)
        Username = str(update.edited_message.from_user.username)
        protecc = str(update.edited_message.text).upper()
        ID_Mess = int(update.edited_message.message_id)
    else:
        ID_Supergroup = str(update.message.chat.id)
        ID_User = int(update.message.from_user.id)
        Username = str(update.message.from_user.username)
        protecc = str(update.message.text).upper()
        ID_Mess = int(update.message.message_id)

    # Check if there is an obtainable servant in the group
    mycursor.execute("""SELECT ID_Servant
                        FROM management
                        WHERE ID_Supergroup = %s""",
                     (ID_Supergroup,))
    data = mycursor.fetchone()
    if data[0]:
        # Register the ID_Servant
        ID_Servant = data[0]

        # Remove command from message
        protecc = protecc.partition(' ')[2]

        if protecc:
            # Take the waifu
            # Look for the name in the db
            mycursor.execute("""SELECT Name_Servant
                                        FROM servants
                                        WHERE ID_Servant = %s
                                        """, (ID_Servant,))
            data = mycursor.fetchone()
            original_Servant = str(data[0])
            Servant = str(data[0]).upper()

            # Remove any accented letters from both names
            protecc = unidecode.unidecode(protecc)
            Servant = unidecode.unidecode(Servant)

            # Remove any symbols
            # 1 - Replace the dashes with spaces
            protecc = re.sub('-', ' ', protecc)
            Servant = re.sub('-', ' ', Servant)
            # 1.2 - Replace slashes with spaces
            protecc = re.sub('/', ' ', protecc)
            Servant = re.sub('/', ' ', Servant)
            # 2 - Replace the rest with blanks
            protecc = re.sub('[^a-zA-Z0-9 \n\.]', '', protecc)
            Servant = re.sub('[^a-zA-Z0-9 \n\.]', '', Servant)
            # 3 Multiple spaces
            protecc = re.sub(' +', ' ', protecc)
            Servant = re.sub(' +', ' ', Servant)
                
            # Check if it matches
            if findWholeWord(protecc, Servant):

                # Check if the account is registered in the db
                CheckUser(ID_User, Username)

                # Add the waifu to the user's harem
                # Check if the user has already secured this waifu
                mycursor.execute("""SELECT *
                                    FROM relations
                                    WHERE ID_User= %s AND
                                    ID_Supergroup = %s AND
                                    ID_Servant = %s
                                    """, (ID_User, ID_Supergroup, ID_Servant,))
                data = mycursor.fetchone()
                # if - If it exists add an NP
                # else - If it doesn't exist create the relationship
                if data:
                    mycursor.execute("""UPDATE relations
                                        SET NP = NP + 1
                                        WHERE ID_User= %s AND
                                        ID_Supergroup = %s AND
                                        ID_Servant = %s
                                        """, (ID_User, ID_Supergroup, ID_Servant,))
                else:
                    # Look for the number of close relationship so far from the user
                    mycursor.execute("""SELECT count(*)
                                        FROM relations
                                        WHERE ID_User = %s AND
                                        ID_Supergroup = %s""",
                                     (ID_User, ID_Supergroup,))
                    data = mycursor.fetchone()
                    NUMERO_RELAZIONI = data[0]

                    # Set the data of the new relationship
                    mycursor.execute("INSERT INTO relations(ID_User, ID_Supergroup, ID_Servant, NP, Place) "
                                     "VALUES(%s, %s, %s, 1, %s)",
                                     (ID_User, ID_Supergroup, ID_Servant, NUMERO_RELAZIONI + 1,))

                # Close the game and reset the message timer
                mycursor.execute("""UPDATE management
                                    SET Time_mess = Time_reset,
                                    Started = 0,
                                    ID_Servant = NULL
                                    WHERE ID_Supergroup = %s""",
                                 (ID_Supergroup,))

                # Tell that he managed to get the servant
                context.bot.send_message(chat_id=ID_Supergroup, text="OwO you protecc'd " + original_Servant +
                                                                     ". This servant has been added to your harem.",
                                         reply_to_message_id=ID_Mess)
                return
        # Notice the error and update the group
        update.message.reply_text("rip, that's not quite right...")
        UpdateGroup(ID_Supergroup, context)
    else:
        # Refresh the group data
        UpdateGroup(ID_Supergroup, context)


# List servants
def haremfatewaifugram(update: Update, context: CallbackContext):
    # Take the reference data
    ID_Supergroup = str(update.message.chat.id)
    Supergroup_name = str(update.message.chat.title)
    ID_User = str(update.message.from_user.id)
    ID_Mess = int(update.message.message_id)

    # Refresh the group data
    UpdateGroup(ID_Supergroup, context)

    # Seeking relationships
    mycursor.execute("""SELECT relations.Place, servants.Name_servant, relations.NP 
                        FROM servants, relations
                        WHERE relations.ID_User= %s AND
                        relations.ID_Supergroup = %s AND
                        relations.ID_Servant = servants.ID_Servant
                        ORDER BY Place asc 
                        LIMIT 21""",
                     (ID_User, ID_Supergroup,))
    data = mycursor.fetchall()
    # Formulate the list
    if data:
        i = 0
        Harem = ""
        for row in data:
            i += 1
            Harem = str(Harem + str(row[0]) + ". " + row[1] + " NP" + str(row[2]) + "\n")
            if i == 20:
                break

        # Formulate the rest of the message
        Username = str(update.message.from_user.username)
        Harem = Username + "'s harem in " + Supergroup_name + "\n\n" + Harem

        # Remove previous harem message if it exists
        mycursor.execute("""SELECT Mess_ID_List
                            FROM harem
                            WHERE ID_User = %s AND
                            ID_Supergroup = %s""",
                         (ID_User, ID_Supergroup,))
        data = mycursor.fetchone()
        if data:
            try:
                context.bot.delete_message(ID_Supergroup, message_id=data[0])
            except:
                pass

        # Count how many relationships the user has
        mycursor.execute("""SELECT count(*)
                                FROM servants, relations
                                WHERE relations.ID_User= %s AND
                                relations.ID_Supergroup = %s AND
                                relations.ID_Servant = servants.ID_Servant""",
                         (ID_User, ID_Supergroup,))
        data = mycursor.fetchone()
        NUMERO_RELAZIONI = data[0]

        # If there are more than 20 relationships add buttons, otherwise not
        if NUMERO_RELAZIONI > 20:
            # Create callback buttons
            keyboard = [[InlineKeyboardButton('⏩', callback_data='Next-0')]]
            """keyboard = [[InlineKeyboardButton('⏪', callback_data='Before'),
                         InlineKeyboardButton('⏩', callback_data='Next')]]"""
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            reply_markup = ""

        # Take my favorite Servant
        mycursor.execute("""SELECT PATH_IMG_LOW_RESOLUTION
                            FROM servants, relations, harem
                            WHERE relations.ID_User= %s AND
                            relations.ID_Supergroup = %s AND
                            relations.ID_Servant = servants.ID_Servant AND
                            harem.Favorite_Servant = servants.ID_Servant AND
                            harem.ID_Supergroup = relations.ID_Supergroup AND
                            harem.ID_User = relations.ID_User
                            """,
                         (ID_User, ID_Supergroup,))
        data = mycursor.fetchone()
        # If he doesn't have an established favorite servant get the first one on the list
        if data:
            PATH_IMG = data[0]
        else:
            mycursor.execute("""SELECT PATH_IMG_LOW_RESOLUTION
                                FROM relations, servants 
                                WHERE relations.ID_Supergroup = %s
                                AND relations.ID_User = %s
                                AND relations.ID_Servant = servants.ID_Servant
                                AND relations.Place = 1""",
                             (ID_Supergroup, ID_User,))
            data = mycursor.fetchone()
            PATH_IMG = data[0]

        Mess_ID_List = context.bot.send_document(chat_id=ID_Supergroup, document=open(PATH_IMG, 'rb'),
                                                 reply_markup=reply_markup, caption=Harem, reply_to_message_id=ID_Mess)
        # Insert the Mess_ID of his list in the user data
        # If your message card exists, update it
        # Otherwise create it
        CheckMessages(ID_Supergroup, ID_User, Mess_ID_List.message_id)
        # Update user info (Username)
        CheckUser(ID_User, Username)
    else:
        update.message.reply_text("You haven't protecc'd any servant yet...")


def PageSelection(update: Update, context: CallbackContext):
    # Collect user data
    ID_User = str(update.callback_query.from_user.id)
    ID_Supergroup = str(update.callback_query.message.chat.id)
    Mess_ID = update.callback_query.message.message_id

    # Check if he owns the message
    if VerifyListIdentity(Mess_ID, ID_Supergroup, ID_User):
        # Collect additional data for creating the new message
        Username = str(update.callback_query.from_user.username)
        Supergroup_name = str(update.callback_query.message.chat.title)

        # Collect the callback request
        CallBackRequest = str(update.callback_query.data)
        CallBackRequest = CallBackRequest.split("-")
        Request = str(CallBackRequest[0])
        Page_contents = int(CallBackRequest[1])

        # Verify the request
        if Request == "Before":
            New_Page = Page_contents - 20

        elif Request == "Next":
            New_Page = Page_contents + 20
        else:
            New_Page = 0

        # Request the page and related data from the db
        mycursor.execute("""SELECT relations.Place, servants.Name_servant, relations.NP 
                                    FROM servants, relations
                                    WHERE relations.ID_User= %s AND
                                    relations.ID_Supergroup = %s AND
                                    relations.ID_Servant = servants.ID_Servant AND
                                    relations.Place > %s
                                    ORDER BY Place asc
                                    LIMIT 20""",
                         (ID_User, ID_Supergroup, New_Page,))
        data = mycursor.fetchall()
        # Creation of the message using 20 lines
        if data:
            i = 0
            Harem = ""
            for row in data:
                i += 1
                Harem = str(Harem + str(row[0]) + ". " + row[1] + " NP" + str(row[2]) + "\n")
                if i == 20:
                    break

            # Formulate the message
            Harem = Username + "'s harem in " + Supergroup_name + "\n\n" + Harem

            # Check which buttons need to be implemented for the new message

            # |NEXT| - Count how many relationships the user has from a starting number
            mycursor.execute("""SELECT COUNT(*) 
                                    FROM ( 
                                        SELECT relations.ID_Servant
        	                            FROM servants, relations
        	                            WHERE relations.ID_User= %s AND
        	                            relations.ID_Supergroup = %s AND
        	                            relations.Place > %s + 20 AND
        	                            relations.ID_Servant = servants.ID_Servant
        	                            LIMIT 20
                                        ) AS count""",
                             (ID_User, ID_Supergroup, New_Page,))
            data = mycursor.fetchone()
            AFTER = data[0]

            # |BEFORE| - I count how many relationships the user has from a starting number
            # if - If the page is 0 it means we are at first, so we limit the before
            if New_Page != 0:
                mycursor.execute("""SELECT COUNT(*) 
                                                FROM ( 
                                                    SELECT relations.ID_Servant
                    	                            FROM servants, relations
                    	                            WHERE relations.ID_User= %s AND
                    	                            relations.ID_Supergroup = %s AND
                    	                            relations.Place > %s - 20 AND
                    	                            relations.ID_Servant = servants.ID_Servant
                    	                            LIMIT 20
                                                    ) AS count""",
                                 (ID_User, ID_Supergroup, New_Page,))
                data = mycursor.fetchone()
                BEFORE = data[0]
            else:
                BEFORE = 0

            # Add buttons
            if AFTER and BEFORE:
                keyboard = [[InlineKeyboardButton('⏪', callback_data='Before-' + str(New_Page)),
                             InlineKeyboardButton('⏩', callback_data='Next-' + str(New_Page))]]
            elif AFTER:
                keyboard = [[InlineKeyboardButton('⏩', callback_data='Next-' + str(New_Page))]]
            elif BEFORE:
                keyboard = [[InlineKeyboardButton('⏪', callback_data='Before-' + str(New_Page))]]
            else:
                keyboard = ""
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Send the updated list definitively
            context.bot.edit_message_caption(chat_id=ID_Supergroup, message_id=Mess_ID, reply_markup=reply_markup,
                                             caption=Harem)
    else:
        update.callback_query.answer(text="That's not your harem...")


# Ranking of the 10 users with the most servants
def topfatewaifugram(update: Update, context: CallbackContext):
    # Take the reference data
    ID_Supergroup = str(update.message.chat.id)

    # Refresh the group data
    UpdateGroup(ID_Supergroup, context)

    # Look for all registered users in this group with a harem
    mycursor.execute(
        """SELECT users.Username, sum(relations.NP) as MAX_NP
            FROM relations, users, servants, supergroups
            WHERE relations.ID_Supergroup=%s  
            AND relations.ID_Supergroup = supergroups.ID_Supergroup 
            AND relations.ID_User = users.ID_User 
            AND relations.ID_Servant = servants.ID_Servant 
            GROUP BY relations.ID_User
            ORDER BY MAX_NP DESC
            LIMIT 10""", (ID_Supergroup,))
    data = mycursor.fetchall()

    # Formulate the list
    # Sorted by np
    if data:
        i = 0
        Harem = ""
        for row in data:
            i += 1
            Harem = str(Harem + str(i) + ". " + str(row[0]) + " -- " + str(row[1]) + "\n")

        # Formulate the rest of the message
        Supergroup_name = str(update.message.chat.title)
        Harem = "Top harems in " + Supergroup_name + "\n\n" + Harem

        # Send the message
        update.message.reply_text(Harem)
    else:
        update.message.reply_text("rip, there are no harems in this group...")


# Change spawn time
def changetime(update: Update, context: CallbackContext):
    # Take the reference data
    ID_Supergroup = str(update.message.chat.id)
    ID_User = str(update.message.from_user.id)
    status = context.bot.get_chat_member(ID_Supergroup, ID_User).status

    if status == "administrator" or status == "creator":
        # Take the message
        NewTime = update.message.text
        try:
            # Remove command from message
            NewTime = int(NewTime.partition(' ')[2])
            if 100 <= NewTime <= 10000:
                mycursor.execute("""UPDATE management
                                    SET Time_reset = %s
                                    WHERE ID_Supergroup = %s
                                    """, (NewTime, ID_Supergroup,))
                update.message.reply_text(
                    "Time changed!\nStart from the next every servant will appear after " + str(NewTime) + " messages")
            else:
                update.message.reply_text("rip, that's not quite right...\nThe new time must be 100 <= new time <= "
                                          "10000")
        except:
            update.message.reply_text("rip, that's not quite right...\nCheck how use correctly the command again")
    else:
        update.message.reply_text("rip, you don't have the rights to use this command...")


# Swap servants
def tradeservant(update: Update, context: CallbackContext):
    # Take the reference data
    ID_Supergroup = str(update.message.chat.id)
    ID_User_1 = int(update.message.from_user.id)

    # Refresh the group data
    UpdateGroup(ID_Supergroup, context)

    # Take the message
    NewTrade = update.message.text

    # Remove command from message
    NewTrade = str(NewTrade.partition(' ')[2])

    # Check if there is any text after the command
    if NewTrade:
        # Check if the command is the reply to another message
        try:
            ID_Mess = int(update.message.reply_to_message.message_id)
        except:
            ID_Mess = ""

        if ID_Mess:
            if not update.message.reply_to_message.from_user.is_bot:

                # Verify that the user did not reply to himself
                ID_User_2 = int(update.message.reply_to_message.from_user.id)

                if ID_User_1 != ID_User_2:
                    # Divide the two numbers in the list
                    NewTrade = NewTrade.split(" ")

                    # Except the 2 trade numbers
                    Trade_1 = ""
                    Trade_2 = ""
                    try:
                        Trade_1 = int(NewTrade[0])
                        Trade_2 = int(NewTrade[1])
                    except:
                        pass

                    # Verify that both numbers have been given
                    if Trade_1 and Trade_2:

                        # Check if there is another trade and delete it if necessary
                        mycursor.execute("""SELECT Mess_ID_Trade
                                            FROM trades
                                            WHERE ID_User_1 = %s AND
                                            ID_Supergroup = %s""",
                                         (ID_User_1, ID_Supergroup))
                        data = mycursor.fetchone()
                        if data:
                            try:
                                # Remove the old trade
                                mycursor.execute("""DELETE FROM trades WHERE ID_Supergroup = %s AND ID_User_1=%s""",
                                                 (ID_Supergroup,
                                                  ID_User_1,))

                                # Delete the old message
                                context.bot.delete_message(ID_Supergroup, message_id=data[0])
                            except:
                                pass

                        # Verify the identity of the 2 servants
                        # If they do not exist send the notice
                        mycursor.execute("""SELECT Name_Servant
                                                                        FROM relations, servants 
                                                                        WHERE relations.ID_Supergroup = %s
                                                                        AND relations.ID_User = %s
                                                                        AND relations.ID_Servant = servants.ID_Servant
                                                                        AND relations.Place = %s""",
                                         (ID_Supergroup, ID_User_1, Trade_1,))
                        data = mycursor.fetchone()
                        if data:
                            Name_Servant_1 = data[0]
                            mycursor.execute("""SELECT Name_Servant
                                                                            FROM relations, servants 
                                                                            WHERE relations.ID_Supergroup = %s
                                                                            AND relations.ID_User = %s
                                                                            AND relations.ID_Servant = servants.ID_Servant
                                                                            AND relations.Place = %s""",
                                             (ID_Supergroup, ID_User_2, Trade_2,))
                            data = mycursor.fetchone()
                            if data:
                                Name_Servant_2 = data[0]

                                # Create the buttons
                                keyboard = [[InlineKeyboardButton('No :(', callback_data='No@FateWaifugram_Bot'),
                                             InlineKeyboardButton('Yes!', callback_data='Yes@FateWaifugram_Bot')],
                                            [InlineKeyboardButton('Quit', callback_data='Quit@FateWaifugram_Bot')]]
                                reply_markup = InlineKeyboardMarkup(keyboard)

                                # Retrieve the Username for creating the message
                                Username_1 = str(update.message.from_user.username)
                                Username_2 = str(update.message.reply_to_message.from_user.username)

                                # Send the message
                                Mess_ID_Trade = context.bot.send_message(
                                    text="You've been offered a servant trade!\n\n" +
                                         Username_1 + " wants your servant " + Name_Servant_2 +
                                         "\nIn return, they will give you " + Name_Servant_1 +
                                         "\nDo you accept, " + Username_2 + "?"
                                    , chat_id=ID_Supergroup,
                                    reply_to_message_id=ID_Mess,
                                    reply_markup=reply_markup)

                                # Type the data in the db
                                mycursor.execute(
                                    "INSERT INTO trades"
                                    "(ID_Supergroup, Mess_ID_Trade, ID_User_1, ID_User_2, Trade_1, Trade_2)"
                                    "VALUES(%s,%s,%s,%s,%s,%s)",
                                    (ID_Supergroup, Mess_ID_Trade.message_id, ID_User_1, ID_User_2, Trade_1, Trade_2))

                                return
                            else:
                                update.message.reply_text(
                                    "Looks like that person doesn't have any servant to trade with...")
                                return
                        else:
                            update.message.reply_text(
                                "Looks like that you don't have any servant to trade with...")
                            return
    # Warn about the error
    update.message.reply_text("kek that doesn't look right. <b>Reply</b> to someone like this:\n\n"
                              "<b>/tradeservant</b> <i>{servant number you want to give} {servant number "
                              "you want to take}</i>\n\n"
                              "e.g. <b>/tradeservant 12 8</b>", parse_mode='HTML')


def checktradeservant(update: Update, context: CallbackContext):
    # Collect user data
    ID_User = int(update.callback_query.from_user.id)
    ID_Supergroup = str(update.callback_query.message.chat.id)
    Mess_ID_Trade = update.callback_query.message.message_id
    CallBackRequest = str(update.callback_query.data)

    # Check that the button was pressed by
    # - creator
    # - participant
    # - external
    mycursor.execute("""SELECT ID_User_1, ID_User_2
                        FROM trades
                        WHERE ID_Supergroup = %s AND Mess_ID_Trade = %s""", (ID_Supergroup, Mess_ID_Trade,))
    data = mycursor.fetchone()
    ID_User_Trade = [data[0], data[1]]
    if ID_User != ID_User_Trade[0] and ID_User != ID_User_Trade[1]:
        # Warn that it is not part of the exchange
        update.callback_query.answer(text="That's not your trade...")
    elif ID_User == ID_User_Trade[0]:
        if CallBackRequest == "Quit@FateWaifugram_Bot":
            # Remove the old trade
            mycursor.execute("""DELETE FROM trades WHERE ID_Supergroup = %s AND Mess_ID_Trade=%s""", (ID_Supergroup,
                                                                                                      Mess_ID_Trade,))
            # Delete the old message
            try:
                context.bot.delete_message(ID_Supergroup, message_id=Mess_ID_Trade)
            except:
                pass

            # Cancel the exchange
        else:
            update.callback_query.answer(text="You can't reply your trade...")
            # Warn that he cannot reply to his own exchange
    else:
        # Collect the callback request
        if CallBackRequest == "Yes@FateWaifugram_Bot":
            # Trade	
            # 1 - Remove the respective servants

            # 1.1 - Retrieving the places of the servants
            mycursor.execute("""SELECT Trade_1, Trade_2 
                                FROM trades
                                WHERE ID_Supergroup = %s AND Mess_ID_Trade = %s""",
                             (ID_Supergroup, Mess_ID_Trade,))
            data = mycursor.fetchone()
            Trade = [data[0], data[1]]
            NP = []
            ID_Servant_Trade = []
            i = 0

            for Place in Trade:
                # Check if both servants are available
                mycursor.execute("""SELECT NP, ID_Servant
                                    FROM relations
                                    WHERE ID_Supergroup = %s AND ID_User = %s 
                                    AND Place = %s""", (ID_Supergroup, ID_User_Trade[i], Place))

                data = mycursor.fetchone()
                if data:
                    NP.append(data[0])
                    ID_Servant_Trade.append(data[1])
                else:
                    # Cancel the exchange and notice that one of the servants is no longer available
                    return
                i += 1
            # Down with the NP of the servants involved
            # If they reach zero they are deleted
            i = 0
            for Place in Trade:
                if NP[i] == 1:
                    # Remove the Servant
                    mycursor.execute("""DELETE FROM relations 
                                        WHERE ID_Supergroup = %s 
                                        AND ID_User = %s
                                        AND Place = %s""", (ID_Supergroup, ID_User_Trade[i], Place,))
                    # Down with the place of the next ones
                    mycursor.execute("""UPDATE relations
                                        SET Place = Place - 1
                                        WHERE ID_Supergroup = %s AND
                                        ID_User = %s AND
                                        Place > %s""", (ID_Supergroup, ID_User_Trade[i], Place,))
                else:
                    # Down with NP
                    mycursor.execute("""UPDATE relations
                                        SET NP = NP - 1
                                        WHERE ID_User= %s AND
                                        ID_Supergroup = %s AND
                                        Place = %s
                                        """, (ID_User_Trade[i], ID_Supergroup, Place,))
                i += 1
            # Add the servant
            # If they already have the servant I increase the NP otherwise I add with insert
            i = 1
            for ID_Servant in ID_Servant_Trade:
                # Verify waifu ID
                # Add the waifu to the user's harem
                # Check if the user has already secured this waifu
                mycursor.execute("""SELECT *
                                    FROM relations
                                    WHERE ID_User= %s AND
                                    ID_Supergroup = %s AND
                                    ID_Servant = %s
                                                    """, (ID_User_Trade[i], ID_Supergroup, ID_Servant,))
                data = mycursor.fetchone()
                # if - If it exists add an NP
                # else - If it doesn't exist I create the relationship
                if data:
                    mycursor.execute("""UPDATE relations
                                                        SET NP = NP + 1
                                                        WHERE ID_User= %s AND
                                                        ID_Supergroup = %s AND
                                                        ID_Servant = %s
                                                        """, (ID_User_Trade[i], ID_Supergroup, ID_Servant,))
                else:
                    # Look for the number of close relationship so far from the user
                    mycursor.execute("""SELECT count(*)
                                                        FROM relations
                                                        WHERE ID_User = %s AND
                                                        ID_Supergroup = %s""",
                                     (ID_User_Trade[i], ID_Supergroup,))
                    data = mycursor.fetchone()
                    NUMERO_RELAZIONI = data[0]

                    # Set the data of the new relationship
                    mycursor.execute("INSERT INTO relations(ID_User, ID_Supergroup, ID_Servant, NP, Place) "
                                     "VALUES(%s, %s, %s, 1, %s)",
                                     (ID_User_Trade[i], ID_Supergroup, ID_Servant, NUMERO_RELAZIONI + 1,))
                i -= 1
            Username = []
            Name_Servant = []
            i = 0

            # Remove the trade
            mycursor.execute("""DELETE FROM trades WHERE ID_Supergroup = %s AND Mess_ID_Trade=%s""", (ID_Supergroup,
                                                                                                      Mess_ID_Trade,))

            for ID_User in ID_User_Trade:
                mycursor.execute("""SELECT Username
                                        FROM users
                                        WHERE ID_User = %s""", (ID_User,))
                data = mycursor.fetchone()
                Username.append(data[0])
                mycursor.execute("""SELECT Name_Servant
                                        FROM servants
                                        WHERE ID_Servant = %s""", (ID_Servant_Trade[i],))
                data = mycursor.fetchone()
                Name_Servant.append(data[0])
                i += 1
            # Send message confirming the trade
            update.callback_query.message.edit_text("OwO the trade is complete!\n\n" + Username[0] + " gave " +
                                                    Name_Servant[0] + " to " + Username[1] + "\nand\n" +
                                                    Username[1] + " gave " +
                                                    Name_Servant[1] + " to " + Username[0])
        elif CallBackRequest == "No@FateWaifugram_Bot":
            # Remove the trade
            mycursor.execute("""DELETE FROM trades WHERE ID_Supergroup = %s AND Mess_ID_Trade=%s""", (ID_Supergroup,
                                                                                                      Mess_ID_Trade,))
            Username = []
            for ID_User in ID_User_Trade:
                mycursor.execute("""SELECT Username
                                        FROM users
                                        WHERE ID_User = %s""", (ID_User,))
                data = mycursor.fetchone()
                Username.append(data[0])

            update.callback_query.message.edit_text(
                "Ah rip, " + Username[1] + " rejected the trade with " + Username[0])
            # Cancel the exchange
        elif CallBackRequest == "Quit@FateWaifugram_Bot":
            update.callback_query.answer(text="You can't press this...")


# Choose your favorite servant to keep on the harem cover
def favoriteservant(update: Update, context: CallbackContext):
    # Take the reference data
    ID_Supergroup = str(update.message.chat.id)
    ID_User = str(update.message.from_user.id)

    # Refresh the group data
    UpdateGroup(ID_Supergroup, context)

    # Remove the command
    Favorite_Servant = update.message.text
    try:
        # Remove command from message
        Favorite_Servant = int(Favorite_Servant.partition(' ')[2])

        # Look for the servant via the given place
        mycursor.execute("""SELECT servants.ID_Servant, servants.Name_Servant
                            FROM relations, servants 
                            WHERE relations.ID_Supergroup = %s
                            AND relations.ID_User = %s
                            AND relations.ID_Servant = servants.ID_Servant
                            AND relations.Place = %s""",
                         (ID_Supergroup, ID_User, Favorite_Servant,))
        data = mycursor.fetchone()
        if data:
            ID_Favorite_Servant = data[0]
            Name_Favorite_Servant = data[1]

            # Insert the new favorite servant into the table
            mycursor.execute("""UPDATE harem 
                                        SET Favorite_Servant = %s
                                        WHERE ID_Supergroup = %s
                                        AND ID_User = %s""",
                             (ID_Favorite_Servant, ID_Supergroup, ID_User,))

            update.message.reply_text("I've set " + Name_Favorite_Servant + " as your favorite Servant!")
        else:
            update.message.reply_text("rip, there's no servant in your list with this number place...")
    except:
        update.message.reply_text("rip, that's not quite right...\n<b>/favoriteservant</b> <i>{servant number you want"
                                  " as favorite}</i>", parse_mode='HTML')


# CHECK AREA
# ---------------------------------------------
def VerifyListIdentity(Mess_ID_List, ID_Supergroup, ID_User):
    #  Search master in DB
    mycursor.execute(
        """SELECT ID_User 
           FROM harem 
           WHERE Mess_ID_List = %s AND 
           ID_Supergroup=%s""", (Mess_ID_List, ID_Supergroup,))
    data = mycursor.fetchone()
    if data:
        Original_ID_User = data[0]
        if int(ID_User) == int(Original_ID_User):
            return True
        else:
            return False


def CheckMessages(ID_Supergroup, ID_User, Mess_ID_List):
    # Enter the Mess_ID of his trade in the user data
    mycursor.execute("SELECT ID_User "
                     "FROM harem "
                     "WHERE ID_User=%s AND ID_Supergroup = %s",
                     (ID_User, ID_Supergroup,))
    data = mycursor.fetchone()
    if data:
        # Update the data
        mycursor.execute("""UPDATE harem
                            SET Mess_ID_List = %s
                            WHERE ID_Supergroup = %s AND
                            ID_User = %s""", (Mess_ID_List,
                                              ID_Supergroup, ID_User,))
    else:
        # Set the data of the new relationship
        mycursor.execute("INSERT INTO harem(ID_Supergroup, ID_User, Mess_ID_List) "
                         "VALUES(%s, %s, %s)",
                         (ID_Supergroup, ID_User, Mess_ID_List))


# Check if the user is registered in the db
# if - If not, register it
# else - Update username if it has changed
def CheckUser(ID_User, Username):
    # Collect user data
    # Search if a user is registered in the db
    mycursor.execute("SELECT ID_User, Username FROM users WHERE ID_User=" + str(ID_User))
    data = mycursor.fetchone()
    if not data:
        mycursor.execute("INSERT INTO users(ID_User, Username) VALUES(%s,%s)", (ID_User, Username))
    else:
        try:
            old_Username = data[1]
            if Username != old_Username:
                mycursor.execute("""UPDATE users
                                            SET Username = %s
                                            WHERE ID_User = %s""",
                                 (Username, ID_User,))
        except:
            pass


def UpdateGroup(ID_Supergroup, context: CallbackContext):
    # Update the number of messages before the next spawn
    mycursor.execute("""SELECT Time_mess, started
                        FROM management
                        WHERE ID_Supergroup = %s""",
                     (ID_Supergroup,))
    data = mycursor.fetchone()
    Time_mess = data[0]
    Started = data[1]

    # Check the message counter before waifu spawns
    if Time_mess == 0:
        if Started:
            mycursor.execute("""UPDATE management
                                SET Time_mess = Time_reset,
                                Started = 0,
                                ID_Servant = NULL
                                WHERE ID_Supergroup = %s""",
                             (ID_Supergroup,))
            context.bot.send_message(chat_id=ID_Supergroup, text="rip, the waifu has run away already...")
        else:
            # Select the maximum value of the servant id
            mycursor.execute("""SELECT ID_Servant 
                                FROM servants
                                ORDER BY ID_Servant desc""")
            data = mycursor.fetchone()
            MAX_SERVANT_ID = int(data[0])

            # Randomly select an id
            ID_SERVANT = random.randrange(1, MAX_SERVANT_ID + 1)

            # Select the servant found
            mycursor.execute("""SELECT ID_Servant, PATH_IMG
                                FROM servants
                                WHERE ID_SERVANT = %s
                                                """, (ID_SERVANT,))
            data = mycursor.fetchone()
            ID_Servant = data[0]
            PATH_IMG = data[1]

            # Register the servant in the group settings and then the game activation
            mycursor.execute("""UPDATE management
                                                SET Time_mess = 25,
                                                Started = 1,
                                                ID_Servant = %s
                                                WHERE ID_Supergroup = %s""",
                             (ID_Servant, ID_Supergroup,))

            # Warn users about the appearance of a waifu
            context.bot.send_photo(chat_id=ID_Supergroup, photo=open(PATH_IMG, 'rb'),
                                   caption="<b>A servant appeared!</b>\nAdd them to your harem by sending "
                                           "/protecc <i>character name</i>\n",
                                   parse_mode='HTML')
    else:
        mycursor.execute("""UPDATE management
                        SET Time_mess = Time_mess - 1
                        WHERE ID_Supergroup = %s""",
                     (ID_Supergroup,))

        
def findWholeWord(protecc, servant):
    for protecc_word in protecc.split(" "):
        for servant_word in servant.split(" "):
            if protecc_word == servant_word:
                return True
    return False


# ---------------------------------------------
# NEW GROUP REGISTRATION
def Welcomechat(update: Update, context: CallbackContext):
    # Take the reference data
    ID_Supergroup = str(update.message.chat.id)
    Supergroup_name = str(update.message.chat.title)
    # Check if the logged in user is the bot
    if update.message.new_chat_members[0].id == context.bot.id:
        NewGroup(ID_Supergroup, Supergroup_name)
        # Send bot information to the group
        update.message.reply_text(text="OwO thanks for adding me. Qt Fate/ waifus will now appear randomly! "
                                       "You can add them to your personal harem by being the first person to guess the "
                                       "character's name!\n"
                                       "Ask /help for all informations!\n"
                                  , parse_mode='HTML')


def NewGroup(ID_Supergroup, Supergroup_name):
    # Check if the group is registered in the db
    mycursor.execute("SELECT ID_Supergroup FROM supergroups WHERE ID_Supergroup=" + str(ID_Supergroup))
    data = mycursor.fetchone()

    # if - If the group is not registered then register
    # else - Waifu spawn counter updated
    if not data:
        mycursor.execute("INSERT INTO supergroups(ID_Supergroup, Supergroup_name) VALUES(%s,%s)",
                         (ID_Supergroup, Supergroup_name))
        mycursor.execute(
            "INSERT INTO management(ID_Supergroup, Time_mess, Time_reset, Started) VALUES (%s,%s,%s,%s)",
            (ID_Supergroup, 1, 100, 0))



#############################################

def main():
    dp = updater.dispatcher
    
    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("protecc", proteccservant, Filters.group))
    dp.add_handler(CommandHandler("groupservants", topfatewaifugram, Filters.group & Filters.update.message))
    dp.add_handler(CommandHandler("changetime", changetime, Filters.group & Filters.update.message))
    dp.add_handler(CommandHandler("tradeservant", tradeservant, Filters.group & Filters.update.message))
    dp.add_handler(CommandHandler("favoriteservant", favoriteservant, Filters.group & Filters.update.message))
    dp.add_handler(CallbackQueryHandler(checktradeservant, pattern="No@FateWaifugram_Bot"))
    dp.add_handler(CallbackQueryHandler(checktradeservant, pattern="Yes@FateWaifugram_Bot"))
    dp.add_handler(CallbackQueryHandler(checktradeservant, pattern="Quit@FateWaifugram_Bot"))

    # Servants list management
    dp.add_handler(CommandHandler("listservants", haremfatewaifugram, Filters.group & Filters.update.message))
    dp.add_handler(CallbackQueryHandler(PageSelection))

    # Group registration
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, callback=Welcomechat))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.group & Filters.update.message, callback=maindef))
    dp.add_handler(MessageHandler(Filters.private & Filters.update.message, callback=private))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
