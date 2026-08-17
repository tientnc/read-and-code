import os
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from alphaagent.core.experiment import FBWorkspace
from alphaagent.log import logger
from alphaagent.utils.env import QTDockerEnv


def _env_value(name: str, cast=str):
    value = os.getenv(name)
    if value in (None, ""):
        return None
    return cast(value)


def _env_segment(name: str):
    value = os.getenv(name)
    if value in (None, ""):
        return None
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"{name} must be formatted as START_DATE,END_DATE")
    return parts


def _set_if_env(mapping: dict, key: str, env_name: str, cast=str) -> bool:
    value = _env_value(env_name, cast=cast)
    if value is None:
        return False
    mapping[key] = value
    return True


def _calendar_dates(provider_uri: str | None) -> list[str]:
    if not provider_uri:
        return []
    calendar_path = Path(provider_uri).expanduser() / "calendars" / "day.txt"
    if not calendar_path.exists():
        return []
    return [line.strip() for line in calendar_path.read_text().splitlines() if line.strip()]


def _previous_calendar_date(date_value: str, calendars: list[str]) -> str:
    if len(calendars) < 2:
        return date_value
    if date_value >= calendars[-1]:
        return calendars[-2]
    return date_value


def _clamp_mapping_end(mapping: dict, key: str, calendars: list[str]) -> bool:
    value = mapping.get(key)
    if not isinstance(value, str):
        return False
    clamped = _previous_calendar_date(value, calendars)
    if clamped == value:
        return False
    mapping[key] = clamped
    return True


def _clamp_segment_end(segment: list, calendars: list[str]) -> bool:
    if not isinstance(segment, list) or len(segment) != 2 or not isinstance(segment[1], str):
        return False
    clamped = _previous_calendar_date(segment[1], calendars)
    if clamped == segment[1]:
        return False
    segment[1] = clamped
    return True


def apply_qlib_config_overrides(config_path: Path) -> None:
    """Apply environment overrides to a copied Qlib config before qrun.

    The template config is copied into a per-run workspace, so rewriting it here
    keeps CN defaults intact while allowing a separate VN provider/market setup.
    """
    if not config_path.exists():
        return

    with config_path.open() as f:
        config = yaml.safe_load(f)
    if not isinstance(config, dict):
        return

    changed = False

    qlib_init = config.setdefault("qlib_init", {})
    changed |= _set_if_env(qlib_init, "provider_uri", "QLIB_PROVIDER_URI")
    changed |= _set_if_env(qlib_init, "region", "QLIB_REGION")
    calendars = _calendar_dates(qlib_init.get("provider_uri"))

    market = _env_value("QLIB_MARKET")
    if market is not None:
        config["market"] = market
        data_handler = config.get("data_handler_config", {})
        if isinstance(data_handler, dict):
            data_handler["instruments"] = market
        changed = True

    benchmark = _env_value("QLIB_BENCHMARK")
    if benchmark is not None:
        config["benchmark"] = benchmark
        backtest = (
            config.get("port_analysis_config", {})
            .get("backtest", {})
        )
        if isinstance(backtest, dict):
            backtest["benchmark"] = benchmark
        changed = True

    data_handler = config.get("data_handler_config", {})
    if isinstance(data_handler, dict):
        changed |= _set_if_env(data_handler, "start_time", "QLIB_DATA_START_TIME")
        changed |= _set_if_env(data_handler, "end_time", "QLIB_DATA_END_TIME")
        changed |= _clamp_mapping_end(data_handler, "end_time", calendars)

    port_analysis = config.get("port_analysis_config", {})
    if isinstance(port_analysis, dict):
        strategy_kwargs = port_analysis.get("strategy", {}).get("kwargs", {})
        if isinstance(strategy_kwargs, dict):
            changed |= _set_if_env(strategy_kwargs, "topk", "QLIB_TOPK", int)
            changed |= _set_if_env(strategy_kwargs, "n_drop", "QLIB_N_DROP", int)

        backtest = port_analysis.get("backtest", {})
        if isinstance(backtest, dict):
            changed |= _set_if_env(backtest, "start_time", "QLIB_BACKTEST_START_TIME")
            changed |= _set_if_env(backtest, "end_time", "QLIB_BACKTEST_END_TIME")
            changed |= _clamp_mapping_end(backtest, "end_time", calendars)
            exchange_kwargs = backtest.setdefault("exchange_kwargs", {})
            if isinstance(exchange_kwargs, dict):
                changed |= _set_if_env(exchange_kwargs, "limit_threshold", "QLIB_LIMIT_THRESHOLD", float)
                changed |= _set_if_env(exchange_kwargs, "deal_price", "QLIB_DEAL_PRICE")
                changed |= _set_if_env(exchange_kwargs, "open_cost", "QLIB_OPEN_COST", float)
                changed |= _set_if_env(exchange_kwargs, "close_cost", "QLIB_CLOSE_COST", float)
                changed |= _set_if_env(exchange_kwargs, "min_cost", "QLIB_MIN_COST", float)

    segments = (
        config.get("task", {})
        .get("dataset", {})
        .get("kwargs", {})
        .get("segments", {})
    )
    if isinstance(segments, dict):
        for key, env_name in (
            ("train", "QLIB_TRAIN_SEGMENT"),
            ("valid", "QLIB_VALID_SEGMENT"),
            ("test", "QLIB_TEST_SEGMENT"),
        ):
            segment = _env_segment(env_name)
            if segment is not None:
                segments[key] = segment
                changed = True
            if key == "test" and key in segments:
                changed |= _clamp_segment_end(segments[key], calendars)

    if changed:
        with config_path.open("w") as f:
            yaml.safe_dump(config, f, sort_keys=False)


class QlibFBWorkspace(FBWorkspace):
    def __init__(self, template_folder_path: Path, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.inject_code_from_folder(template_folder_path)

    def execute(
        self, 
        qlib_config_name: str = "conf.yaml", 
        run_env: dict = {}, 
        use_local: bool = True, 
        *args, 
        **kwargs
    ) -> str:
        # Use the local environment or Docker environment
        qtde = QTDockerEnv(is_local=use_local)
        # Apply project-local provider and market overrides to the copied run config.
        apply_qlib_config_overrides(self.workspace_path / qlib_config_name)
        qtde.prepare()
        
        # Run the Qlib backtest
        logger.info(f"Execute {'Local' if use_local else 'Docker container'} Backtest: qrun {qlib_config_name}")
        execute_log = qtde.run(
            local_path=str(self.workspace_path),
            entry=f"qrun {qlib_config_name}",
            env=run_env,
        )

        # Process results
        logger.info(f"Read {'Local' if use_local else 'Docker container'} Backtest Result")
        execute_log = qtde.run(
            local_path=str(self.workspace_path),
            entry="python read_exp_res.py",
            env=run_env,
        )

        # Load results
        ret_df = pd.read_pickle(self.workspace_path / "ret.pkl")
        logger.log_object(ret_df, tag="Quantitative Backtesting Chart")

        csv_path = self.workspace_path / "qlib_res.csv"
        if not csv_path.exists():
            logger.error(f"File {csv_path} does not exist.")
            return None

        return pd.read_csv(csv_path, index_col=0).iloc[:, 0]
