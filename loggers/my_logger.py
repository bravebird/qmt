import sys
import smtplib
from email.mime.text import MIMEText
import logging
from logging.handlers import SMTPHandler
from concurrent_log_handler import ConcurrentRotatingFileHandler
from dotenv import load_dotenv
import os
import threading
import colorlog

load_dotenv()  # 加载 .env 文件中的环境变量


class LogManager:
    _instance = None
    _lock = threading.Lock()

    # 自定义日志级别
    TRADER_LEVEL_NO = 35
    logging.addLevelName(TRADER_LEVEL_NO, "TRADER")

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(
            self,
            mail_server="smtp.qq.com",
            mail_port=465,
            mail_username=os.getenv("SMTP_USER_NAME"),
            mail_password=os.getenv("SMTP_PASSWORD"),
            mail_receivers="280712999@qq.com"  # 收件人邮箱地址，用英文逗号分隔。
    ):
        """
        初始化 LogManager.

        Args:
            mail_server (str): 邮件服务器地址.
            mail_port (int): 邮件服务器端口.
            mail_username (str): 邮件发送账号.
            mail_password (str): 邮件发送密码 (或授权码).
            mail_receivers (str): 邮件接收地址，用英文逗号分隔的字符串.
        """
        if hasattr(self, "_initialized") and self._initialized:
            return  # 防止多次初始化

        self.mail_server = mail_server
        self.mail_port = mail_port
        self.mail_username = mail_username
        self.mail_password = mail_password
        self.mail_receivers = [email.strip() for email in mail_receivers.split(",")]

        # 初始化日志记录器
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        # 创建安全的文件处理器
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_file_path = os.path.join(script_dir, "logs/app.log")
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
        file_handler = ConcurrentRotatingFileHandler(log_file_path, "a", 512 * 1024, 10)
        file_formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(module)s:%(lineno)d - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_formatter)

        # 添加控制台处理器
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
                'TRADER': 'purple',  # 用于自定义日志级别
            }
        )
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.DEBUG)

        # 添加邮件处理器
        smtp_handler = SMTPHandler(
            mailhost=(mail_server, mail_port),
            fromaddr=mail_username,
            toaddrs=self.mail_receivers,
            subject='量化交易日志提醒',
            credentials=(mail_username, mail_password),
            secure=()
        )
        email_formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s\nModule: %(module)s\nLine: %(lineno)d', datefmt='%Y-%m-%d %H:%M:%S')
        smtp_handler.setFormatter(email_formatter)
        smtp_handler.setLevel(logging.ERROR)

        # 添加TRADER邮件处理器
        trader_mail_handler = TraderMailHandler(
            mailhost=(mail_server, mail_port),
            fromaddr=mail_username,
            toaddrs=self.mail_receivers,
            subject='TRADER级别日志提醒',
            credentials=(mail_username, mail_password),
            secure=()
        )
        trader_mail_handler.setFormatter(email_formatter)
        trader_mail_handler.setLevel(LogManager.TRADER_LEVEL_NO)

        # 添加处理器到logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        self.logger.addHandler(smtp_handler)
        self.logger.addHandler(trader_mail_handler)

        self._initialized = True

    def get_logger(self):
        return self.logger

class TraderMailHandler(SMTPHandler):
    def emit(self, record):
        """
        Emit a record.

        Send the record to the specified email addresses.
        """
        try:
            # Format the record and get the message
            msg = self.format(record)
            # Create email
            email_msg = MIMEText(msg, _subtype='plain', _charset='utf-8')
            email_msg['Subject'] = self.getSubject(record)
            email_msg['From'] = self.fromaddr
            email_msg['To'] = ','.join(self.toaddrs)
            # Establish a secured connection and send email
            smtp = smtplib.SMTP_SSL(self.mailhost, self.mailport)
            smtp.login(self.username, self.password)
            smtp.sendmail(self.fromaddr, self.toaddrs, email_msg.as_string())
            smtp.quit()
        except Exception:
            self.handleError(record)


def log_trader(self, message, *args, **kws):
    if self.isEnabledFor(LogManager.TRADER_LEVEL_NO):
        self._log(LogManager.TRADER_LEVEL_NO, message, args, **kws)

logging.Logger.trader = log_trader


# 使用示例
if __name__ == "__main__":
    # 初始化 LogManager (根据需要修改配置)
    log_manager = LogManager()
    logger = log_manager.get_logger()

    # 使用 logger 对象记录日志
    try:
        logger.debug("这是一条调试信息")
        logger.info("这是一条信息")
        logger.warning("这是一条警告信息")
        logger.error("这是一条错误信息")
        logger.trader("这是一条 TRADER 级别的信息")  # 使用自定义级别

        1 / 0
    except ZeroDivisionError:
        logger.exception("捕获到异常")
    except Exception as e:
        print(f"记录日志时发生错误: {e}")