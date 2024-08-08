import sys
import smtplib
from email.mime.text import MIMEText
import logging
import threading
import queue
import time
from logging.handlers import SMTPHandler
from concurrent_log_handler import ConcurrentRotatingFileHandler
from dotenv import load_dotenv
import os
import colorlog

load_dotenv()  # 加载 .env 文件中的环境变量


class SingletonMeta(type):
    """ A thread-safe implementation of Singleton """
    _instances = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


class EmailSender:
    def __init__(self, server, port, username, password):
        self.server = server
        self.port = port
        self.username = username
        self.password = password

    def send_email(self, subject, message, from_addr, to_addrs):
        try:
            email_msg = MIMEText(message, _subtype='plain', _charset='utf-8')
            email_msg['Subject'] = subject
            email_msg['From'] = from_addr
            email_msg['To'] = ','.join(to_addrs)

            with smtplib.SMTP_SSL(self.server, self.port) as smtp:
                smtp.login(self.username, self.password)
                smtp.sendmail(from_addr, to_addrs, email_msg.as_string())
        except Exception as e:
            print(f"Error: 在发送邮件时发生错误: {e}", file=sys.stderr)


class LogManager(metaclass=SingletonMeta):
    # 自定义日志级别
    TRADER_LEVEL_NO = 35
    logging.addLevelName(TRADER_LEVEL_NO, "TRADER")

    def __init__(
            self,
            mail_server="smtp.qq.com",
            mail_port=465,
            mail_username=os.getenv("SMTP_USER_NAME"),
            mail_password=os.getenv("SMTP_PASSWORD"),
            mail_receivers="280712999@qq.com"  # 收件人邮箱地址，用英文逗号分隔。
    ):
        if hasattr(self, "_initialized") and self._initialized:
            return  # 防止多次初始化

        # 初始化邮件处理相关变量
        self.mail_server = mail_server
        self.mail_port = mail_port
        self.mail_username = mail_username
        self.mail_password = mail_password
        self.mail_receivers = [email.strip() for email in mail_receivers.split(",")]

        self.email_sender = EmailSender(mail_server, mail_port, mail_username, mail_password)

        # Initialize queue before calling initialize_logger
        self.email_queue = queue.Queue()
        self.buffer = []

        # 初始化日志记录器
        self.logger = self.initialize_logger()

        # 初始化电子邮件处理线程
        self.stop_event = threading.Event()
        self.email_thread = threading.Thread(target=self.process_email_queue)
        self.email_thread.daemon = True
        self.email_thread.start()

        self._initialized = True

    def initialize_logger(self):
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.DEBUG)

        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_file_path = os.path.join(script_dir, "logs/app.log")
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

        logger.addHandler(self.create_file_handler(log_file_path))
        logger.addHandler(self.create_console_handler())
        logger.addHandler(self.create_trader_handler())

        return logger

    def create_file_handler(self, log_file_path):
        file_handler = ConcurrentRotatingFileHandler(log_file_path, "a", 512 * 1024, 10)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(module)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        return file_handler

    def create_console_handler(self):
        console_handler = logging.StreamHandler()
        console_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s | %(levelname)-8s | %(module)s:%(lineno)d - %(message)s",
            datefmt='%Y-%m-%d %H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red',
                'TRADER': 'purple',
            }
        )
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.DEBUG)
        return console_handler

    def create_trader_handler(self):
        trader_mail_handler = QueueSMTPHandler(
            email_queue=self.email_queue,
            mailhost=(self.mail_server, self.mail_port),
            fromaddr=self.mail_username,
            toaddrs=self.mail_receivers,
            subject='TRADER级别日志提醒',
            credentials=(self.mail_username, self.mail_password),
            secure=()
        )
        trader_mail_handler.setLevel(LogManager.TRADER_LEVEL_NO)
        return trader_mail_handler

    def get_logger(self):
        return self.logger

    def process_email_queue(self):
        while not self.stop_event.is_set():
            try:
                record = self.email_queue.get(timeout=1)
                if record is None:
                    break
                self.buffer.append(record)
                self.email_queue.task_done()
                print(f"Debug: Buffer currently has {len(self.buffer)} items.")
            except queue.Empty:
                pass

            if time.time() - getattr(self, '_last_send_time', 0) >= 15:
                self.send_buffered_emails()
                self._last_send_time = time.time()

    def send_buffered_emails(self):
        if self.buffer:
            combined_message = "\n\n".join([rec.msg for rec in self.buffer])
            try:
                self.email_sender.send_email(
                    subject=self.buffer[0].subject,
                    message=combined_message,
                    from_addr=self.buffer[0].fromaddr,
                    to_addrs=self.buffer[0].toaddrs
                )
                print("Debug: Combined email sent successfully")
            except Exception as e:
                print(f"Error: 在发送合并邮件时发生错误: {e}", file=sys.stderr)
            finally:
                self.buffer.clear()

    def stop(self):
        self.stop_event.set()
        self.email_thread.join()


class QueueSMTPHandler(SMTPHandler):
    def __init__(self, email_queue, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.email_queue = email_queue

    def emit(self, record):
        try:
            msg = self.format(record)
            email_record = type('EmailRecord', (), {})()
            email_record.msg = msg
            email_record.subject = self.getSubject(record)
            email_record.fromaddr = self.fromaddr
            email_record.toaddrs = self.toaddrs
            print(f"Debug: Adding message to queue: {msg}")
            self.email_queue.put(email_record)
        except Exception:
            self.handleError(record)


def log_trader(self, message, *args, **kws):
    if self.isEnabledFor(LogManager.TRADER_LEVEL_NO):
        self._log(LogManager.TRADER_LEVEL_NO, message, args, **kws)


logging.Logger.trader = log_trader

if __name__ == "__main__":
    log_manager = LogManager()
    logger = log_manager.get_logger()

    try:
        logger.debug("这是一条调试信息")
        logger.info("这是一条信息")
        logger.warning("这是一条警告信息")

        for _ in range(5):
            logger.trader("这是一条 TRADER 级别的信息")
        logger.error("这是一条错误信息")
        time.sleep(16)

        1 / 0
    except ZeroDivisionError:
        logger.exception("捕获到异常")
    finally:
        log_manager.stop()