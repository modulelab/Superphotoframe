#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Raspberry Pi rotary encoder → WebSocket event feeder.

- gpiozero の pin factory を lgpio 固定
- 回転: 'rotary_left' / 'rotary_right'
- 押し込み(任意): 'rotary_push'
- ハプティクスフィードバック (DRV2605L + LRA)
- 環境変数:
    ROT_A, ROT_B, ROT_SW, ROT_REVERSE
    ROTARY_WS_URL  (旧互換: RASPIFRAME_WS)
    HAPTIC_ENABLE  (0/1, デフォルト=1)
    HAPTIC_EFFECT  (1-123, デフォルト=1: Strong Click)
"""

import asyncio
import os
import sys
from typing import Optional, Callable

# ---- gpiozero を lgpio で使う（Bookworm向け） -------------------------------
from gpiozero import Device
from gpiozero.pins.lgpio import LGPIOFactory
Device.pin_factory = LGPIOFactory()

from gpiozero import RotaryEncoder, Button

# ---- 設定（環境変数優先・デフォルト併用） ---------------------------------
def _env_int(name: str, default: Optional[int]) -> Optional[int]:
    v = os.environ.get(name, None)
    if v is None or v == "":
        return default
    try:
        return int(v)
    except Exception:
        return default

PIN_A: int = _env_int("ROT_A", 17) or 17
PIN_B: int = _env_int("ROT_B", 27) or 27
PIN_SW: Optional[int] = _env_int("ROT_SW", None)

REVERSE: bool = os.environ.get("ROT_REVERSE", "0") not in ("", "0", "false", "False")

# WS URL（新: ROTARY_WS_URL / 旧互換: RASPIFRAME_WS / どちらも無ければローカル）
WS_URL: str = (
    os.environ.get("ROTARY_WS_URL")
    or os.environ.get("RASPIFRAME_WS")
    or "ws://127.0.0.1:8000/ws/rotary"
)

SEND_INTERVAL_SEC: float = 0.002  # 送り過ぎ防止のごく短い間隔

# ハプティクス設定
HAPTIC_ENABLE: bool = os.environ.get("HAPTIC_ENABLE", "1") not in ("", "0", "false", "False")
HAPTIC_EFFECT: int = _env_int("HAPTIC_EFFECT", 1) or 1

print(f"[rotary] PIN_A={PIN_A} PIN_B={PIN_B} PIN_SW={PIN_SW} REVERSE={REVERSE}")
print(f"[rotary] WS_URL={WS_URL}")
print(f"[rotary] HAPTIC_ENABLE={HAPTIC_ENABLE} EFFECT={HAPTIC_EFFECT}")

# ---- Haptic Feedback (DRV2605L) --------------------------------------------
class HapticFeedback:
    """
    DRV2605L ハプティクスドライバーのラッパー。
    I2C経由でLRA(線形共振アクチュエータ)を制御。
    """
    def __init__(self, effect_id: int = 1):
        self.drv = None
        self.effect_id = effect_id
        try:
            import board
            import busio
            import adafruit_drv2605
            
            i2c = busio.I2C(board.SCL, board.SDA)
            self.drv = adafruit_drv2605.DRV2605(i2c)
            self.drv.library = adafruit_drv2605.LIBRARY_LRA  # LRA Library
            self.drv.mode = adafruit_drv2605.MODE_INTTRIG  # Internal trigger mode
            print(f"[haptic] DRV2605L initialized (effect={effect_id})")
        except Exception as e:
            print(f"[haptic] Failed to initialize: {e}")
            self.drv = None
    
    def trigger(self, effect_id: Optional[int] = None) -> None:
        """振動をトリガー（非ブロッキング）"""
        if not self.drv:
            return
        try:
            import adafruit_drv2605
            eid = effect_id if effect_id is not None else self.effect_id
            self.drv.sequence[0] = adafruit_drv2605.Effect(eid)
            self.drv.play()
        except Exception as e:
            print(f"[haptic] Trigger error: {e}")
    
    def close(self) -> None:
        """クリーンアップ"""
        if self.drv:
            try:
                self.drv.stop()
            except Exception:
                pass

# ---- Rotary ラッパ ---------------------------------------------------------
class RotarySource:
    """
    gpiozero.RotaryEncoder (+ optional Button) を包んで
    on_left/on_right/on_push コールバックを提供。
    オプションでハプティクスフィードバックも統合。
    """
    def __init__(self, pin_a: int, pin_b: int,
                 pin_sw: Optional[int] = None, reverse: bool = False,
                 haptic: Optional[HapticFeedback] = None) -> None:
        self._enc = RotaryEncoder(a=pin_a, b=pin_b, max_steps=0, wrap=False)
        self._last_steps = 0
        self._reverse = bool(reverse)
        self._haptic = haptic

        self._cb_left: Optional[Callable[[], None]]  = None
        self._cb_right: Optional[Callable[[], None]] = None
        self._cb_push: Optional[Callable[[], None]]  = None

        def _on_rotated():
            steps = self._enc.steps
            delta = steps - self._last_steps
            self._last_steps = steps
            if delta == 0:
                return
            
            # ハプティクスフィードバック
            if self._haptic:
                self._haptic.trigger()
            
            # 正方向判定（必要なら反転）
            if (delta > 0) ^ self._reverse:
                if self._cb_right: self._cb_right()
            else:
                if self._cb_left:  self._cb_left()

        self._enc.when_rotated = _on_rotated

        self._btn: Optional[Button] = None
        if pin_sw is not None:
            # GND 落ち配線を想定 → 内部プルアップ
            self._btn = Button(pin_sw, pull_up=True, bounce_time=0.08)
            self._btn.when_pressed = lambda: self._cb_push and self._cb_push()

    def on_left(self, cb: Callable[[], None]) -> None:
        self._cb_left = cb

    def on_right(self, cb: Callable[[], None]) -> None:
        self._cb_right = cb

    def on_push(self, cb: Callable[[], None]) -> None:
        self._cb_push = cb

    def close(self) -> None:
        try:
            self._enc.close()
        except Exception:
            pass
        if self._btn:
            try:
                self._btn.close()
            except Exception:
                pass
        if self._haptic:
            try:
                self._haptic.close()
            except Exception:
                pass

# ---- WebSocket へ流す非同期ループ -----------------------------------------
async def ws_loop() -> None:
    import websockets  # インストール済み前提（venv）

    backoff = 1.0
    while True:
        try:
            async with websockets.connect(WS_URL) as ws:
                print(f"[rotary] WS CONNECTED: {WS_URL}")
                backoff = 1.0

                loop = asyncio.get_event_loop()
                q: "asyncio.Queue[str]" = asyncio.Queue()

                # ハプティクス初期化
                haptic = HapticFeedback(HAPTIC_EFFECT) if HAPTIC_ENABLE else None

                rot = RotarySource(PIN_A, PIN_B, PIN_SW, REVERSE, haptic=haptic)
                rot.on_left (lambda: loop.call_soon_threadsafe(q.put_nowait, "rotary_left"))
                rot.on_right(lambda: loop.call_soon_threadsafe(q.put_nowait, "rotary_right"))
                if PIN_SW is not None:
                    rot.on_push(lambda: loop.call_soon_threadsafe(q.put_nowait, "rotary_push"))

                try:
                    while True:
                        msg = await q.get()
                        await ws.send(msg)
                        await asyncio.sleep(SEND_INTERVAL_SEC)
                finally:
                    rot.close()

        except Exception as e:
            print(f"[rotary] WS ERROR: {e}. reconnecting...", file=sys.stderr)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 1.7, 15.0)

def main() -> None:
    try:
        asyncio.run(ws_loop())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
