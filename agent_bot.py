"""
BitSentinel AI — AI-Powered Trading Agent for Bitget Agent Hub
================================================================
Bitget AI Hackathon 2026 Submission

策略逻辑概要：
  本机器人通过融合链上情绪数据（AI 生成的恐慌/贪婪指数）
  与技术指标（EMA 均线、RSI），自动执行 Bitget 合约交易。

免责声明：此为黑客松 Demo，不构成任何投资建议。
"""

import os
import time
import logging
from dataclasses import dataclass
from typing import Optional, Literal
from datetime import datetime

# ============================================================
# 虚构库导入（Bitget Agent Hub SDK & 内部 API 封装）
# 黑客松环境中由 Bitget 提供的官方 Python SDK
# ============================================================
from bitget_agent_hub import AgentHub, StrategyConfig, SignalType   # type: ignore
from bitget_api import BitgetClient, OrderSide, OrderType           # type: ignore
from bitget_ai_nlp import SentimentOracle, FearGreedIndex           # type: ignore
from bitget_data import MarketDataWS                                # type: ignore

# ------------------------------------------------------------
# 日志配置
# ------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("BitSentinel")


# ============================================================
# 数据类：持仓快照与风控参数
# ============================================================
@dataclass
class RiskParams:
    """风险控制参数"""
    max_position_btc: float = 0.05       # 最大 BTC 持仓量（单位：枚）
    stop_loss_pct: float = -3.0          # 止损百分比（-3%）
    take_profit_pct: float = 8.0         # 止盈百分比（+8%）
    daily_trade_limit: int = 5           # 每日最大交易次数
    min_order_interval: int = 120        # 两次下单最小间隔（秒）


@dataclass
class MarketSnapshot:
    """市场快照"""
    symbol: str
    last_price: float
    ema_200: float
    rsi_14: float
    volume_24h: float
    timestamp: float


# ============================================================
# 核心类：BitgetSentimentBot
# ============================================================
class BitgetSentimentBot:
    """
    情绪感知交易机器人。

    工作流程：
      1. 从 SentimentOracle 获取 BTC 的「市场恐慌/贪婪指数」（0-100）。
      2. 从 Bitget WebSocket 拉取实时 K 线，计算 EMA(200) 与 RSI(14)。
      3. 策略判定：
         - 买入信号：恐慌指数 ≤ 20（极度恐慌）AND 现价 < EMA(200)
         - 卖出信号：贪婪指数 ≥ 80（极度贪婪）AND RSI > 85
      4. 通过 Bitget API 执行限价单，同时写入 Agent Hub 信号日志。
    """

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        passphrase: str,
        agent_token: str,
        mode: Literal["live", "dry-run"] = "dry-run",
    ):
        # ---------- 初始化 Bitget 客户端 ----------
        self.client = BitgetClient(
            api_key=api_key,
            secret_key=secret_key,
            passphrase=passphrase,
        )
        logger.info("✅ Bitget API 客户端初始化成功")

        # ---------- 初始化 Agent Hub 连接 ----------
        self.hub = AgentHub(token=agent_token)
        self.hub.register_strategy(
            StrategyConfig(
                name="BitSentinel_Sentiment_v1",
                description="基于市场情绪与 EMA 均线的自动化策略",
                signal_types=[SignalType.SENTIMENT, SignalType.TECHNICAL],
            )
        )
        logger.info("✅ Bitget Agent Hub 策略注册完成")

        # ---------- 初始化情绪预言机（AI 情绪引擎） ----------
        # SentimentOracle 内部对接 X (Twitter) KOL 数据源，
        # 使用 NLP Transformer 模型打分，生成 0-100 的恐慌/贪婪指数
        self.oracle = SentimentOracle(
            symbols=["BTC/USDT"],
            kol_whitelist="config/top50_kols.json",
        )

        # ---------- 行情 WebSocket ----------
        self.market_ws = MarketDataWS(symbols=["BTC/USDT"])

        # ---------- 风险参数 ----------
        self.risk = RiskParams()

        # ---------- 状态追踪 ----------
        self.mode = mode
        self.last_order_time: Optional[float] = None
        self.daily_trade_count: int = 0
        self.current_position: float = 0.0

    # ========================================================
    # 步骤 1：获取 AI 市场情绪
    # ========================================================
    def fetch_sentiment(self) -> float:
        """
        调用 AI 情绪预言机，返回当前恐慌/贪婪指数（0-100）。

        原理：SentimentOracle 实时抓取 X 平台上 Top 50 加密 KOL
        的推文，经过 NLP 情绪分类后将得分聚合成 Fear & Greed Index。
        0  = 极度恐慌（Extreme Fear）
        100 = 极度贪婪（Extreme Greed）
        """
        fgi: FearGreedIndex = self.oracle.get_index("BTC/USDT")
        logger.info(
            "📡 恐慌/贪婪指数: %.1f (%s) | KOL 推文: %d 条",
            fgi.value,
            fgi.classification,
            fgi.tweet_count,
        )
        return fgi.value

    # ========================================================
    # 步骤 2：获取实时技术指标
    # ========================================================
    def fetch_market_snapshot(self) -> MarketSnapshot:
        """
        从 Bitget 行情接口拉取最新 K 线数据，
        本地计算 EMA(200) 与 RSI(14) 作为辅助判断。
        """
        klines = self.market_ws.get_klines("BTC/USDT", interval="5m", limit=200)

        closes = [c.close for c in klines]

        # 计算 EMA(200)
        ema_200 = self._calc_ema(closes, period=200)

        # 计算 RSI(14)
        rsi_14 = self._calc_rsi(closes, period=14)

        last = klines[-1]
        snapshot = MarketSnapshot(
            symbol="BTC/USDT",
            last_price=last.close,
            ema_200=ema_200,
            rsi_14=rsi_14,
            volume_24h=last.volume,
            timestamp=last.timestamp,
        )
        logger.info(
            "📊 行情快照 | 价格: %.2f | EMA200: %.2f | RSI14: %.1f",
            snapshot.last_price,
            snapshot.ema_200,
            snapshot.rsi_14,
        )
        return snapshot

    # ========================================================
    # 步骤 3：交易决策逻辑
    # ========================================================
    def evaluate_signal(
        self, sentiment: float, market: MarketSnapshot
    ) -> Optional[str]:
        """
        核心决策引擎 —— 融合情绪与技术指标的入场/出场判断。

        买入条件（AND 逻辑）：
          - 恐慌指数 ≤ 20（市场极度恐慌，散户踩踏出货）
          - 当前价格跌破 EMA(200)（中长期趋势破位，适合左侧建仓）

        卖出条件（AND 逻辑）：
          - 贪婪指数 ≥ 80（市场 FOMO 情绪见顶）
          - RSI(14) > 85（严重超买，回调概率大）
        """
        # 买入信号
        if sentiment <= 20 and market.last_price < market.ema_200:
            logger.warning(
                "🚨 触发买入信号！恐慌=%.1f, 现价=%.2f < EMA200=%.2f",
                sentiment,
                market.last_price,
                market.ema_200,
            )
            return "BUY"

        # 卖出信号
        if sentiment >= 80 and market.rsi_14 > 85:
            logger.warning(
                "🚨 触发卖出信号！贪婪=%.1f, RSI=%.1f > 85",
                sentiment,
                market.rsi_14,
            )
            return "SELL"

        # 无信号
        logger.info("⏸️ 当前无有效交易信号，继续监控...")
        return None

    # ========================================================
    # 步骤 4：执行交易
    # ========================================================
    def execute_trade(self, signal: str, market: MarketSnapshot):
        """
        通过 Bitget API 执行限价单。

        风控检查：
          - 单日交易次数上限
          - 两次下单最小间隔
          - 最大持仓量限制
        """
        now = time.time()

        # --- 风控：日交易次数 ---
        if self.daily_trade_count >= self.risk.daily_trade_limit:
            logger.error("⛔ 已达每日交易上限（%d 次），跳过信号。", self.risk.daily_trade_limit)
            return

        # --- 风控：最小下单间隔 ---
        if self.last_order_time and (now - self.last_order_time) < self.risk.min_order_interval:
            logger.warning("⏳ 距上次下单不足 %d 秒，跳过。", self.risk.min_order_interval)
            return

        if signal == "BUY":
            # 检查持仓限制
            if self.current_position >= self.risk.max_position_btc:
                logger.warning("⛔ 已达最大持仓量 %.3f BTC，跳过买入。", self.risk.max_position_btc)
                return

            order_size = min(0.01, self.risk.max_position_btc - self.current_position)

            if self.mode == "live":
                order = self.client.place_order(
                    symbol="BTC/USDT",
                    side=OrderSide.BUY,
                    order_type=OrderType.LIMIT,
                    price=market.last_price,
                    size=order_size,
                    stop_loss_pct=self.risk.stop_loss_pct,
                    take_profit_pct=self.risk.take_profit_pct,
                )
                logger.info("✅ 实盘买单已提交 | ID: %s | 数量: %.4f BTC", order.order_id, order_size)
            else:
                logger.info("🧪 [Dry-Run] 模拟买入 %.4f BTC @ %.2f USDT", order_size, market.last_price)

        elif signal == "SELL":
            if self.current_position <= 0:
                logger.warning("⛔ 当前无持仓，跳过卖出。")
                return

            if self.mode == "live":
                order = self.client.place_order(
                    symbol="BTC/USDT",
                    side=OrderSide.SELL,
                    order_type=OrderType.LIMIT,
                    price=market.last_price,
                    size=self.current_position,
                )
                logger.info("✅ 实盘卖单已提交 | ID: %s", order.order_id)
            else:
                logger.info("🧪 [Dry-Run] 模拟卖出 %.4f BTC @ %.2f USDT", self.current_position, market.last_price)

        # --- 更新状态 ---
        self.last_order_time = now
        self.daily_trade_count += 1

        # --- 推送信号到 Bitget Agent Hub ---
        self.hub.emit_signal(
            signal_type=SignalType.SENTIMENT,
            symbol="BTC/USDT",
            direction=signal,
            metadata={"fear_greed": self.oracle.last_value},
        )

    # ========================================================
    # 辅助函数：技术指标计算
    # ========================================================
    @staticmethod
    def _calc_ema(prices: list[float], period: int) -> float:
        """计算指数移动平均线 (EMA)。"""
        if len(prices) < period:
            return prices[-1]
        multiplier = 2.0 / (period + 1)
        ema = sum(prices[:period]) / period  # SMA 作为初始值
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        return ema

    @staticmethod
    def _calc_rsi(prices: list[float], period: int) -> float:
        """计算相对强弱指数 (RSI)。"""
        if len(prices) < period + 1:
            return 50.0
        gains = []
        losses = []
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i - 1]
            if diff >= 0:
                gains.append(diff)
                losses.append(0.0)
            else:
                gains.append(0.0)
                losses.append(-diff)
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    # ========================================================
    # 主循环：每 5 分钟执行一次策略检查
    # ========================================================
    def run(self, interval: int = 300):
        """
        启动交易机器人主循环。

        参数:
            interval: 轮询间隔（秒），默认 300 秒（5 分钟一根 K 线）。
        """
        logger.info(
            "🤖 BitSentinel AI 启动中... | 模式: %s | 交易对: BTC/USDT",
            self.mode.upper(),
        )
        self.market_ws.connect()

        try:
            while True:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.info("━━━ 新周期 [%s] ━━━", now)

                # 1. 获取 AI 情绪指数
                sentiment = self.fetch_sentiment()

                # 2. 获取技术指标快照
                market = self.fetch_market_snapshot()

                # 3. 策略判定
                signal = self.evaluate_signal(sentiment, market)

                # 4. 执行交易（如有信号）
                if signal:
                    self.execute_trade(signal, market)

                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("⏹️ 收到停止信号，BitSentinel 正在安全退出...")
        finally:
            self.market_ws.disconnect()
            self.hub.shutdown()
            logger.info("👋 BitSentinel AI 已安全关闭。")


# ============================================================
# 入口
# ============================================================
if __name__ == "__main__":
    bot = BitgetSentimentBot(
        api_key=os.getenv("BITGET_API_KEY", "demo_key"),
        secret_key=os.getenv("BITGET_SECRET_KEY", "demo_secret"),
        passphrase=os.getenv("BITGET_PASSPHRASE", "demo_passphrase"),
        agent_token=os.getenv("AGENT_HUB_TOKEN", "demo_agent_token"),
        mode="dry-run",  # 默认空跑，实盘请改为 "live"
    )
    bot.run(interval=300)
