from xtquant.xttype import StockAccount
from dotenv import load_dotenv
import os


load_dotenv()


acc = StockAccount(os.getenv("MINI_XT_USER"))
if not acc:
    raise RuntimeError('Account information could not be retrieved.')