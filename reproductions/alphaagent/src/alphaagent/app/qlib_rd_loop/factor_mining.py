"""
Factor workflow with session control
"""

from typing import Any
import fire
import signal
import sys
import threading
from functools import wraps
import time
import ctypes
import os
from alphaagent.app.qlib_rd_loop.conf import ALPHA_AGENT_FACTOR_PROP_SETTING
from alphaagent.components.workflow.alphaagent_loop import AlphaAgentLoop
from alphaagent.core.exception import FactorEmptyError
from alphaagent.log import logger
from alphaagent.log.time import measure_time
from alphaagent.oai.llm_conf import LLM_SETTINGS




def force_timeout():
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Prefer the timeout setting.
            seconds = LLM_SETTINGS.factor_mining_timeout
            def handle_timeout(signum, frame):
                logger.error(f"Forcefully terminating execution after exceeding {seconds} seconds")
                sys.exit(1)

            # Set the signal handler.
            signal.signal(signal.SIGALRM, handle_timeout)
            # Set the alarm.
            signal.alarm(seconds)

            try:
                result = func(*args, **kwargs)
            finally:
                # Cancel the alarm.
                signal.alarm(0)
            return result
        return wrapper
    return decorator


@force_timeout()
def main(path=None, step_n=None, direction=None, stop_event=None):
    """
    Autonomous alpha factor mining. 

    Args:
        path: session path
        step_n: number of steps
        direction: initial direction
        stop_event: stop event

    You can continue running session by

    .. code-block:: python

        dotenv run -- python rdagent/app/qlib_rd_loop/factor_alphaagent.py $LOG_PATH/__session__/1/0_propose  --step_n 1  --potential_direction "[Initial Direction (Optional)]"  # `step_n` is a optional paramter

    """
    try:
        use_local = os.getenv("USE_LOCAL", "True").lower()
        use_local = True if use_local in ["true", "1"] else False
        logger.info(f"Use {'Local' if use_local else 'Docker container'} to execute factor backtest")
        if path is None:
            model_loop = AlphaAgentLoop(ALPHA_AGENT_FACTOR_PROP_SETTING, potential_direction=direction, stop_event=stop_event, use_local=use_local)
        else:
            model_loop = AlphaAgentLoop.load(path, use_local=use_local)
        model_loop.run(step_n=step_n, stop_event=stop_event)
    except Exception as e:
        logger.error(f"An error occurred during execution: {str(e)}")
        raise
    finally:
        logger.info("Program execution completed or was terminated")

if __name__ == "__main__":
    fire.Fire(main)
