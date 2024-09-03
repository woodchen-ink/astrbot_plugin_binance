import asyncio
import ccxt
from datetime import datetime
import pytz

from util.plugin_dev.api.v1.bot import Context, AstrMessageEvent, CommandResult
from util.plugin_dev.api.v1.config import *
from util.plugin_dev.api.v1.platform import *

class Main:
    def __init__(self, context: Context) -> None:
        NAMESPACE = "astrbot_plugin_cryptomarket"
        self.context = context
        self.context.register_commands(NAMESPACE, "market", "获取加密货币市场更新", 1, self.send_price_update)
        
        # 注册配置项
        put_config(NAMESPACE, "symbols", "订阅的币对", "BTC/USDT,ETH/USDT", "请输入要订阅的币对，用逗号分隔")
        put_config(NAMESPACE, "update_interval", "更新间隔（分钟）", "60", "请输入更新间隔，单位为分钟")
        
        self.cfg = load_config(NAMESPACE)
        self.singapore_tz = pytz.timezone('Asia/Singapore')
        self.exchange = ccxt.binance()
        self.SYMBOLS = self.cfg["symbols"].split(',')
        self.UPDATE_INTERVAL = int(self.cfg["update_interval"])

        # 注册定时任务
        self.context.register_task(self.scheduled_update(), "crypto_market_update")

    def get_ticker_info(self, symbol):
        ticker = self.exchange.fetch_ticker(symbol)
        return {
            'symbol': symbol,
            'last': ticker['last'],
            'change_percent': ticker['percentage'],
            'high': ticker['high'],
            'low': ticker['low'],
            'volume': ticker['baseVolume'],
            'quote_volume': ticker['quoteVolume'],
            'bid': ticker['bid'],
            'ask': ticker['ask']
        }

    def format_change(self, change_percent):
        if change_percent > 0:
            return f"🔼 +{change_percent:.2f}%"
        elif change_percent < 0:
            return f"🔽 {change_percent:.2f}%"
        else:
            return f"◀▶ {change_percent:.2f}%"

    async def send_price_update(self, message: AstrMessageEvent, context: Context):
        now = datetime.now(self.singapore_tz)
        update_message = f"市场更新 - {now.strftime('%Y-%m-%d %H:%M:%S')} (SGT)\n\n"
        
        for symbol in self.SYMBOLS:
            info = self.get_ticker_info(symbol)
            change_str = self.format_change(info['change_percent'])
            
            update_message += f"*{info['symbol']}*\n"
            update_message += f"价格: ${info['last']:.7f}\n"
            update_message += f"24h 涨跌: {change_str}\n"
            update_message += f"24h 高/低: ${info['high']:.7f} / ${info['low']:.7f}\n"
            update_message += f"24h 成交量: {info['volume']:.2f}\n"
            update_message += f"24h 成交额: ${info['quote_volume']:.2f}\n"
            update_message += f"买一/卖一: ${info['bid']:.7f} / ${info['ask']:.7f}\n\n"
        
        return CommandResult().message(update_message).use_t2i(False)

    async def scheduled_update(self):
        while True:
            result = await self.send_price_update(None, self.context)
            for platform in self.context.platforms:
                if platform.platform_name == 'aiocqhttp':
                    inst = platform.platform_instance
                    # 这里需要替换为实际的群号或用户ID列表
                    target_list = ["群号1", "群号2", "用户ID1", "用户ID2"]
                    for target in target_list:
                        await inst.send_msg({"group_id": target}, result)
            
            # 等待下一次更新
            await asyncio.sleep(self.UPDATE_INTERVAL * 60)
