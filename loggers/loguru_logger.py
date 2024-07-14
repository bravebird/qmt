import sys
import smtplib
from email.mime.text import MIMEText
from loguru import logger
from dotenv import load_dotenv
import os

load_dotenv()  # 加载 .env 文件中的环境变量

class LogManager:
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
        self.mail_server = mail_server
        self.mail_port = mail_port
        self.mail_username = mail_username
        self.mail_password = mail_password
        self.mail_receivers = [email.strip() for email in mail_receivers.split(",")]

        # 获取脚本文件所在的目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_file_path = os.path.join(script_dir, "logs/app.log")

        # 确保日志文件夹存在
        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

        # 自定义日志级别 TRADER
        self.TRADER_LEVEL_NO = 36
        logger.level("TRADER", no=self.TRADER_LEVEL_NO, color="<red>", icon="🔥")

        # 配置 Loguru
        logger.remove()

        # 添加控制台处理器
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{module}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="DEBUG",
            colorize=True,
        )

        # 添加文件 처리器
        logger.add(
            log_file_path,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {module}:{line} - {message}",
            level="DEBUG",
            rotation="3 MB",
            compression="zip",
        )

        # 添加拦截器
        logger.add(self.error_interceptor, level=self.TRADER_LEVEL_NO)
        logger.add(self.error_interceptor, level="ERROR")

    def send_error_mail(self, record):
        """发送错误日志邮件."""
        try:
            level = record["level"].name
            record_str = str(record)

            msg = MIMEText(record_str, "plain", "utf-8")
            msg["Subject"] = f"量化交易日志提醒 [{level}]"
            msg["From"] = self.mail_username
            msg["To"] = ", ".join(self.mail_receivers)

            try:
                with smtplib.SMTP_SSL(host=self.mail_server, port=self.mail_port, timeout=10) as server:
                    # server.set_debuglevel(1)
                    server.login(self.mail_username, self.mail_password)
                    server.sendmail(self.mail_username, self.mail_receivers, msg.as_string())

                print("错误邮件发送成功")
            except Exception as e:
                print(f"发送邮件失败: {e}")
        except Exception as e:
            print(f"处理日志记录时发生错误: {e}")

    def error_interceptor(self, message):
        """拦截 TRADER 和 ERROR 级别的日志并发送邮件。"""
        self.send_error_mail(message.record)

# 使用示例:
if __name__ == "__main__":
    # 初始化 LogManager (根据需要修改配置)
    log_manager = LogManager()

    # 使用 logger 对象记录日志
    logger.debug("这是一条调试信息")
    logger.info("这是一条信息")
    logger.warning("这是一条警告信息")
    logger.error("这是一条错误信息")
    logger.log("TRADER", "这是一条 TRADER 级别的信息")  # 使用自定义级别

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("捕获到异常")