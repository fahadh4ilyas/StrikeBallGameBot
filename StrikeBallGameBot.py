#!/usr/bin/env python
# -*- coding: utf-8 -*-

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, Filters
from telegram.error import (TelegramError, Unauthorized, BadRequest, NetworkError)
import logging, argparse, time, random

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger_formatter = logging.Formatter('%(levelname)s [%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

file_handler = logging.FileHandler('./StrikeBallGame.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logger_formatter)
logger.addHandler(file_handler)

def start(bot,update):
    """Welcome Message Bot."""
    if update.message.chat.type == 'private':
        logger.info("{} mengirim perintah /start di pesan pribadi".format(update.message.from_user.name))
        who = update.message.from_user.username
    else:
        logger.info("{} mengirim perintah /start di grup {}".format(update.message.from_user.name,update.message.chat.title))
        who = 'SEMUANYA'
    bot.send_chat_action(update.message.chat_id,'typing')
    bot.send_message(update.message.chat_id,'''HALO, {}! 👋
Selamat Datang di Strike Ball Game Bot! 🎉

Strike Ball Game adalah gim tebak angka di mana kamu dan temanmu saling bergantian menebak angka rahasia lawanmu.

Jangan lupa untuk add Bot ini sebagai temanmu dengan mengirim pesan ke Bot ini!

Ketik /help untuk mengetahui cara bermain ❓'''.format(who),disable_notification=True)
    
def get_help(bot,update):
    """Getting Help from Bot."""
    if update.message.chat.type == 'private':
        logger.info("{} mengirim perintah /help di pesan pribadi".format(update.message.from_user.name))
    else:
        logger.info("{} mengirim perintah /help di grup {}".format(update.message.from_user.name,update.message.chat.title))
    bot.send_chat_action(update.message.chat_id,'typing')
    bot.send_message(update.message.chat_id,'''📖 Berikut adalah tata cara gim Strike Ball:
1. Mulai permainan dengan mengirim /mulai. Cukup satu orang saja ya! ☝
2. Orang yang memulai akan diminta untuk memilih berapa digit angka yang akan ditebak. 🖐
3. Pemain yang ingin bergabung bisa mengirim /gabung untuk ikut bermain gim. 🙋‍♂️🙋‍
4. Setiap pemain yang bergabung, akan dikirimkan pesan pribadi oleh Bot. 🤖
5. Balas pesan Bot dengan "/angkaku (angka_rahasiamu)" untuk menentukan angka rahasiamu. 🤐
6. Diberikan waktu selama 120 detik untuk bergabung dalam gim. ⏳
7. Untuk menambah waktu untuk bergabung, kirim /extend untuk menambah waktu bergabung. ⌛
8. Untuk langsung memulai gim, kirim /forcestart. ▶
9. Secara bergantian, pemain akan menebak angka rahasia pemain lain. 🤔
10. Ketik "/tebak (angka_tebakanmu)" untuk menebak angka rahasia lawanmu. 👍
11. Pemenangnya adalah yang berhasil terlebih dahulu menebak angka lawan. 🏆
12. Ketik "/stop" untuk menghentikan permainan di tengah permainan.

Contoh Permainan: 🎯
Misal angka rahasia lawanmu adalah 1495. Dan kamu menebak 1590. Maka, Bot akan menjawab "2 Strike 1 Ball".

Strike artinya angka tebakanmu benar dan posisinya benar. Ball artinya angka tebakanmu benar tapi posisinya salah.

Kamu mendapat 2 Strike karena ada 2 angka yang benar dan posisinya benar yaitu angka 1 dan 9. Dan kamu mendapat 1 Ball karena ada 1 angka yang benar tapi posisinya salah yaitu angka 5.''',disable_notification=True)

def get_guess(num1,num2,digit):
    if not num2.isdigit():
        return 'Ketik "/tebak (angka_tebakanmu)" untuk menebak!'
    if len(num1) != len(num2):
        return 'Masukkan angka tebakan  berupa angka dengan {} digit berbeda'.format(digit)
    
    Strike = [num1[i]==num2[i] for i in range(digit)].count(True)
    Ball = len([num2[i] for i in range(digit) if num2[i] in num1]) - Strike
    
    if Strike == digit:
        return True
    
    return '{} Strike {} Ball'.format(Strike,Ball)
    
def mulai(bot,update,chat_data):
    """Start The Game"""
    logger.info("{} mengirim perintah /mulai di grup {}".format(update.message.from_user.name,update.message.chat.title))
    bot.send_chat_action(update.message.chat_id,'typing')
    if chat_data.get('phase') != None:
        bot.send_message(update.message.chat_id,"Permainan Sudah Dimulai!",reply_to_message_id=update.message.message_id,disable_notification=True)
    else:
        chat_data['phase'] = ['digit']
        chat_data['selector'] = update.message.from_user.id
        chat_data['numbers'] = {}
        chat_data['winner'] = []
        keyboard = [[InlineKeyboardButton("4 digit", callback_data='4'),InlineKeyboardButton("5 digit", callback_data='5')],
                    [InlineKeyboardButton("6 digit", callback_data='6'),InlineKeyboardButton("7 digit", callback_data='7')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        bot.send_message(update.message.chat_id,"Berapa digit angka yang ditebak?",
                         reply_to_message_id=update.message.message_id,
                         reply_markup=reply_markup,disable_notification=True)
        
def digit_choose(bot,update,job_queue,chat_data):
    """Choose Digit to Play"""
    query = update.callback_query
    logger.info("{} memilih banyak digit di grup {}".format(query.from_user.name,query.message.chat.title))
    if chat_data.get('phase') != None:
        if chat_data.get('phase')[0] == 'digit' and chat_data['selector'] == query.from_user.id:
            chat_data['phase'][0] = 'join'
            chat_data['digit'] = int(query.data)
            bot.edit_message_text('Banyak digit yang dipilih: '+query.data,query.message.chat_id,query.message.message_id)
            bot.send_chat_action(query.message.chat_id,'typing')
            bot.send_message(query.message.chat_id,"Silakan kirim perintah /gabung untuk ikut bermain!",disable_notification=True)
            job = job_queue.run_repeating(game_start, 30, context=[30,query,chat_data])
            chat_data['job'] = job
        
def game_start(bot,job):
    times = [30,60,90]
    if job.context[0] in times:
        bot.send_chat_action(job.context[1].message.chat_id,'typing')
        bot.send_message(job.context[1].message.chat_id,"Tersisa {} detik untuk bergabung dalam permainan.".format(120-job.context[0]),
                         disable_notification=True)
        job.context[0] += 30
    else:
        job.context[-1]['phase'][0] = 'started'
        job.schedule_removal()
        del job.context[-1]['job']
        start_game(bot,job.context[-2],job.context[-1])

def extend(bot,update,job_queue,chat_data):
    """Extend Time to Join Game"""
    logger.info("{} mengirim perintah /extend di grup {}".format(update.message.from_user.name,update.message.chat.title))
    if chat_data.get('job'):
        chat_data['job'].schedule_removal()
        bot.send_chat_action(update.message.chat_id,'typing')
        bot.send_message(update.message.chat_id,"Waktu untuk bergabung diperpanjang menjadi 120 detik.",disable_notification=True)
        del chat_data['job']
        job = job_queue.run_repeating(game_start, 30, context=[30,update,chat_data])
        chat_data['job'] = job
        
def gabung(bot,update,chat_data,user_data):
    """User Join The Game"""
    logger.info("{} mengirim perintah /gabung di grup {}".format(update.message.from_user.name,update.message.chat.title))
    if chat_data.get('phase') != None:
        if chat_data['phase'][0] == 'join' and update.message.from_user.id not in chat_data['numbers']:
            if user_data.get('groups'):
                if update.message.chat_id not in user_data['groups']:
                    user_data['groups'] += [[update.message.chat_id,update.message.chat.title,chat_data['phase'],chat_data['digit']]]
                    bot.send_chat_action(update.message.from_user.id,'typing')
                    bot.send_message(update.message.from_user.id,'Ketik "/angkaku (angka_rahasiamu)" untuk menentukan angka rahasiamu.')
            else:
                user_data['groups'] = [[update.message.chat_id,update.message.chat.title,chat_data['phase'],chat_data['digit']]]
                bot.send_chat_action(update.message.from_user.id,'typing')
                bot.send_message(update.message.from_user.id,'Ketik "/angkaku (angka_rahasiamu)" untuk menentukan angka rahasiamu.')
            if user_data.get('numbers'):
                if update.message.chat_id not in user_data['numbers'] or user_data['numbers'][update.message.chat_id][1]:
                    user_data['numbers'][update.message.chat_id] = [None,False,'']
                chat_data['numbers'][update.message.from_user.id] = user_data['numbers'][update.message.chat_id]
            else:
                user_data['numbers'] = {update.message.chat_id:[None,False,'']}
                chat_data['numbers'][update.message.from_user.id] = user_data['numbers'][update.message.chat_id]
        elif not chat_data['numbers'][update.message.from_user.id][1]:
            bot.send_chat_action(update.message.from_user.id,'typing')
            bot.send_message(update.message.from_user.id,'Ketik "/angkaku (angka_rahasiamu)" untuk menentukan angka rahasiamu.')
        elif chat_data['numbers'][update.message.from_user.id][1]:
            bot.send_chat_action(update.message.chat_id,'typing')
            bot.send_message(update.message.chat_id,"Kamu sudah bergabung dalam permainan.",reply_to_message_id=update.message.message_id)

def angkaku(bot, update, args, user_data):
    """User Send Number to Bot"""
    logger.info("{} mengirim perintah /angkaku ".format(update.message.from_user.name)+' '.join(args))
    if user_data.get('groups') not in [None,[]]:
        while user_data['groups'][0][2][0] != 'join':
            del user_data['groups'][0]
            if user_data['groups'] == []:
                bot.send_chat_action(update.message.chat_id,'typing')
                bot.send_message(update.message.chat_id,"Kamu tidak sedang mengikuti permainan apapun.")
                return
        
        group_id = user_data['groups'][0][0]
        group_name = user_data['groups'][0][1]
        group_digit = user_data['groups'][0][3]
        
        if args[0].isdigit() and len(list(set(args[0]))) == group_digit:
            user_data['numbers'][group_id][0] = args[0]
            user_data['numbers'][group_id][1] = True
            bot.send_chat_action(update.message.chat_id,'typing')
            bot.send_message(update.message.chat_id,"Angka yang kamu pilih adalah:\n"+args[0]+"\nuntuk permainan dalam grup:\n"+group_name)
            bot.send_chat_action(group_id,'typing')
            bot.send_message(group_id,update.message.from_user.mention_markdown()+' telah bergabung dalam permainan.',disable_notification=True)
            user_data['numbers'][group_id][2] = update.message.from_user.mention_markdown()
            del user_data['groups'][0]
        else:
            bot.send_chat_action(update.message.chat_id,'typing')
            bot.send_message(update.message.chat_id,'Angka rahasiamu harus berupa angka '+str(group_digit)+' digit yang berbeda.\n\nKetik "/angkaku (angka_rahasiamu)" untuk menentukan angka rahasiamu.',reply_to_message_id=update.message.message_id)
    else:
        bot.send_chat_action(update.message.chat_id,'typing')
        bot.send_message(update.message.chat_id,"Kamu tidak sedang mengikuti permainan apapun.")

def forcestart(bot,update,chat_data):
    """Force Start The Game"""
    logger.info("{} mengirim perintah /forcestart di grup {}".format(update.message.from_user.name,update.message.chat.title))
    if chat_data.get('phase') != None:
        chat_data['phase'][0] = 'started'
        if chat_data.get('job'):
            chat_data['job'].schedule_removal()
            del chat_data['job']
        start_game(bot,update,chat_data)
    else:
        bot.send_chat_action(update.message.chat_id,'typing')
        bot.send_message(update.message.chat_id,'Permainan belum dimulai!',reply_to_message_id=update.message.message_id,disable_notification=True)
    
def forcestop(bot,update,chat_data):
    """Force Stop The Game"""
    logger.info("{} mengirim perintah /stop di grup {}".format(update.message.from_user.name,update.message.chat.title))
    if chat_data.get('phase') != None:
        bot.send_chat_action(update.message.chat_id,'typing')
        bot.send_message(update.message.chat_id,'==PERMAINAN DIHENTIKAN==',disable_notification=True)
        stop_game(chat_data)
    else:
        bot.send_chat_action(update.message.chat_id,'typing')
        bot.send_message(update.message.chat_id,'Permainan belum dimulai!',reply_to_message_id=update.message.message_id,disable_notification=True)
    
def start_game(bot,update,chat_data):
    """Start Guessing Game"""
    if chat_data.get('phase') != None:
        if chat_data['phase'][0] == 'started' and len([i for i in chat_data['numbers'] if chat_data['numbers'][i][1]]) >= 2:
            starter = '==💥PERMAINAN DIMULAI💥==\n\nDaftar Pemain:\n'
            player_name = '\n'.join([chat_data['numbers'][i][2] for i in chat_data['numbers'] if chat_data['numbers'][i][1]])
            player_list = [(i,chat_data['numbers'][i][2]) for i in chat_data['numbers']]
            random.shuffle(player_list)
            starter += player_name
            chat_data['turn'] = list(zip(player_list,player_list[1:]+player_list[:1]))
            chat_data['count'] = 0
            chat_data['round'] = 1
            bot.send_chat_action(update.message.chat_id,'typing')
            bot.send_message(update.message.chat_id,starter,disable_notification=True)
            time.sleep(1)
            bot.send_chat_action(update.message.chat_id,'typing')
            bot.send_message(update.message.chat_id,'==Round {}=='.format(chat_data['round']),disable_notification=True)
            time.sleep(1)
            bot.send_chat_action(update.message.chat_id,'typing')
            bot.send_message(update.message.chat_id,'Untuk {},\nSilakan menebak angka {}.\nKetik "/tebak (angka_tebakanmu)" untuk menebak!'.format(chat_data['turn'][chat_data['count']][0][1],chat_data['turn'][chat_data['count']][1][1]),disable_notification=True)
        elif len([i for i in chat_data['numbers'] if chat_data['numbers'][i][1]]) < 2:
            bot.send_chat_action(update.message.chat_id,'typing')
            bot.send_message(update.message.chat_id,'Maaf! Jumlah pemain kurang dari dua orang.\n\n==PERMAINAN DIHENTIKAN==',disable_notification=True)
            stop_game(chat_data)
            
def tebak(bot,update,args,chat_data):
    """User Menebak Angka"""
    logger.info("{} mengirim perintah /tebak {} di grup {}".format(update.message.from_user.name,' '.join(args),update.message.chat.title))
    if chat_data.get('phase') != None:
        if chat_data['phase'][0] == 'started':
            if update.message.from_user.id == chat_data['turn'][chat_data['count']][0][0]:
                if args[0].isdigit():
                    penebak = chat_data['turn'][chat_data['count']][0][0]
                    ditebak = chat_data['turn'][chat_data['count']][1][0]
                    tebakan = get_guess(chat_data['numbers'][ditebak][0],args[0],chat_data['digit'])
                    if tebakan == True:
                        chat_data['winner'] += [(chat_data['numbers'][penebak][2],chat_data['round'])]
                        bot.send_chat_action(update.message.chat_id,'typing')
                        bot.send_message(update.message.chat_id,'Selamat!🎉\nKamu benar menebak setelah {} tebakan'.format(chat_data['round']),reply_to_message_id=update.message.message_id,disable_notification=True)
                        del chat_data['turn'][chat_data['count']]
                        if len(chat_data['turn']) == 0:
                            winner = '==🔚PERMAINAN SELESAI🔚==\n\nHasil Permainan:'
                            for i in range(len(chat_data['winner'])):
                                temp = chat_data['winner'][i]
                                if i == 0:
                                    winner += '\n1. {}: {} tebakan 🥇'.format(temp[0],temp[1])
                                elif i == 1:
                                    winner += '\n2. {}: {} tebakan 🥈'.format(temp[0],temp[1])
                                elif i == 2:
                                    winner += '\n3. {}: {} tebakan 🥉'.format(temp[0],temp[1])
                                else:
                                    winner += '\n{}. {}: {} tebakan'.format(i+1,temp[0],temp[1])
                            bot.send_chat_action(update.message.chat_id,'typing')
                            bot.send_message(update.message.chat_id,winner,disable_notification=True)
                            stop_game(chat_data)
                        else:
                            if len(chat_data['turn']) == chat_data['count']:
                                chat_data['count'] = 0
                                chat_data['round'] += 1
                                bot.send_chat_action(update.message.chat_id,'typing')
                                bot.send_message(update.message.chat_id,'==Round {}=='.format(chat_data['round']),disable_notification=True)
                                time.sleep(1)
                            bot.send_chat_action(update.message.chat_id,'typing')
                            bot.send_message(update.message.chat_id,'Untuk {},\nSilakan menebak angka {}.\nKetik "/tebak (angka_tebakanmu)" untuk menebak!'.format(chat_data['turn'][chat_data['count']][0][1],chat_data['turn'][chat_data['count']][1][1]),disable_notification=True)
                    else:
                        while 'Strike' not in tebakan:
                            bot.send_chat_action(update.message.chat_id,'typing')
                            bot.send_message(update.message.chat_id,tebakan,reply_to_message_id=update.message.message_id,disable_notification=True)
                        bot.send_chat_action(update.message.chat_id,'typing')
                        bot.send_message(update.message.chat_id,tebakan,reply_to_message_id=update.message.message_id,disable_notification=True)
                        chat_data['count'] = (chat_data['count']+1)%(len(chat_data['turn']))
                        if chat_data['count'] == 0:
                            chat_data['round'] += 1
                            bot.send_chat_action(update.message.chat_id,'typing')
                            bot.send_message(update.message.chat_id,'==Round {}=='.format(chat_data['round']),disable_notification=True)
                            time.sleep(1)
                        bot.send_chat_action(update.message.chat_id,'typing')
                        bot.send_message(update.message.chat_id,'Untuk {},\nSilakan menebak angka {}.\nKetik "/tebak (angka_tebakanmu)" untuk menebak!'.format(chat_data['turn'][chat_data['count']][0][1],chat_data['turn'][chat_data['count']][1][1]),disable_notification=True)

def stop_game(chat_data):
    if chat_data.get('job'):
        chat_data['job'].schedule_removal()
    chat_data.clear()
    
def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, error)
    try:
        raise error
    except (TimedOut, NetworkError, BadRequest):
        bot.send_chat_action(update.message.chat_id,'typing')
        bot.send_message(update.message.chat_id,'Mohon kirim ulang pesan anda!\nJika tidak berhasil, ketik /stop untuk menghentikan permainan',reply_to_message_id=update.message.message_id,disable_notification=True)
    except Unauthorized:
        bot.send_chat_action(update.message.chat_id,'typing')
        bot.send_message(update.message.chat_id,'Kamu belum berteman dengan Bot. Silakan kirim pesan pribadi ke Bot.',reply_to_message_id=update.message.message_id,disable_notification=True)
    except BadRequest:
        bot.send_chat_action(update.message.chat_id,'typing')
        bot.send_message(update.message.chat_id,'Periksa kembali pesan yang kamu kirim ya!',reply_to_message_id=update.message.message_id,disable_notification=True)
    except TelegramError:
        pass

def main(TOKEN):
    """Run Bot."""
    updater = Updater(TOKEN)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start",start))
    dp.add_handler(CommandHandler("help",get_help))
    dp.add_handler(CommandHandler("mulai",mulai,filters=Filters.group,pass_chat_data=True))
    dp.add_handler(CallbackQueryHandler(digit_choose,pass_job_queue=True,pass_chat_data=True))
    dp.add_handler(CommandHandler("extend",extend,filters=Filters.group,pass_job_queue=True,pass_chat_data=True))
    dp.add_handler(CommandHandler("gabung",gabung,filters=Filters.group,pass_chat_data=True,pass_user_data=True))
    dp.add_handler(CommandHandler("angkaku",angkaku,filters=Filters.private,pass_args=True,pass_user_data=True))
    dp.add_handler(CommandHandler("forcestart",forcestart,filters=Filters.group,pass_chat_data=True))
    dp.add_handler(CommandHandler("stop",forcestop,filters=Filters.group,pass_chat_data=True))
    dp.add_handler(CommandHandler("tebak",tebak,filters=Filters.group,pass_args=True,pass_chat_data=True))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Block until you press Ctrl-C or the process receives SIGINT, SIGTERM or
    # SIGABRT. This should be used most of the time, since start_polling() is
    # non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Menjalankan Bot Telegram")
    parser.add_argument("token",help="Token dari Bot Telegram")
    parser.add_argument("-v","--verbose", help="Tampilkan log pada layar",action="store_true")
    
    args = parser.parse_args()
    
    if args.verbose:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(logger_formatter)
        logger.addHandler(console_handler)
    
    main(args.token)